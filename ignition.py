"""
ignition.py — Tactile, realistic ignition mini-games:
1. Match: Drag across striker with the right speed, cup hand (RMB) in wind/rain, bring to tinder.
2. Lighter: Scroll wheel down (spin flint) + hold LMB (gas lever) -> torch flame, carry to tinder.
3. Flint & Steel: Rapid downward strikes over tinder nest, then blow (SPACE) on glowing ember.
"""
import pygame
import random
import math
from sound_synth import sounds
from ui import draw_text, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_TINY

TINDER_RECT = pygame.Rect(320, 360, 160, 90)

class BaseIgnition:
    def __init__(self, material_key, weather):
        self.material_key = material_key
        self.weather = weather
        self.success = False
        self.failed = False
        self.fail_reason = ""
        self.hint = ""
        self.hint_color = (255, 215, 100)

    def update(self, dt):
        pass

    def handle_event(self, event):
        pass

    def draw(self, surface):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 1. MATCH IGNITION
# ─────────────────────────────────────────────────────────────────────────────
class MatchIgnition(BaseIgnition):
    def __init__(self, material_key, weather):
        super().__init__(material_key, weather)
        self.box_rect = pygame.Rect(480, 420, 260, 130)
        self.striker_rect = pygame.Rect(495, 455, 230, 45)

        self.match_pos = [600, 320]
        self.prev_pos = [600, 320]
        self.holding = False
        self.shielding = False  # RMB held to shield from wind/rain

        self.lit = False
        self.burn_time = 7.5    # seconds of flame before burning out
        self.broken = False
        self.tinder_timer = 0.0 # time touching tinder
        self.unshielded_wind_time = 0.0

        self.flame_particles = []
        self.swipe_distance = 0.0

    def handle_event(self, event):
        if self.failed or self.success or self.broken:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # LMB
                self.holding = True
                self.match_pos = list(event.pos)
                self.prev_pos = list(event.pos)
                self.swipe_distance = 0.0
            elif event.button == 3: # RMB
                self.shielding = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.holding = False
            elif event.button == 3:
                self.shielding = False

        elif event.type == pygame.MOUSEMOTION:
            if self.holding:
                self.match_pos = list(event.pos)

    def update(self, dt):
        if self.failed or self.success:
            return

        mx, my = self.match_pos
        px, py = self.prev_pos
        vx = (mx - px) / max(0.001, dt)
        vy = (my - py) / max(0.001, dt)
        speed = math.hypot(vx, vy)
        self.prev_pos = [mx, my]

        head_rect = pygame.Rect(mx - 8, my - 8, 16, 16)

        # ── Strike logic (if not lit) ─────────────────────────────────────────
        if not self.lit and not self.broken:
            if self.holding and self.striker_rect.colliderect(head_rect):
                self.swipe_distance += math.hypot(mx - px, my - py)

                if speed > 2300:
                    # Snapped!
                    self.broken = True
                    sounds.play('match_break')
                    self.failed = True
                    self.fail_reason = "Слишком резко! Спичка сломалась."
                    self.hint = "Нужен плавный, уверенный чирк, а не бешеный рывок."
                    self.hint_color = (255, 80, 70)
                elif speed > 450 and self.swipe_distance > 70:
                    # Ignited!
                    self.lit = True
                    sounds.play('match_scratch')
                    sounds.play('match_light')
                    self.hint = "Спичка горит! Неси её к растопке костра (слева внизу)!"
                    self.hint_color = (120, 240, 120)
                elif speed > 50:
                    # Friction sound
                    if random.random() < 0.2:
                        sounds.play('match_scratch')
                    self.hint = "Черкай резче по коричневой полосе коробка!"
                    self.hint_color = (255, 200, 80)
            else:
                if not self.lit and not self.holding:
                    self.hint = "Зажми ЛКМ и чиркни спичкой по коробку (справа)!"
                    self.hint_color = (230, 210, 160)

        # ── Burning logic (if lit) ────────────────────────────────────────────
        if self.lit:
            self.burn_time -= dt
            if self.burn_time <= 0:
                self.lit = False
                sounds.play('blow')
                self.failed = True
                self.fail_reason = "Спичка догорела до пальцев и погасла."
                self.hint = "Нужно было быстрее нести огонь к костру!"
                self.hint_color = (255, 90, 70)
                return

            # Wind / rain hazard
            needs_shield = self.weather.is_strong_wind or self.weather.is_raining
            if needs_shield:
                if not self.shielding:
                    self.unshielded_wind_time += dt
                    self.hint = "Ветер задувает спичку! ЗАЖМИ ПКМ, чтобы прикрыть пламя ладонью!"
                    self.hint_color = (255, 100, 80)
                    if self.unshielded_wind_time > 0.8:
                        self.lit = False
                        sounds.play('blow')
                        self.failed = True
                        self.fail_reason = "Ветер или дождь задул спичку!"
                        self.hint = "В непогоду обязательно прикрывай спичку ладонью (удерживай ПКМ)!"
                        self.hint_color = (255, 80, 70)
                        return
                else:
                    self.unshielded_wind_time = max(0.0, self.unshielded_wind_time - dt * 2)
                    self.hint = "Ладонь защищает пламя. Неси спичку к растопке костра!"
                    self.hint_color = (130, 230, 130)

            # Check touching tinder nest
            if TINDER_RECT.colliderect(head_rect):
                self.tinder_timer += dt
                self.hint = f"Поджигаем растопку... ({int(self.tinder_timer * 100)}%)"
                self.hint_color = (255, 220, 50)
                if self.tinder_timer >= 0.7:
                    # Ignite fire!
                    self.success = True
                    sounds.play('match_light')
            else:
                self.tinder_timer = max(0.0, self.tinder_timer - dt)

            # Spawn flame particles on match tip
            if random.random() < 0.8:
                self.flame_particles.append([
                    mx + random.uniform(-3, 3),
                    my - 8 + random.uniform(-4, 0),
                    random.uniform(-0.6, 0.6),
                    random.uniform(-1.8, -0.6),
                    random.uniform(0.15, 0.35)
                ])

        # Update particles
        alive_flames = []
        for p in self.flame_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= dt
            if p[4] > 0:
                alive_flames.append(p)
        self.flame_particles = alive_flames

    def draw(self, surface):
        # 1. Matchbox
        bx, by, bw, bh = self.box_rect
        pygame.draw.rect(surface, (45, 55, 75), self.box_rect, border_radius=8)
        pygame.draw.rect(surface, (70, 85, 115), self.box_rect, width=2, border_radius=8)
        draw_text(surface, "СПИЧКИ", bx + bw // 2, by + 12, size=FONT_SIZE_SMALL,
                  color=(220, 225, 235), anchor="midtop")

        # Striker strip
        sx, sy, sw, sh = self.striker_rect
        pygame.draw.rect(surface, (85, 45, 30), self.striker_rect, border_radius=4)
        for i in range(sx + 5, sx + sw - 5, 8):
            pygame.draw.line(surface, (115, 60, 40), (i, sy + 3), (i + 4, sy + sh - 3), 1)
        draw_text(surface, "ПОЛОСА ЧЕРКАША (чиркай здесь)", sx + sw // 2, sy + sh // 2,
                  size=FONT_SIZE_TINY, color=(200, 160, 140), anchor="center")

        # 2. Tinder nest indicator
        tx, ty, tw, th = TINDER_RECT
        pygame.draw.rect(surface, (65, 48, 28), TINDER_RECT, border_radius=8)
        pygame.draw.rect(surface, (130, 95, 50), TINDER_RECT, width=2, border_radius=8)
        draw_text(surface, "РАСТОПКА КОСТРА", tx + tw // 2, ty + 12, size=FONT_SIZE_TINY,
                  color=(230, 190, 120), anchor="midtop")
        draw_text(surface, "(подноси огонь сюда)", tx + tw // 2, ty + 30, size=FONT_SIZE_TINY,
                  color=(160, 130, 85), anchor="midtop")

        # 3. Flame particles
        for p in self.flame_particles:
            alpha = int(255 * (p[4] / 0.35))
            sz = int(10 * (p[4] / 0.35))
            if sz > 0:
                s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                col = (255, 200, 50, alpha) if random.random() < 0.6 else (255, 90, 20, alpha)
                pygame.draw.circle(s, col, (sz, sz), sz)
                surface.blit(s, (int(p[0]) - sz, int(p[1]) - sz))

        # 4. Shielding hand representation
        mx, my = self.match_pos
        if self.shielding:
            hand_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.arc(hand_surf, (220, 170, 130, 180), (10, 10, 60, 60), 0.5, 3.8, 8)
            surface.blit(hand_surf, (mx - 40, my - 45))
            draw_text(surface, "Ладонь защищает (ПКМ)", mx, my - 50, size=FONT_SIZE_TINY,
                      color=(160, 220, 160), anchor="midbottom")

        # 5. Match stick
        if self.broken:
            # Broken stick
            pygame.draw.line(surface, (190, 165, 125), (mx, my), (mx + 25, my + 45), 4)
            pygame.draw.line(surface, (190, 165, 125), (mx + 28, my + 48), (mx + 45, my + 75), 4)
        else:
            # Whole stick
            pygame.draw.line(surface, (200, 175, 130), (mx, my), (mx + 50, my + 50), 5)
            # Sulfur head
            head_col = (50, 45, 45) if self.lit else (180, 40, 30)
            pygame.draw.circle(surface, head_col, (mx, my), 6)

        # 6. Burn timer bar if lit
        if self.lit:
            ratio = max(0.0, self.burn_time / 7.5)
            bw = 140
            pygame.draw.rect(surface, (40, 30, 20), (mx - bw // 2, my + 60, bw, 8), border_radius=3)
            pygame.draw.rect(surface, (255, 140, 20), (mx - bw // 2, my + 60, int(bw * ratio), 8), border_radius=3)

        # 7. Help banner
        draw_text(surface, self.hint, 400, 560, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center")


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIGHTER IGNITION
# ─────────────────────────────────────────────────────────────────────────────
class LighterIgnition(BaseIgnition):
    def __init__(self, material_key, weather):
        super().__init__(material_key, weather)
        self.lighter_pos = [580, 380]
        self.holding_gas = False   # LMB held
        self.flint_spun = False
        self.spark_timer = 0.0
        self.lit = False
        self.fuel = 1.0           # 100% fuel
        self.tinder_timer = 0.0
        self.sparks = []
        self.flame_particles = []

    def handle_event(self, event):
        if self.failed or self.success:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # LMB holds gas lever
                self.holding_gas = True
                sounds.play('lighter_spin')
            elif event.button == 5 or event.button == 4: # Mouse Wheel
                # Spin the flint wheel!
                self.flint_spun = True
                self.spark_timer = 0.55
                sounds.play('lighter_spin')
                self._spawn_sparks()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.holding_gas = False
                self.lit = False

        elif event.type == pygame.MOUSEMOTION:
            if self.holding_gas or self.lit:
                self.lighter_pos = list(event.pos)

    def _spawn_sparks(self):
        lx, ly = self.lighter_pos
        for _ in range(12):
            self.sparks.append([
                lx - 10 + random.uniform(-4, 4),
                ly - 40 + random.uniform(-4, 4),
                random.uniform(-2.5, 1.5),
                random.uniform(-4.0, -1.0),
                random.uniform(0.1, 0.28)
            ])

    def update(self, dt):
        if self.failed or self.success:
            return

        if self.spark_timer > 0:
            self.spark_timer -= dt

        # Ignite check: flint spun while gas held OR gas pressed while sparks active
        if self.holding_gas and self.spark_timer > 0 and not self.lit and self.fuel > 0:
            self.lit = True
            sounds.play('lighter_whoosh')

        # Burn fuel while flame is on
        if self.lit:
            self.fuel -= dt * 0.07 # ~14 seconds continuous burn
            if self.fuel <= 0:
                self.lit = False
                self.failed = True
                self.fail_reason = "В зажигалке закончился газ!"
                self.hint = "Слишком долго держал газ без поджига."
                self.hint_color = (255, 80, 70)
                return

            self.hint = "Зажигалка горит! Подноси сопло к растопке костра (слева)!"
            self.hint_color = (120, 240, 120)

            # Check touching tinder
            lx, ly = self.lighter_pos
            flame_rect = pygame.Rect(lx - 25, ly - 75, 30, 40)
            if TINDER_RECT.colliderect(flame_rect):
                self.tinder_timer += dt
                self.hint = f"Растопка занимается... ({int(self.tinder_timer * 100)}%)"
                if self.tinder_timer >= 0.8:
                    self.success = True
                    sounds.play('match_light')
            else:
                self.tinder_timer = max(0.0, self.tinder_timer - dt)

            # Flame particles
            if random.random() < 0.9:
                self.flame_particles.append([
                    lx - 12 + random.uniform(-4, 4),
                    ly - 50 + random.uniform(-3, 0),
                    random.uniform(-0.4, 0.4),
                    random.uniform(-2.5, -1.2),
                    random.uniform(0.12, 0.26)
                ])
        else:
            if not self.holding_gas:
                self.hint = "1. КРУТНИ КОЛЕСИКО МЫШИ (чиркнуть колесико) + 2. ЗАЖМИ ЛКМ (подать газ)!"
                self.hint_color = (240, 210, 150)
            else:
                self.hint = "Газ шипит! Крутни КОЛЕСИКО МЫШИ, чтобы высечь искру!"
                self.hint_color = (255, 180, 60)

        # Update sparks
        alive_sparks = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[3] += 8.0 * dt # gravity
            s[4] -= dt
            if s[4] > 0:
                alive_sparks.append(s)
        self.sparks = alive_sparks

        # Update flame particles
        alive_flames = []
        for p in self.flame_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= dt
            if p[4] > 0:
                alive_flames.append(p)
        self.flame_particles = alive_flames

    def draw(self, surface):
        # 1. Tinder nest
        tx, ty, tw, th = TINDER_RECT
        pygame.draw.rect(surface, (65, 48, 28), TINDER_RECT, border_radius=8)
        pygame.draw.rect(surface, (130, 95, 50), TINDER_RECT, width=2, border_radius=8)
        draw_text(surface, "РАСТОПКА КОСТРА", tx + tw // 2, ty + 12, size=FONT_SIZE_TINY,
                  color=(230, 190, 120), anchor="midtop")
        draw_text(surface, "(подноси огонь сюда)", tx + tw // 2, ty + 30, size=FONT_SIZE_TINY,
                  color=(160, 130, 85), anchor="midtop")

        # 2. Sparks
        for s in self.sparks:
            alpha = int(255 * (s[4] / 0.28))
            pygame.draw.circle(surface, (255, 230, 110), (int(s[0]), int(s[1])), 2)

        # 3. Flame
        for p in self.flame_particles:
            sz = int(14 * (p[4] / 0.26))
            if sz > 0:
                col = (120, 180, 255) if p[4] > 0.2 else (255, 200, 40)
                pygame.draw.circle(surface, col, (int(p[0]), int(p[1])), sz)

        # 4. Lighter body
        lx, ly = self.lighter_pos
        body_col = (190, 150, 40) if self.material_key == "birch" else (70, 75, 85)
        # Metal case
        pygame.draw.rect(surface, body_col, (lx - 25, ly - 35, 50, 85), border_radius=6)
        pygame.draw.rect(surface, (220, 220, 230), (lx - 25, ly - 35, 50, 85), width=2, border_radius=6)
        # Hood / nozzle
        pygame.draw.rect(surface, (140, 140, 150), (lx - 20, ly - 50, 22, 16), border_radius=2)
        # Flint wheel
        wheel_col = (230, 210, 50) if self.spark_timer > 0 else (180, 180, 190)
        pygame.draw.circle(surface, wheel_col, (lx + 8, ly - 42), 8)
        pygame.draw.circle(surface, (90, 90, 100), (lx + 8, ly - 42), 8, 2)
        # Gas thumb button
        btn_y = ly - 36 if self.holding_gas else ly - 42
        pygame.draw.rect(surface, (200, 50, 40), (lx + 2, btn_y, 16, 8), border_radius=2)

        # Fuel gauge
        pygame.draw.rect(surface, (30, 30, 30), (lx - 18, ly + 25, 36, 6), border_radius=2)
        pygame.draw.rect(surface, (60, 180, 240), (lx - 18, ly + 25, int(36 * self.fuel), 6), border_radius=2)

        draw_text(surface, self.hint, 400, 560, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center")


# ─────────────────────────────────────────────────────────────────────────────
# 3. FLINT & STEEL IGNITION
# ─────────────────────────────────────────────────────────────────────────────
class FlintIgnition(BaseIgnition):
    def __init__(self, material_key, weather):
        super().__init__(material_key, weather)
        self.striker_pos = [400, 240]
        self.prev_pos = [400, 240]
        self.holding = False

        self.ember_heat = 0.0      # 0 to 1.0 (from sparks)
        self.ember_ready = False   # glowing ember formed, now needs breath
        self.blown_ratio = 0.0     # 0 to 1.0 from blowing

        self.sparks = []
        self.smoke_particles = []

    def handle_event(self, event):
        if self.failed or self.success:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.holding = True
            self.striker_pos = list(event.pos)
            self.prev_pos = list(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.holding = False

        elif event.type == pygame.MOUSEMOTION and self.holding:
            self.striker_pos = list(event.pos)

    def _strike(self):
        sounds.play('flint_clink')
        # Spawn generous shower of sparks flying into tinder nest
        for _ in range(16):
            self.sparks.append([
                self.striker_pos[0] + random.uniform(-8, 8),
                self.striker_pos[1] + random.uniform(-6, 6),
                random.uniform(-1.5, 1.5),
                random.uniform(2.5, 7.0),
                random.uniform(0.2, 0.45)
            ])

    def update(self, dt):
        if self.failed or self.success:
            return

        sx, sy = self.striker_pos
        px, py = self.prev_pos
        vy = (sy - py) / max(0.001, dt)
        self.prev_pos = [sx, sy]

        # Strike check: sharp downward slash across the flint edge (y ~ 320)
        if self.holding and not self.ember_ready:
            if py < 320 <= sy and vy > 650:
                self._strike()
                self.ember_heat += random.uniform(0.18, 0.28)
                self.hint = f"Удар! Искры сыплются в трут ({int(self.ember_heat * 100)}%)"
                self.hint_color = (255, 200, 60)
                if self.ember_heat >= 1.0:
                    self.ember_ready = True
                    sounds.play('match_light')
            else:
                self.ember_heat = max(0.0, self.ember_heat - dt * 0.08)
                if not self.ember_ready:
                    self.hint = "Зажми ЛКМ и сделай РЕЗКИЙ ВЗМАХ МЫШЬЮ СВЕРХУ ВНИЗ по кремню!"
                    self.hint_color = (230, 210, 160)

        # Blowing stage
        if self.ember_ready:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                self.blown_ratio += dt * 0.65
                if random.random() < 0.15:
                    sounds.play('blow')
                self.hint = f"Раздувай угли! Зажми ПРОБЕЛ ({int(self.blown_ratio * 100)}%)"
                self.hint_color = (255, 140, 40)
                if self.blown_ratio >= 1.0:
                    self.success = True
                    sounds.play('match_light')
            else:
                self.blown_ratio = max(0.0, self.blown_ratio - dt * 0.15)
                self.hint = "УГОЛЁК ЗАТЛЕЛ! ЗАЖМИ ПРОБЕЛ, ЧТОБЫ РАЗДУТЬ ЕГО В ПЛАМЯ!"
                self.hint_color = (255, 190, 50)

            # Smoke from ember
            if random.random() < 0.5:
                tx, ty, tw, th = TINDER_RECT
                self.smoke_particles.append([
                    tx + tw // 2 + random.uniform(-15, 15),
                    ty + th // 2 + random.uniform(-10, 10),
                    random.uniform(-0.5, 0.5),
                    random.uniform(-1.5, -0.7),
                    random.uniform(0.4, 0.8)
                ])

        # Update sparks
        alive_sparks = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= dt
            if s[4] > 0:
                alive_sparks.append(s)
        self.sparks = alive_sparks

        # Update smoke
        alive_smoke = []
        for m in self.smoke_particles:
            m[0] += m[2]
            m[1] += m[3]
            m[4] -= dt
            if m[4] > 0:
                alive_smoke.append(m)
        self.smoke_particles = alive_smoke

    def draw(self, surface):
        # 1. Tinder nest
        tx, ty, tw, th = TINDER_RECT
        pygame.draw.rect(surface, (65, 48, 28), TINDER_RECT, border_radius=8)
        pygame.draw.rect(surface, (130, 95, 50), TINDER_RECT, width=2, border_radius=8)

        # Ember glow in tinder
        if self.ember_ready:
            glow_r = int(12 + 18 * self.blown_ratio)
            s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 90, 10, 180), (glow_r, glow_r), glow_r)
            pygame.draw.circle(s, (255, 230, 80, 230), (glow_r, glow_r), glow_r // 2)
            surface.blit(s, (tx + tw // 2 - glow_r, ty + th // 2 - glow_r))

        draw_text(surface, "ГНЕЗДО РАСТОПКИ (ТРУТ)", tx + tw // 2, ty + 10,
                  size=FONT_SIZE_TINY, color=(230, 190, 120), anchor="midtop")

        # 2. Flint stone (кремень)
        pygame.draw.polygon(surface, (75, 75, 80), [(370, 310), (430, 310), (415, 345), (385, 345)])
        pygame.draw.polygon(surface, (120, 120, 130), [(370, 310), (430, 310), (415, 345), (385, 345)], 2)
        draw_text(surface, "КРЕМЕНЬ", 400, 320, size=FONT_SIZE_TINY,
                  color=(200, 205, 215), anchor="center")

        # 3. Steel striker in hand (кресало)
        sx, sy = self.striker_pos
        pygame.draw.rect(surface, (180, 185, 195), (sx - 28, sy - 10, 56, 18), border_radius=4)
        pygame.draw.rect(surface, (230, 235, 245), (sx - 28, sy - 10, 56, 18), width=2, border_radius=4)
        draw_text(surface, "КРЕСАЛО", sx, sy - 1, size=FONT_SIZE_TINY,
                  color=(40, 45, 55), anchor="center")

        # 4. Sparks
        for s in self.sparks:
            pygame.draw.circle(surface, (255, 220, 90), (int(s[0]), int(s[1])), 2)

        # 5. Smoke
        for m in self.smoke_particles:
            sz = int(12 * (1.0 - m[4] / 0.8)) + 4
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (180, 180, 180, 100), (sz, sz), sz)
            surface.blit(s, (int(m[0]) - sz, int(m[1]) - sz))

        # 6. Heat progress bar
        if not self.ember_ready:
            bw = 200
            pygame.draw.rect(surface, (30, 25, 20), (300, 470, bw, 10), border_radius=3)
            pygame.draw.rect(surface, (255, 160, 30), (300, 470, int(bw * self.ember_heat), 10), border_radius=3)

        draw_text(surface, self.hint, 400, 560, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center")
