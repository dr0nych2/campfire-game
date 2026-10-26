"""
fire.py — Optimized fire, smoke, and ember particle system with dynamic ambient lighting.
"""
import pygame
import random
import math

MAX_FIRE_PARTICLES   = 160
MAX_SMOKE_PARTICLES  = 50
MAX_EMBER_PARTICLES  = 40

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
        self.temperature = 0.0
        self.wind_x = 0.0
        self._spawn_acc = 0.0
        self._glow_phase = 0.0

        # Pre-allocated transparent surfaces for batch particle and glow rendering
        self._fire_surf = pygame.Surface((800, 600), pygame.SRCALPHA)
        self._light_surf = pygame.Surface((800, 600), pygame.SRCALPHA)

    def set_temperature(self, temp):
        self.temperature = max(0.0, min(100.0, temp))

    def set_wind(self, wind_x):
        self.wind_x = wind_x

    def burst_embers(self, count=15):
        """Spawns an energetic shower of sparks when poked or blown."""
        for _ in range(count):
            if len(self.ember_particles) < MAX_EMBER_PARTICLES * 2:
                p = Particle(
                    self.cx + random.uniform(-25, 25),
                    self.cy + random.uniform(-5, 5),
                    random.uniform(-2.2, 2.2),
                    random.uniform(-4.5, -1.5),
                    random.randint(40, 80),
                    random.randint(2, 4),
                    (255, 220, 80),
                    (255, 60, 0)
                )
                self.ember_particles.append(p)

    def update(self):
        temp_ratio = self.temperature / 100.0
        wind_effect = self.wind_x * 0.035
        self._glow_phase += 0.08

        # ── Update existing particles ─────────────────────────────────────────
        for lst in (self.fire_particles, self.smoke_particles, self.ember_particles):
            for p in lst:
                p.update(wind_effect)

        self.fire_particles  = [p for p in self.fire_particles  if p.alive]
        self.smoke_particles = [p for p in self.smoke_particles if p.alive]
        self.ember_particles = [p for p in self.ember_particles if p.alive]

        # ── Spawn fire particles ──────────────────────────────────────────────
        if temp_ratio > 0.03:
            width = 18 + int(65 * temp_ratio)
            height_mul = 0.5 + 1.4 * temp_ratio
            rate = 6.0 * temp_ratio
            self._spawn_acc += rate
            to_spawn = min(int(self._spawn_acc), MAX_FIRE_PARTICLES - len(self.fire_particles))
            self._spawn_acc -= to_spawn

            for _ in range(max(0, to_spawn)):
                x = self.cx + random.uniform(-width / 2, width / 2)
                y = self.cy + random.uniform(-6, 6)
                vx = random.uniform(-0.7, 0.7)
                vy = -2.2 * height_mul + random.uniform(-1.0, 1.0)
                lt = int(32 * height_mul + random.uniform(0, 16))
                sz = random.randint(5, 10)
                # Color based on temp
                c_start = (255, 230, 80) if temp_ratio > 0.4 else (255, 140, 30)
                c_end   = (190, 25, 5)
                p = Particle(x, y, vx, vy, lt, sz, c_start, c_end)
                self.fire_particles.append(p)

        # ── Spawn smoke ───────────────────────────────────────────────────────
        smoke_chance = 0.12 if temp_ratio < 0.25 else 0.05
        if random.random() < smoke_chance and len(self.smoke_particles) < MAX_SMOKE_PARTICLES:
            p = Particle(
                self.cx + random.uniform(-15, 15),
                self.cy - 12,
                random.uniform(-0.4, 0.4),
                random.uniform(-1.1, -0.6),
                random.randint(60, 110),
                random.randint(6, 12),
                (95, 90, 85),
                (45, 42, 40),
                grows=True
            )
            self.smoke_particles.append(p)

        # ── Ambient embers ────────────────────────────────────────────────────
        if temp_ratio > 0.35 and random.random() < 0.08 and len(self.ember_particles) < MAX_EMBER_PARTICLES:
            self.ember_particles.append(Particle(
                self.cx + random.uniform(-20, 20),
                self.cy + random.uniform(-4, 4),
                random.uniform(-1.2, 1.2),
                random.uniform(-2.5, -0.8),
                random.randint(45, 80),
                3,
                (255, 180, 40),
                (255, 60, 0)
            ))

    def draw(self, surface):
        self._fire_surf.fill((0, 0, 0, 0))

        # 1. Glowing ember bed in log pile
        temp_ratio = self.temperature / 100.0
        if temp_ratio > 0.02:
            bed_w = int(50 + 60 * temp_ratio)
            ember_col = (
                min(255, int(150 + 105 * temp_ratio)),
                max(20, int(30 + 120 * temp_ratio)),
                10,
                int(160 + 60 * math.sin(self._glow_phase))
            )
            pygame.draw.ellipse(self._fire_surf, ember_col,
                                (self.cx - bed_w // 2, self.cy - 4, bed_w, 18))

        # 2. Smoke particles
        for p in self.smoke_particles:
            col = p.color()
            sz = p.current_size()
            alpha = int(140 * p.ratio)
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], alpha), (int(p.x), int(p.y)), sz)

        # 3. Fire particles
        for p in self.fire_particles:
            col = p.color()
            sz = p.current_size()
            alpha = int(225 * p.ratio)
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], alpha), (int(p.x), int(p.y)), sz)

        # 4. Embers
        for p in self.ember_particles:
            col = p.color()
            pygame.draw.circle(self._fire_surf, (col[0], col[1], col[2], 240), (int(p.x), int(p.y)), p.size)

        surface.blit(self._fire_surf, (0, 0))

    def draw_ambient_light(self, surface):
        """Draws atmospheric warm illumination cast onto the scene."""
        temp_ratio = self.temperature / 100.0
        if temp_ratio <= 0.02:
            return

        self._light_surf.fill((0, 0, 0, 0))
        # Pulsing flicker
        flicker = 1.0 + 0.08 * math.sin(self._glow_phase * 2.3) + 0.04 * math.sin(self._glow_phase * 4.7)
        radius = int((90 + 260 * temp_ratio) * flicker)
        max_alpha = int(110 * temp_ratio)

        for r in range(radius, 0, -18):
            step_alpha = int(max_alpha * (1.0 - (r / radius) ** 1.8))
            if step_alpha > 0:
                pygame.draw.circle(self._light_surf, (255, 140, 20, step_alpha), (self.cx, self.cy - 10), r)

        surface.blit(self._light_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
