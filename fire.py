"""
fire.py — Optimized fire, smoke, ember particle system, dynamic lighting,
and physical burning logs/kindling pile that chars and glows over time.
"""
import pygame
import random
import math

MAX_FIRE_PARTICLES   = 170
MAX_SMOKE_PARTICLES  = 50
MAX_EMBER_PARTICLES  = 55


class FuelPiece:
    """Реальный кусок топлива в костре, который постепенно обугливается и светится."""
    def __init__(self, kind, cx, cy):
        self.kind = kind  # 'tinder', 'kindling', 'log'
        self.ox = random.uniform(-28, 28)
        self.oy = random.uniform(-6, 10)
        self.angle = random.uniform(-38, 38)
        self.char = 0.0   # 0.0 = свежее дерево, 1.0 = чёрный уголь с красным жаром
        self.life = 1.0   # 1.0 -> 0.0 (сгорает полностью)

        if kind == 'tinder':
            self.length = random.randint(28, 42)
            self.thick = random.randint(6, 9)
            self.base_col = (215, 195, 160)
            self.burn_rate = 0.045
        elif kind == 'kindling':
            self.length = random.randint(55, 80)
            self.thick = random.randint(5, 8)
            self.base_col = (135, 95, 55)
            self.burn_rate = 0.020
        else:  # log
            self.length = random.randint(85, 115)
            self.thick = random.randint(16, 22)
            self.base_col = (155, 125, 85)
            self.burn_rate = 0.009

    def update(self, dt, temp_ratio):
        rate = self.burn_rate * (0.4 + 1.2 * temp_ratio)
        self.char = min(1.0, self.char + rate * dt * 1.6)
        self.life -= rate * dt * 0.75


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "lifetime", "max_life", "size", "c_start", "c_end", "grows")

    def __init__(self, x, y, vx, vy, lifetime, size, c_start, c_end, grows=False):
        self.x        = x
        self.y        = y
        self.vx       = vx
        self.vy       = vy
        self.lifetime = lifetime
        self.max_life = lifetime
        self.size     = size
        self.c_start  = c_start
        self.c_end    = c_end
        self.grows    = grows

    @property
    def alive(self):
        return self.lifetime > 0

    @property
    def ratio(self):
        return self.lifetime / self.max_life

    def color(self):
        r = self.ratio
        cs, ce = self.c_start, self.c_end
        return (
            int(cs[0] * r + ce[0] * (1 - r)),
            int(cs[1] * r + ce[1] * (1 - r)),
            int(cs[2] * r + ce[2] * (1 - r)),
        )

    def current_size(self):
        if self.grows:
            return max(2, int(self.size + 0.15 * (self.max_life - self.lifetime)))
        return max(1, int(self.size * self.ratio))

    def update(self, wind_x=0.0):
        self.x += self.vx + wind_x
        self.y += self.vy
        self.lifetime -= 1
        self.vx += random.uniform(-0.06, 0.06)


