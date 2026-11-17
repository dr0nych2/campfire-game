"""
ignition.py — Tactile, realistic ignition mini-games with authentic pixel-art:
1. Match: Hand-held match with real burn stages (1..5), strike along matchbox striker edge, cup with RMB.
2. Lighter: Zippo lighter with animated flame loop (1..4), flick flint wheel + hold LMB.
3. Flint & Steel: Downward strike slash with spark bursts (1..4), blow (SPACE) with real breath on ember.
"""
import pygame
import random
import math
from sound_synth import sounds
from textures import TextureManager
from ui import draw_text, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_TINY

TINDER_RECT = pygame.Rect(310, 345, 180, 90)


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
        # Matchbox at bottom-right of screen
        self.box_rect = pygame.Rect(530, 410, 230, 130)
        # Striker strip bounds mapped precisely to brown side of matchbox texture
        # Texture 186x99: striker is x: 71..181, y: 8..84
        bw, bh = self.box_rect.width, self.box_rect.height
        bx, by = self.box_rect.x, self.box_rect.y
        self.striker_rect = pygame.Rect(
            bx + int(bw * 71 / 186),
            by + int(bh * 10 / 99),
            int(bw * 105 / 186),
            int(bh * 70 / 99)
        )

        self.match_pos = [620, 260]
        self.prev_pos = [620, 260]
        self.holding = False
        self.shielding = False  # RMB held to shield from wind/rain

        self.lit = False
        self.burn_time = 7.5    # seconds of flame
        self.broken = False
        self.tinder_timer = 0.0
        self.unshielded_wind_time = 0.0

        self.flame_particles = []
        self.sparks = []
        self.swipe_distance = 0.0
        self.burn_frame = 0

    def handle_event(self, event):
        if self.failed or self.success or self.broken:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # LMB
                self.holding = True
                self.match_pos = list(event.pos)
                self.prev_pos = list(event.pos)
                self.swipe_distance = 0.0
            elif event.button == 3:  # RMB
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

        head_rect = pygame.Rect(mx - 12, my - 12, 24, 24)

        # ── Strike logic (if not lit) ─────────────────────────────────────────
        if not self.lit and not self.broken:
            if self.holding and self.striker_rect.colliderect(head_rect):
                self.swipe_distance += math.hypot(mx - px, my - py)

                # Too violent -> break match
                if speed > 2400:
                    self.broken = True
                    sounds.play('match_break')
                    self.failed = True
                    self.fail_reason = "Слишком резкий удар! Спичка сломалась пополам."
                    self.hint = "Спичка сломалась! Нажми 'Начать заново' (ESC)."
                    self.hint_color = (255, 70, 60)
                    return

                # Normal strike speed: 300 to 2200 px/sec
                if speed > 320 and self.swipe_distance > 40:
                    sounds.play('match_scratch')
                    # Spark particles
                    for _ in range(8):
                        self.sparks.append([
                            mx + random.uniform(-6, 6),
                            my + random.uniform(-6, 6),
                            random.uniform(-1.5, 1.5),
                            random.uniform(-2.5, 1.0),
                            random.uniform(0.12, 0.28)
                        ])

                    # Chance to catch fire
                    prob = 0.65
                    if self.weather.is_raining:
                        prob = 0.35 if self.shielding else 0.12
                    elif self.weather.is_strong_wind:
                        prob = 0.45 if self.shielding else 0.20

                    if random.random() < prob:
                        self.lit = True
                        sounds.play('match_light')
                        self.hint = "Спичка горит! Неси пламя к растопке костра (слева)!"
                        self.hint_color = (255, 215, 80)
            else:
                self.swipe_distance = 0.0
                self.hint = "Зажми ЛКМ и чиркни спичкой по коробку (справа)!"
                self.hint_color = (240, 215, 160)

        # ── Burning logic (if lit) ───────────────────────────────────────────
        if self.lit:
            self.burn_time -= dt
            # 6 animation frames across 7.5 seconds
            burn_ratio = max(0.0, min(1.0, 1.0 - self.burn_time / 7.5))
            self.burn_frame = min(5, int(burn_ratio * 6))

            if self.burn_time <= 0:
                self.failed = True
                self.fail_reason = "Спичка догорела до пальцев и погасла."
                self.hint = "Спичка догорела! Нажми 'Начать заново' (ESC)."
                self.hint_color = (255, 80, 70)
                return

            # Weather effects on exposed match
            if self.weather.is_raining or self.weather.is_strong_wind:
                if not self.shielding:
                    self.unshielded_wind_time += dt
                    self.hint = "ВЕТЕР/ДОЖДЬ СДУВАЕТ ПЛАМЯ! ЗАЖМИ ПКМ, ЧТОБЫ ПРИКРЫТЬ ЛАДОНЬЮ!"
                    self.hint_color = (255, 140, 40)
                    if self.unshielded_wind_time > 1.2:
                        self.failed = True
                        self.fail_reason = "Порыв ветра задул незащищённую спичку."
                        self.hint = "Пламя задуло ветром! Защищай спичку ладонью (ПКМ)."
                        self.hint_color = (255, 80, 70)
                        return
                else:
                    self.unshielded_wind_time = max(0.0, self.unshielded_wind_time - dt * 2)
                    self.hint = "Ладонь защищает пламя. Неси спичку к растопке костра!"
                    self.hint_color = (130, 230, 130)

            # Check touching tinder nest
            if TINDER_RECT.colliderect(head_rect):
                self.tinder_timer += dt
                self.hint = f"Поджигаем растопку... ({int(self.tinder_timer / 0.65 * 100)}%)"
                self.hint_color = (255, 220, 50)
                if self.tinder_timer >= 0.65:
                    self.success = True
                    sounds.play('match_light')
            else:
                self.tinder_timer = max(0.0, self.tinder_timer - dt)

        # Update sparks
        alive_sparks = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= dt
            if s[4] > 0:
                alive_sparks.append(s)
        self.sparks = alive_sparks

    def draw(self, surface):
        # 1. Tinder nest in campfire hearth
        tx, ty, tw, th = TINDER_RECT
        nest_tex = TextureManager.get('tinder_nest', (tw, th))
        if nest_tex:
            surface.blit(nest_tex, (tx, ty))

        # Warm glow on nest if tinder is igniting
        if self.tinder_timer > 0:
            glow_r = int(25 + 35 * (self.tinder_timer / 0.65))
            glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 140, 30, 120), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow_s, (255, 230, 90, 180), (glow_r, glow_r), glow_r // 2)
            surface.blit(glow_s, (tx + tw // 2 - glow_r, ty + th // 2 - glow_r))

        draw_text(surface, "Гнездо растопки", tx + tw // 2, ty - 18, size=FONT_SIZE_SMALL,
                  color=(255, 220, 160), anchor="midtop", shadow=True)

        # 2. Matchbox at bottom-right
        bx, by, bw, bh = self.box_rect
        box_tex = TextureManager.get('matchbox', (bw, bh))
        if box_tex:
            # Drop shadow
            shadow_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            shadow_s.fill((0, 0, 0, 120))
            surface.blit(box_tex, (bx, by))

        # Striker highlight glow when match is close or hovered
        mx, my = self.match_pos
        sx, sy, sw, sh = self.striker_rect
        dist_to_striker = math.hypot(mx - (sx + sw // 2), my - (sy + sh // 2))
        if not self.lit and dist_to_striker < 150:
            glow_alpha = int(max(40, min(140, (150 - dist_to_striker) * 1.5)))
            glint = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(glint, (255, 200, 80, glow_alpha), (0, 0, sw, sh), width=2, border_radius=4)
            surface.blit(glint, (sx, sy))

        # 3. Sparks from strike
        for s in self.sparks:
            alpha = int(255 * (s[4] / 0.28))
            pygame.draw.circle(surface, (255, 230, 110), (int(s[0]), int(s[1])), 2)

        # 4. Shielding hand representation
        if self.shielding and self.lit:
            cup_s = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(cup_s, (220, 175, 130, 70), (60, 60), 55)
            pygame.draw.circle(cup_s, (255, 210, 150, 130), (60, 60), 55, width=3)
            surface.blit(cup_s, (mx - 60, my - 60))
            draw_text(surface, "Ладонь защищает от ветра (ПКМ)", mx, my - 68,
                      size=FONT_SIZE_TINY, color=(160, 230, 160), anchor="midbottom", shadow=True)

        # 5. Hand holding match (authentic pixel-art)
        if not self.lit and not self.broken:
            hand_unlit = TextureManager.get('match_hand_unlit')
            if hand_unlit:
                # Sulfur head is at (111, 63) in unlit sprite
                surface.blit(hand_unlit, (mx - 111, my - 63))
            else:
                pygame.draw.line(surface, (200, 175, 130), (mx, my), (mx + 45, my + 50), 4)
                pygame.draw.circle(surface, (180, 40, 30), (mx, my), 5)
        elif self.lit:
            hand_lit = TextureManager.get(f'match_burn_{self.burn_frame + 1}')
            if hand_lit:
                # Flame tip is at (111, 10) in burning sprite
                surface.blit(hand_lit, (mx - 111, my - 10))
            else:
                pygame.draw.line(surface, (120, 95, 70), (mx, my), (mx + 45, my + 50), 4)
                pygame.draw.circle(surface, (255, 180, 40), (mx, my), 8)

            # Burn time indicator bar
            ratio = max(0.0, self.burn_time / 7.5)
            bw = 100
            pygame.draw.rect(surface, (30, 20, 15), (mx - bw // 2, my + 75, bw, 6), border_radius=3)
            bar_col = (255, 180, 40) if ratio > 0.3 else (255, 60, 40)
            pygame.draw.rect(surface, bar_col, (mx - bw // 2, my + 75, int(bw * ratio), 6), border_radius=3)

        # 6. Help banner at bottom
        draw_text(surface, self.hint, 400, 565, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center", shadow=True)


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
        self.flame_frame = 0.0

    def handle_event(self, event):
        if self.failed or self.success:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # LMB holds gas lever
                self.holding_gas = True
                sounds.play('lighter_spin')
            elif event.button == 5 or event.button == 4:  # Mouse Wheel
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
                lx + random.uniform(-10, 10),
                ly - 30 + random.uniform(-6, 6),
                random.uniform(-1.8, 1.8),
                random.uniform(-3.5, 0.5),
                random.uniform(0.12, 0.28)
            ])

    def update(self, dt):
        if self.failed or self.success:
            return

        if self.spark_timer > 0:
            self.spark_timer -= dt

        # Ignition condition
        if self.holding_gas and self.spark_timer > 0 and not self.lit and self.fuel > 0:
            prob = 0.85
            if self.weather.is_raining:
                prob = 0.40
            if random.random() < prob:
                self.lit = True
                sounds.play('match_light')

        # Burn logic
        if self.lit:
            self.fuel -= dt * 0.06
            self.flame_frame = (self.flame_frame + dt * 10.0) % 4.0

            if self.fuel <= 0:
                self.lit = False
                self.failed = True
                self.fail_reason = "В зажигалке закончился газ!"
                self.hint = "Газ закончился! Нажми 'Начать заново' (ESC)."
                self.hint_color = (255, 70, 70)
                return

            self.hint = "Зажигалка горит! Подноси пламя к растопке костра (слева)!"
            self.hint_color = (130, 240, 130)

            # Check touching tinder
            lx, ly = self.lighter_pos
            flame_rect = pygame.Rect(lx - 35, ly - 50, 45, 45)
            if TINDER_RECT.colliderect(flame_rect):
                self.tinder_timer += dt
                self.hint = f"Растопка занимается... ({int(self.tinder_timer / 0.75 * 100)}%)"
                if self.tinder_timer >= 0.75:
                    self.success = True
                    sounds.play('match_light')
            else:
                self.tinder_timer = max(0.0, self.tinder_timer - dt)
        else:
            if not self.holding_gas:
                self.hint = "1. КРУТНИ КОЛЕСИКО МЫШИ (искра) + 2. ЗАЖМИ ЛКМ (подать газ)!"
                self.hint_color = (240, 215, 160)
            else:
                self.hint = "Газ шипит! Крутни КОЛЕСИКО МЫШИ, чтобы высечь искру!"
                self.hint_color = (255, 185, 60)

        # Update sparks
        alive_sparks = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[3] += 8.0 * dt
            s[4] -= dt
            if s[4] > 0:
                alive_sparks.append(s)
        self.sparks = alive_sparks

    def draw(self, surface):
        # 1. Tinder nest
        tx, ty, tw, th = TINDER_RECT
        nest_tex = TextureManager.get('tinder_nest', (tw, th))
        if nest_tex:
            surface.blit(nest_tex, (tx, ty))

        if self.tinder_timer > 0:
            glow_r = int(25 + 35 * (self.tinder_timer / 0.75))
            glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 140, 30, 120), (glow_r, glow_r), glow_r)
            surface.blit(glow_s, (tx + tw // 2 - glow_r, ty + th // 2 - glow_r))

        draw_text(surface, "Гнездо растопки", tx + tw // 2, ty - 18, size=FONT_SIZE_SMALL,
                  color=(255, 220, 160), anchor="midtop", shadow=True)

        # 2. Sparks
        for s in self.sparks:
            pygame.draw.circle(surface, (255, 230, 110), (int(s[0]), int(s[1])), 2)

        # 3. Zippo lighter body & flame
        lx, ly = self.lighter_pos
        lw, lh = 90, 65
        if not self.lit:
            tex = TextureManager.get('lighter_open_unlit', (lw, lh))
            if tex:
                surface.blit(tex, (lx - lw // 2, ly - lh // 2))
        else:
            frame_idx = int(self.flame_frame) % 4 + 1
            tex = TextureManager.get(f'lighter_flame_{frame_idx}', (lw, lh))
            if tex:
                surface.blit(tex, (lx - lw // 2, ly - lh // 2))

        # Fuel gauge
        pygame.draw.rect(surface, (30, 30, 30), (lx - 22, ly + 38, 44, 6), border_radius=2)
        pygame.draw.rect(surface, (60, 180, 240), (lx - 22, ly + 38, int(44 * self.fuel), 6), border_radius=2)

        draw_text(surface, self.hint, 400, 565, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center", shadow=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. FLINT & STEEL IGNITION
# ─────────────────────────────────────────────────────────────────────────────
class FlintIgnition(BaseIgnition):
    def __init__(self, material_key, weather):
        super().__init__(material_key, weather)
        self.striker_pos = [400, 220]
        self.prev_pos = [400, 220]
        self.holding = False

        self.ember_heat = 0.0
        self.ember_ready = False
        self.blown_ratio = 0.0

        self.sparks = []
        self.smoke_particles = []
        self.spark_burst_anim = 0.0

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
        self.spark_burst_anim = 0.35
        for _ in range(16):
            self.sparks.append([
                self.striker_pos[0] + random.uniform(-10, 10),
                self.striker_pos[1] + random.uniform(-8, 8),
                random.uniform(-1.8, 1.8),
                random.uniform(2.5, 6.5),
                random.uniform(0.2, 0.45)
            ])

    def update(self, dt):
        if self.failed or self.success:
            return

        if self.spark_burst_anim > 0:
            self.spark_burst_anim -= dt

        sx, sy = self.striker_pos
        px, py = self.prev_pos
        vy = (sy - py) / max(0.001, dt)
        self.prev_pos = [sx, sy]

        # Strike check: sharp downward slash across the flint edge (y ~ 310)
        if self.holding and not self.ember_ready:
            if py < 310 <= sy and vy > 600:
                self._strike()
                self.ember_heat += random.uniform(0.22, 0.32)
                self.hint = f"Удар! Искры сыплются в трут ({int(self.ember_heat * 100)}%)"
                self.hint_color = (255, 200, 60)
                if self.ember_heat >= 1.0:
                    self.ember_ready = True
                    sounds.play('match_light')
            else:
                self.ember_heat = max(0.0, self.ember_heat - dt * 0.08)
                if not self.ember_ready:
                    self.hint = "Зажми ЛКМ и сделай РЕЗКИЙ ВЗМАХ МЫШЬЮ СВЕРХУ ВНИЗ по кремню!"
                    self.hint_color = (230, 215, 160)

        # Blowing stage
        if self.ember_ready:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                self.blown_ratio += dt * 0.60
                if random.random() < 0.12:
                    sounds.play('blow')
                self.hint = f"Раздувай угли! Зажми ПРОБЕЛ ({int(self.blown_ratio * 100)}%)"
                self.hint_color = (255, 140, 40)
                if self.blown_ratio >= 1.0:
                    self.success = True
                    sounds.play('match_light')
            else:
                self.blown_ratio = max(0.0, self.blown_ratio - dt * 0.12)
                self.hint = "УГОЛЁК ЗАТЛЕЛ! ЗАЖМИ ПРОБЕЛ, ЧТОБЫ РАЗДУТЬ ЕГО В ПЛАМЯ!"
                self.hint_color = (255, 190, 50)

            # Smoke wisps
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
        nest_tex = TextureManager.get('tinder_nest', (tw, th))
        if nest_tex:
            surface.blit(nest_tex, (tx, ty))

        # Ember glow in tinder
        if self.ember_ready:
            glow_r = int(18 + 24 * self.blown_ratio)
            s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 80, 10, 180), (glow_r, glow_r), glow_r)
            pygame.draw.circle(s, (255, 220, 80, 230), (glow_r, glow_r), glow_r // 2)
            surface.blit(s, (tx + tw // 2 - glow_r, ty + th // 2 - glow_r))

        draw_text(surface, "Гнездо растопки (Трут)", tx + tw // 2, ty - 18,
                  size=FONT_SIZE_SMALL, color=(255, 220, 150), anchor="midtop", shadow=True)

        # 2. Flint stone with authentic texture
        flint_tex = TextureManager.get('flint', (105, 80))
        if flint_tex:
            surface.blit(flint_tex, (400 - 52, 310 - 40))

        # 3. Animated spark burst if struck
        if self.spark_burst_anim > 0:
            frame = min(3, int((0.35 - self.spark_burst_anim) / 0.35 * 4))
            sp_tex = TextureManager.get(f'flint_sparks_{frame + 1}', (90, 60))
            if sp_tex:
                surface.blit(sp_tex, (400 - 45, 300 - 30))

        # 4. Steel striker in hand
        sx, sy = self.striker_pos
        pygame.draw.rect(surface, (160, 165, 175), (sx - 32, sy - 12, 64, 24), border_radius=6)
        pygame.draw.rect(surface, (230, 235, 245), (sx - 32, sy - 12, 64, 24), width=2, border_radius=6)
        draw_text(surface, "КРЕСАЛО", sx, sy - 1, size=FONT_SIZE_TINY,
                  color=(20, 25, 35), anchor="center")

        # 5. Sparks
        for s in self.sparks:
            pygame.draw.circle(surface, (255, 230, 90), (int(s[0]), int(s[1])), 2)

        # 6. Smoke
        for m in self.smoke_particles:
            sz = int(12 * (1.0 - m[4] / 0.8)) + 4
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (180, 180, 180, 90), (sz, sz), sz)
            surface.blit(s, (int(m[0]) - sz, int(m[1]) - sz))

        # 7. Heat progress bar
        if not self.ember_ready:
            bw = 180
            pygame.draw.rect(surface, (30, 25, 20), (310, 480, bw, 8), border_radius=3)
            pygame.draw.rect(surface, (255, 160, 30), (310, 480, int(bw * self.ember_heat), 8), border_radius=3)

        draw_text(surface, self.hint, 400, 565, size=FONT_SIZE_SMALL,
                  color=self.hint_color, anchor="center", shadow=True)