class FireSystem:
    def __init__(self, cx, cy):
        self.cx = cx
        self.cy = cy
        self.fire_particles = []
        self.smoke_particles = []
        self.ember_particles = []
        self.fuel_pieces = []
        self.temperature = 0.0
        self.wind_x = 0.0
        self._spawn_acc = 0.0
        self._glow_phase = 0.0

        self._fire_surf = pygame.Surface((800, 600), pygame.SRCALPHA)
        self._light_surf = pygame.Surface((800, 600), pygame.SRCALPHA)

    def clear_fuel(self):
        self.fuel_pieces.clear()

    def add_fuel_visual(self, kind):
        """Добавляет физический кусок дерева в костёр."""
        if len(self.fuel_pieces) < 18:
            self.fuel_pieces.append(FuelPiece(kind, self.cx, self.cy))

    def set_temperature(self, temp):
        self.temperature = max(0.0, min(100.0, temp))

    def set_wind(self, wind_x):
        self.wind_x = wind_x

    def burst_embers(self, count=15):
        for _ in range(count):
            if len(self.ember_particles) < MAX_EMBER_PARTICLES * 2:
                p = Particle(
                    self.cx + random.uniform(-30, 30),
                    self.cy + random.uniform(-8, 6),
                    random.uniform(-2.4, 2.4),
                    random.uniform(-4.8, -1.5),
                    random.randint(35, 75),
                    random.randint(2, 4),
                    (255, 230, 90),
                    (255, 60, 0)
                )
                self.ember_particles.append(p)

    def update(self, dt=1/60.0):
        temp_ratio = self.temperature / 100.0
        wind_effect = self.wind_x * 0.035
        self._glow_phase += 0.08

        # Update physical fuel pieces
        for fp in self.fuel_pieces:
            fp.update(dt, temp_ratio)
        self.fuel_pieces = [fp for fp in self.fuel_pieces if fp.life > 0]

        # Update particles
        for lst in (self.fire_particles, self.smoke_particles, self.ember_particles):
            for p in lst:
                p.update(wind_effect)

        self.fire_particles  = [p for p in self.fire_particles  if p.alive]
        self.smoke_particles = [p for p in self.smoke_particles if p.alive]
        self.ember_particles = [p for p in self.ember_particles if p.alive]

        # Spawn fire particles
        if temp_ratio > 0.03:
            width = 22 + int(70 * temp_ratio)
            height_mul = 0.5 + 1.45 * temp_ratio
            rate = 6.5 * temp_ratio
            self._spawn_acc += rate
            to_spawn = min(int(self._spawn_acc), MAX_FIRE_PARTICLES - len(self.fire_particles))
            self._spawn_acc -= to_spawn

            for _ in range(max(0, to_spawn)):
                x = self.cx + random.uniform(-width / 2, width / 2)
                y = self.cy + random.uniform(-6, 6)
                vx = random.uniform(-0.7, 0.7)
                vy = -2.2 * height_mul + random.uniform(-1.0, 1.0)
                lt = int(32 * height_mul + random.uniform(0, 16))
                sz = random.randint(5, 11)
                c_start = (255, 235, 90) if temp_ratio > 0.4 else (255, 145, 35)
                c_end   = (195, 25, 5)
                self.fire_particles.append(Particle(x, y, vx, vy, lt, sz, c_start, c_end))

        # Spawn smoke
        smoke_chance = 0.14 if temp_ratio < 0.25 else 0.05
        if random.random() < smoke_chance and len(self.smoke_particles) < MAX_SMOKE_PARTICLES:
            self.smoke_particles.append(Particle(
                self.cx + random.uniform(-18, 18),
                self.cy - 14,
                random.uniform(-0.4, 0.4),
                random.uniform(-1.2, -0.6),
                random.randint(60, 110),
                random.randint(6, 12),
                (95, 90, 85),
                (45, 42, 40),
                grows=True
            ))

        # Ambient embers
        if temp_ratio > 0.30 and random.random() < 0.09 and len(self.ember_particles) < MAX_EMBER_PARTICLES:
            self.ember_particles.append(Particle(
                self.cx + random.uniform(-24, 24),
                self.cy + random.uniform(-4, 4),
                random.uniform(-1.2, 1.2),
                random.uniform(-2.6, -0.8),
                random.randint(45, 80),
                3,
                (255, 190, 50),
                (255, 60, 0)
            ))

    def draw_fuel_pile(self, surface):
        """Рисует набросанные в костёр дрова, которые чернеют и тлеют."""
        temp_ratio = self.temperature / 100.0
        for fp in self.fuel_pieces:
            rad = math.radians(fp.angle)
            hw = int((fp.length * (0.6 + 0.4 * fp.life)) // 2)
            cx = int(self.cx + fp.ox)
            cy = int(self.cy + fp.oy)
            x1 = int(cx - hw * math.cos(rad))
            y1 = int(cy + hw * math.sin(rad))
            x2 = int(cx + hw * math.cos(rad))
            y2 = int(cy - hw * math.sin(rad))

            # Цвет переходит от дерева к чёрному углю
            c = fp.char
            col = (
                int(fp.base_col[0] * (1 - c) + 32 * c),
                int(fp.base_col[1] * (1 - c) + 26 * c),
                int(fp.base_col[2] * (1 - c) + 24 * c),
            )
            thick = max(2, int(fp.thick * (0.5 + 0.5 * fp.life)))
            pygame.draw.line(surface, col, (x1, y1), (x2, y2), thick)

            # Светящиеся трещины углей на обгоревшем дереве
            if c > 0.35 and temp_ratio > 0.05:
                glow = int(min(255, 180 * c * temp_ratio * (0.8 + 0.2 * math.sin(self._glow_phase * 2 + fp.ox))))
                if glow > 25:
                    pygame.draw.line(surface, (255, int(glow * 0.45), 10), (x1, y1 + 1), (x2, y2 + 1), max(1, thick // 3))

    def draw(self, surface):
        self._fire_surf.fill((0, 0, 0, 0))

        # 1. Glowing ember bed
        temp_ratio = self.temperature / 100.0
        if temp_ratio > 0.02:
            bed_w = int(55 + 65 * temp_ratio)
            ember_col = (
                min(255, int(160 + 95 * temp_ratio)),
                max(20, int(35 + 120 * temp_ratio)),
                10,
                int(165 + 55 * math.sin(self._glow_phase))
            )
            pygame.draw.ellipse(self._fire_surf, ember_col,
                                (self.cx - bed_w // 2, self.cy - 4, bed_w, 20))

        # 2. Physical fuel pieces inside fire
        self.draw_fuel_pile(self._fire_surf)

        # 3. Smoke
        for p in self.smoke_particles:
            col = p.color()
            sz = p.current_size()
            alpha = int(140 * p.ratio)
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], alpha), (int(p.x), int(p.y)), sz)

        # 4. Fire
        for p in self.fire_particles:
            col = p.color()
            sz = p.current_size()
            alpha = int(225 * p.ratio)
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], alpha), (int(p.x), int(p.y)), sz)

        # 5. Embers
        for p in self.ember_particles:
            col = p.color()
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], 240), (int(p.x), int(p.y)), p.size)

        surface.blit(self._fire_surf, (0, 0))

    def draw_ambient_light(self, surface):
        temp_ratio = self.temperature / 100.0
        if temp_ratio <= 0.02:
            return

        self._light_surf.fill((0, 0, 0, 0))
        flicker = 1.0 + 0.07 * math.sin(self._glow_phase * 2.3) + 0.04 * math.sin(self._glow_phase * 4.7)
        radius = int((95 + 270 * temp_ratio) * flicker)
        max_alpha = int(115 * temp_ratio)

        for r in range(radius, 0, -18):
            step_alpha = int(max_alpha * (1.0 - (r / radius) ** 1.8))
            if step_alpha > 0:
                pygame.draw.circle(self._light_surf, (255, 140, 20, step_alpha), (self.cx, self.cy - 10), r)

        surface.blit(self._light_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)