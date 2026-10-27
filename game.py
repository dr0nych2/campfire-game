"""
game.py — Core game loop with full mouse drag-and-drop campfire interaction,
marshmallow roasting, interactive poker, swaying forest, fireflies, and night eyes.
"""
import pygame
import random
import math

from fire import FireSystem
from events import WeatherSystem
from sound_synth import sounds
from ignition import MatchIgnition, LighterIgnition, FlintIgnition
from ui import (
    Button, Card, Bar, Panel, draw_text, draw_notification,
    COLOR_PANEL, COLOR_PANEL_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_DIM, COLOR_TEXT_HIGHLIGHT,
    COLOR_WIN, COLOR_FAIL, COLOR_BAR_BREATH,
    FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_TINY
)

SCREEN_W = 800
SCREEN_H = 600
FPS      = 60

FIRE_CX  = SCREEN_W // 2
FIRE_CY  = 400
LOG_W    = 130
LOG_H    = 22

TEMP_DECAY_BASE          = 0.070
TEMP_BLOW_BOOST          = 0.52
BREATH_MAX               = 1.0
BREATH_DEPLETE_RATE      = 0.015
BREATH_REFILL_RATE       = 0.025
BREATH_EMPTY_PENALTY     = 0.14

BURN_GOAL_SECONDS = 60.0

STATE_START    = "start"
STATE_PREP     = "prep"
STATE_IGNITION = "ignition"
STATE_BURNING  = "burning"
STATE_WIN      = "win"
STATE_FAIL     = "fail"

MATERIALS = {
    "newspaper": {
        "name":     "Газета",
        "subtitle": "Быстрая растопка",
        "desc":     "Вспыхивает от малейшей искры, но быстро прогорает. Даёт мало углей.",
        "decay_mul": 1.30,
        "heat_mul":  0.80,
    },
    "pine": {
        "name":     "Хвоя",
        "subtitle": "Смолистая",
        "desc":     "Ароматная, потрескивает смолой. Хороший баланс жара и углей.",
        "decay_mul": 1.00,
        "heat_mul":  1.00,
    },
    "birch": {
        "name":     "Берёза",
        "subtitle": "Долгое горение",
        "desc":     "Тяжело заняться, но даёт мощный жар и плотную подушку углей.",
        "decay_mul": 0.72,
        "heat_mul":  1.35,
    },
}

TOOLS = {
    "match": {
        "name":     "Спички",
        "subtitle": "Тактильный коробок",
        "desc":     "Проведи спичкой по черкашу с нужной резкостью. При сильном ветре прикрывай пламя ладонью (ПКМ)!",
        "uses":     3,
    },
    "lighter": {
        "name":     "Зажигалка",
        "subtitle": "Колёсико + газ",
        "desc":     "Крутни колёсико мыши (высечь искру) + зажми ЛКМ (подать газ). Не боится ветра.",
        "uses":     5,
    },
    "flint": {
        "name":     "Кремень и сталь",
        "subtitle": "Огниво выживальщика",
        "desc":     "Резкими взмахами мыши высеки искру в трут, а затем аккуратно раздуй тлеющий уголёк (ПРОБЕЛ)!",
        "uses":     8,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  Forest Scenery with Wind Sway, Fireflies & Night Predator Eyes
# ─────────────────────────────────────────────────────────────────────────────
class ForestScenery:
    def __init__(self):
        self.stars = []
        for _ in range(65):
            x = random.randint(0, SCREEN_W)
            y = random.randint(0, int(SCREEN_H * 0.55))
            brightness = random.randint(120, 255)
            twinkle_speed = random.uniform(1.2, 3.5)
            size = 1 if random.random() < 0.8 else 2
            self.stars.append([x, y, brightness, twinkle_speed, size])

        # Светлячки
        self.fireflies = []
        for _ in range(12):
            self.fireflies.append([
                random.uniform(40, SCREEN_W - 40),
                random.uniform(220, 480),
                random.uniform(0, math.pi * 2),
                random.uniform(0.4, 1.1)
            ])

        # Точки в лесу, где могут загораться глаза хищников, когда костёр гаснет
        self.eye_spots = [
            (110, 325), (185, 315), (250, 330),
            (555, 328), (630, 318), (705, 332)
        ]

    def draw(self, surface, time_sec, wind_strength=0.0, fire_temp=50.0):
        # 1. Night sky gradient
        for y in range(0, FIRE_CY + 15):
            ratio = y / (FIRE_CY + 15)
            r = int(6 + 14 * ratio)
            g = int(10 + 16 * ratio)
            b = int(22 + 18 * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

        # 2. Moon crescent
        pygame.draw.circle(surface, (230, 235, 210), (680, 85), 24)
        pygame.draw.circle(surface, (8, 12, 25), (670, 80), 22)

        # 3. Twinkling stars
        for s in self.stars:
            alpha = int(s[2] * (0.65 + 0.35 * math.sin(time_sec * s[3])))
            col = (alpha, alpha, min(255, int(alpha * 1.1)))
            pygame.draw.circle(surface, col, (s[0], s[1]), s[4])

        # 4. Swaying distant pines
        sway = math.sin(time_sec * 2.2) * (2.0 + abs(wind_strength) * 0.22) + (wind_strength * 0.15)
        self._draw_pines(surface, y_base=345, height=110, count=16, color=(12, 18, 22), sway=sway)

        # 5. Closer side trees
        self._draw_side_trees(surface, sway * 1.3)

        # 6. Ground
        for y in range(FIRE_CY, SCREEN_H):
            ratio = (y - FIRE_CY) / (SCREEN_H - FIRE_CY)
            r = max(5, int(28 - 16 * ratio))
            g = max(4, int(22 - 12 * ratio))
            b = max(3, int(15 - 9 * ratio))
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

        # 7. Glowing Eyes in the dark when fire is weak (< 45 temp)
        if fire_temp < 45.0:
            danger = (45.0 - fire_temp) / 45.0  # 0..1
            num_eyes = int(danger * len(self.eye_spots)) + 1
            for idx in range(min(num_eyes, len(self.eye_spots))):
                ex, ey = self.eye_spots[idx]
                # Blinking
                blink = math.sin(time_sec * 1.7 + idx * 2.1)
                if blink > -0.7:
                    eye_col = (255, int(180 - 120 * danger), 40)
                    pygame.draw.circle(surface, eye_col, (ex - 4, ey), 2)
                    pygame.draw.circle(surface, eye_col, (ex + 4, ey), 2)

        # 8. Fireflies
        for ff in self.fireflies:
            ff[0] += math.cos(time_sec * ff[3] + ff[2]) * 0.35 + wind_strength * 0.01
            ff[1] += math.sin(time_sec * 1.3 + ff[2]) * 0.25
            if ff[0] < 20: ff[0] = SCREEN_W - 20
            if ff[0] > SCREEN_W - 20: ff[0] = 20
            glow = 0.5 + 0.5 * math.sin(time_sec * 3.5 + ff[2])
            if glow > 0.3:
                c = int(220 * glow)
                pygame.draw.circle(surface, (c, c, int(80 * glow)), (int(ff[0]), int(ff[1])), 2)

    def _draw_pines(self, surface, y_base, height, count, color, sway):
        step = SCREEN_W // count
        for i in range(count + 1):
            x = i * step + ((i * 37) % 23)
            h = height + ((i * 47) % 35)
            w = int(h * 0.42)
            tip_x = int(x + sway * (0.7 + (i % 3) * 0.2))
            pts = [(tip_x, y_base - h), (x - w // 2, y_base), (x + w // 2, y_base)]
            pygame.draw.polygon(surface, color, pts)

    def _draw_side_trees(self, surface, sway):
        for (x, w, h) in [(-30, 90, 320), (30, 80, 290), (740, 85, 300), (810, 95, 330)]:
            pygame.draw.rect(surface, (16, 13, 10), (x + w // 2 - 12, 350, 24, 250))
            for tier in range(4):
                tw = int(w * (0.45 + tier * 0.18))
                th = int(h * 0.32)
                ty = 130 + tier * 55
                tier_sway = int(sway * (1.2 - tier * 0.25))
                pts = [(x + w // 2 + tier_sway, ty),
                       (x + w // 2 - tw // 2, ty + th),
                       (x + w // 2 + tw // 2, ty + th)]
                pygame.draw.polygon(surface, (14, 19, 16), pts)


def draw_stones_and_base_logs(surface, material_key):
    cx, cy = FIRE_CX, FIRE_CY + 12
    stone_positions = [
        (-58, 4), (-42, 16), (-20, 22), (0, 24), (20, 22), (42, 16), (58, 4),
        (-64, -4), (64, -4), (-50, -10), (50, -10)
    ]
    for (ox, oy) in stone_positions:
        sx, sy = cx + ox, cy + oy
        pygame.draw.ellipse(surface, (55, 50, 44), (sx - 12, sy - 7, 24, 14))
        pygame.draw.ellipse(surface, (78, 70, 60), (sx - 11, sy - 6, 22, 12))
        pygame.draw.ellipse(surface, (40, 35, 30), (sx - 12, sy - 7, 24, 14), 1)

    colors = {
        "newspaper": (135, 105, 75),
        "pine":      (95, 70, 45),
        "birch":     (175, 170, 160),
    }
    log_col = colors.get(material_key, (100, 75, 50))
    for angle in (-24, 24):
        rad = math.radians(angle)
        hw = LOG_W // 2
        x1 = int(cx - hw * math.cos(rad))
        y1 = int(cy + hw * math.sin(rad) - 4)
        x2 = int(cx + hw * math.cos(rad))
        y2 = int(cy - hw * math.sin(rad) - 4)
        pygame.draw.line(surface, log_col, (x1, y1), (x2, y2), LOG_H)
        pygame.draw.line(surface, tuple(min(255, c + 25) for c in log_col), (x1, y1 - 2), (x2, y2 - 2), 3)
        pygame.draw.circle(surface, log_col, (x1, y1), LOG_H // 2)
        pygame.draw.circle(surface, log_col, (x2, y2), LOG_H // 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Main Game Class
# ─────────────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen   = screen
        self.clock    = pygame.time.Clock()
        self.running  = True
        self.time_sec = 0.0

        self.fire     = FireSystem(FIRE_CX, FIRE_CY)
        self.weather  = WeatherSystem(SCREEN_W, SCREEN_H)
        self.scenery  = ForestScenery()

        self._reset()

    def _reset(self):
        self.state         = STATE_START
        self.temperature   = 0.0
        self.breath        = BREATH_MAX
        self.blowing       = False
        self.rmb_blowing   = False
        self.selected_mat  = "pine"
        self.selected_tool = "match"
        self.burn_timer    = 0.0

        # Запасы топлива на поляне
        self.inv_tinder   = 4
        self.inv_kindling = 6
        self.inv_logs     = 5
        self.poker_cooldown = 0.0

        # Интерактивное перетаскивание мышью (Drag & Drop)
        # 'tinder', 'kindling', 'log', 'poker', 'marshmallow', None
        self.drag_item = None
        self.mouse_pos = [400, 300]
        self.prev_mouse_pos = [400, 300]
        self.poke_accum = 0.0

        # Состояние зефирки (0.0 = сырая белая, 0.5..0.85 = золотистая, >1.0 = сгорела)
        self.marsh_roast = 0.0
        self.marsh_eaten_count = 0

        # Хитбоксы предметов внизу экрана на поляне
        self.rect_tinder   = pygame.Rect(45,  485, 115, 75)
        self.rect_kindling = pygame.Rect(180, 485, 125, 75)
        self.rect_logs     = pygame.Rect(325, 485, 135, 75)
        self.rect_poker    = pygame.Rect(485, 485, 120, 75)
        self.rect_marsh    = pygame.Rect(625, 485, 130, 75)
        self.fire_drop_zone = pygame.Rect(FIRE_CX - 95, FIRE_CY - 70, 190, 125)

        self.ignition_game = None

        self.notif       = ""
        self.notif_t     = 0.0
        self.notif_color = COLOR_TEXT_HIGHLIGHT

        self.fire.set_temperature(0)
        self.fire.clear_fuel()
        self.weather.force_calm()

        self._build_ui()

    def _build_ui(self):
        self.btn_start = Button((SCREEN_W // 2 - 110, 420, 220, 48),
                                "Начать симуляцию", size=FONT_SIZE_MEDIUM)

        # Кнопка включения/выключения звука в правом верхнем углу
        self.btn_mute = Button((SCREEN_W - 135, 12, 120, 28),
                               "Звук: ВКЛ (M)", size=FONT_SIZE_TINY)

        card_w, card_h = 220, 165
        gap = 18
        start_x = (SCREEN_W - (3 * card_w + 2 * gap)) // 2
        self.mat_cards = []
        for i, (k, mat) in enumerate(MATERIALS.items()):
            c = Card((start_x + i * (card_w + gap), 170, card_w, card_h),
                     mat["name"], mat["subtitle"], mat["desc"], tag=k)
            self.mat_cards.append(c)

        tw = 190
        start_tx = (SCREEN_W - (3 * tw + 2 * gap)) // 2
        self.tool_btns = []
        for i, (k, tool) in enumerate(TOOLS.items()):
            b = Button((start_tx + i * (tw + gap), 370, tw, 46), tool["name"])
            b.tag = k
            self.tool_btns.append(b)

        self.btn_prep_confirm = Button((SCREEN_W // 2 - 110, 490, 220, 46),
                                      "К розжигу!", size=FONT_SIZE_MEDIUM)

        # Компактный HUD сверху слева
        self.bar_temp   = Bar((20, 18, 200, 20), "Жар костра")
        self.bar_breath = Bar((20, 44, 200, 20), "Дыхание",
                              lo_color=COLOR_BAR_BREATH,
                              mid_color=COLOR_BAR_BREATH,
                              hi_color=COLOR_BAR_BREATH)

        self.btn_play_again   = Button((SCREEN_W // 2 - 110, 430, 220, 48),
                                       "Играть снова", size=FONT_SIZE_MEDIUM)
        self.btn_back_to_prep = Button((SCREEN_W // 2 - 110, 490, 220, 42),
                                       "Выбрать другое снаряжение", size=FONT_SIZE_SMALL)

    def _toggle_mute(self):
        sounds.enabled = not sounds.enabled
        self.btn_mute.label = "Звук: ВКЛ (M)" if sounds.enabled else "Звук: ВЫКЛ (M)"

    def _notify(self, text, duration=2.6, color=COLOR_TEXT_HIGHLIGHT):
        self.notif       = text
        self.notif_t     = duration * FPS
        self.notif_color = color

    # ── State transitions ─────────────────────────────────────────────────────
    def _go_prep(self):
        self.state = STATE_PREP
        for c in self.mat_cards:
            c.selected = (c.tag == self.selected_mat)
        for b in self.tool_btns:
            b.active = (b.tag == self.selected_tool)

    def _go_ignition(self):
        self.state = STATE_IGNITION
        self.temperature = 0.0
        self.fire.set_temperature(0)
        self.fire.clear_fuel()

        if self.selected_tool == "match":
            self.ignition_game = MatchIgnition(self.selected_mat, self.weather)
        elif self.selected_tool == "lighter":
            self.ignition_game = LighterIgnition(self.selected_mat, self.weather)
        else:
            self.ignition_game = FlintIgnition(self.selected_mat, self.weather)

    def _go_burning(self):
        self.state       = STATE_BURNING
        self.temperature = 18.0
        self.burn_timer  = 0.0
        self.fire.set_temperature(self.temperature)
        self.fire.add_fuel_visual('tinder')
        self.fire.add_fuel_visual('kindling')
        self.fire.burst_embers(25)
        sounds.play('match_light')
        self._notify("Перетаскивай дрова мышкой прямо в костёр! Води кочергой по углям!", 4.0)

    # ── Fuel & Item actions ───────────────────────────────────────────────────
    def _add_tinder(self):
        if self.inv_tinder <= 0:
            self._notify("Береста закончилась!", color=COLOR_FAIL)
            return
        self.inv_tinder -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('tinder')
        self.temperature = min(100.0, self.temperature + 16.0)
        self.fire.burst_embers(12)
        self._notify(f"Береста вспыхнула в огне! (+16° жара)")

    def _add_kindling(self):
        if self.inv_kindling <= 0:
            self._notify("Хворост закончился!", color=COLOR_FAIL)
            return
        self.inv_kindling -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('kindling')
        self.temperature = min(100.0, self.temperature + 18.0)
        self.fire.burst_embers(16)
        self._notify(f"Сухие ветки весело затрещали! (+18° жара)")

    def _add_log(self):
        if self.inv_logs <= 0:
            self._notify("Поленья закончились!", color=COLOR_FAIL)
            return

        sounds.play('wood_drop')
        self.fire.add_fuel_visual('log')
        if self.temperature < 25.0:
            self.inv_logs -= 1
            self.temperature = max(2.0, self.temperature - 9.0)
            self._notify("Тяжёлое полено придавило слабый огонёк! Нужно больше жара (>25°)!", color=COLOR_FAIL)
        else:
            self.inv_logs -= 1
            mat_mult = MATERIALS[self.selected_mat]["heat_mul"]
            gain = int(26.0 * mat_mult)
            self.temperature = min(100.0, self.temperature + gain)
            self.fire.burst_embers(22)
            self._notify(f"Бревно занялось мощным жаром! (+{gain}°)")

    def _use_poker(self):
        if self.poker_cooldown > 0:
            return
        self.poker_cooldown = 2.2
        sounds.play('poker_poke')
        self.fire.burst_embers(25)
        self.temperature = min(100.0, self.temperature + 6.5)
        self._notify("Угли разворошены кочергой! (+6.5° жара)")

    # ── Event handling ────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.MOUSEMOTION:
                self.prev_mouse_pos = list(self.mouse_pos)
                self.mouse_pos = list(event.pos)

            # Mute button works everywhere
            if self.btn_mute.handle_event(event):
                self._toggle_mute()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                if event.key == pygame.K_m:
                    self._toggle_mute()

                if self.state == STATE_BURNING:
                    if event.key == pygame.K_SPACE:
                        self.blowing = True
                    elif event.key == pygame.K_1:
                        self._add_tinder()
                    elif event.key == pygame.K_2:
                        self._add_kindling()
                    elif event.key == pygame.K_3:
                        self._add_log()
                    elif event.key == pygame.K_4 or event.key == pygame.K_f:
                        self._use_poker()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.blowing = False

            if self.state == STATE_IGNITION and self.ignition_game:
                self.ignition_game.handle_event(event)

            if self.state == STATE_START:
                if self.btn_start.handle_event(event):
                    self._go_prep()

            elif self.state == STATE_PREP:
                for c in self.mat_cards:
                    if c.handle_event(event):
                        for cc in self.mat_cards:
                            cc.selected = False
                        c.selected = True
                        self.selected_mat = c.tag
                for b in self.tool_btns:
                    if b.handle_event(event):
                        for bb in self.tool_btns:
                            bb.active = False
                        b.active = True
                        self.selected_tool = b.tag
                if self.btn_prep_confirm.handle_event(event):
                    self._go_ignition()

            elif self.state in (STATE_WIN, STATE_FAIL):
                if self.btn_play_again.handle_event(event):
                    self._reset()
                    self._go_ignition()
                elif self.btn_back_to_prep.handle_event(event):
                    self._reset()
                    self._go_prep()

            elif self.state == STATE_BURNING:
                self._handle_burning_mouse(event)

    def _handle_burning_mouse(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            if event.button == 1:  # ЛКМ — берём предмет в руку
                if self.rect_tinder.collidepoint(pos) and self.inv_tinder > 0:
                    self.drag_item = 'tinder'
                elif self.rect_kindling.collidepoint(pos) and self.inv_kindling > 0:
                    self.drag_item = 'kindling'
                elif self.rect_logs.collidepoint(pos) and self.inv_logs > 0:
                    self.drag_item = 'log'
                elif self.rect_poker.collidepoint(pos):
                    self.drag_item = 'poker'
                    self.poke_accum = 0.0
                elif self.rect_marsh.collidepoint(pos):
                    self.drag_item = 'marshmallow'

            elif event.button == 3:  # ПКМ — съесть поджаренную зефирку ИЛИ дуть на костёр
                if self.drag_item == 'marshmallow':
                    if 0.45 <= self.marsh_roast <= 0.95:
                        self.marsh_roast = 0.0
                        self.marsh_eaten_count += 1
                        self.breath = BREATH_MAX
                        self.temperature = min(100.0, self.temperature + 5.0)
                        sounds.play('match_light')
                        self._notify("Идеальная золотистая зефирка съедена! Дыхание 100%!", color=COLOR_WIN)
                    elif self.marsh_roast > 0.95:
                        self.marsh_roast = 0.0
                        self._notify("Фу, сгоревший уголёк... Насадил новую зефирку.", color=COLOR_FAIL)
                    else:
                        self._notify("Она ещё сырая! Подержи её над макушкой огня.", color=COLOR_TEXT_DIM)
                else:
                    # Зажатие ПКМ дует на угли (альтернатива Пробелу)
                    self.rmb_blowing = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.drag_item:
                # Если бросили топливо в зону костра
                if self.fire_drop_zone.collidepoint(event.pos):
                    if self.drag_item == 'tinder':
                        self._add_tinder()
                    elif self.drag_item == 'kindling':
                        self._add_kindling()
                    elif self.drag_item == 'log':
                        self._add_log()
                self.drag_item = None

            elif event.button == 3:
                self.rmb_blowing = False

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        self.time_sec += dt
        self.weather.update(dt)
        self.fire.set_wind(self.weather.wind_strength)

        if self.poker_cooldown > 0:
            self.poker_cooldown -= dt

        if self.notif_t > 0:
            self.notif_t -= 1

        if self.state == STATE_IGNITION and self.ignition_game:
            self.ignition_game.update(dt)
            if self.ignition_game.success:
                self._go_burning()
            elif self.ignition_game.failed:
                self.state = STATE_FAIL

        elif self.state == STATE_BURNING:
            self._update_burning(dt)

        self.fire.update(dt)
        sounds.update_fire_audio(self.temperature, dt)

    def _update_burning(self, dt):
        mat = MATERIALS[self.selected_mat]
        decay = TEMP_DECAY_BASE * mat["decay_mul"]
        decay -= self.weather.temp_modifier
        self.temperature -= decay

        # Интерактив кочергой: если водим кочергой по зоне костра
        mx, my = self.mouse_pos
        if self.drag_item == 'poker' and self.fire_drop_zone.collidepoint((mx, my)):
            dist = math.hypot(mx - self.prev_mouse_pos[0], my - self.prev_mouse_pos[1])
            self.poke_accum += dist
            if dist > 4 and random.random() < 0.35:
                self.fire.burst_embers(2)
            if self.poke_accum > 95:
                self.poke_accum = 0.0
                self._use_poker()

        # Интерактив жарки зефирки над огнём
        if self.drag_item == 'marshmallow':
            # Зона над огнём
            dist_x = abs(mx - FIRE_CX)
            if dist_x < 75 and (FIRE_CY - 140 < my < FIRE_CY + 10) and self.temperature > 10:
                if my > FIRE_CY - 35:
                    # Слишком низко в самом пекле — быстро сгорает!
                    self.marsh_roast += dt * 0.45
                else:
                    # Над огнём — плавно подрумянивается
                    self.marsh_roast += dt * 0.18 * (self.temperature / 50.0)

        # Раздувание (Пробел ИЛИ ПКМ)
        is_blowing = self.blowing or self.rmb_blowing
        if is_blowing and self.breath > 0:
            self.breath = max(0.0, self.breath - BREATH_DEPLETE_RATE)
            if random.random() < 0.12:
                sounds.play('blow')
            if self.breath <= 0:
                self.temperature -= BREATH_EMPTY_PENALTY
            else:
                self.temperature += TEMP_BLOW_BOOST * mat["heat_mul"]
                if random.random() < 0.22:
                    self.fire.burst_embers(2)
        else:
            self.breath = min(BREATH_MAX, self.breath + BREATH_REFILL_RATE)

        self.temperature = max(0.0, min(100.0, self.temperature))
        self.fire.set_temperature(self.temperature)

        if self.temperature > 5.0:
            self.burn_timer += dt

        if self.burn_timer >= BURN_GOAL_SECONDS:
            self.state = STATE_WIN
            sounds.play('match_light')
        elif self.temperature <= 0.0:
            self.state = STATE_FAIL
            sounds.play('blow')

        self.bar_temp.set_value(self.temperature / 100.0)
        self.bar_breath.set_value(self.breath)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        fire_vis_temp = self.temperature if self.state == STATE_BURNING else 45.0
        self.scenery.draw(self.screen, self.time_sec, self.weather.wind_strength, fire_vis_temp)
        draw_stones_and_base_logs(self.screen, self.selected_mat)
        self.weather.draw(self.screen)
        self.fire.draw(self.screen)
        self.fire.draw_ambient_light(self.screen)

        if self.state == STATE_START:
            self._draw_start()
        elif self.state == STATE_PREP:
            self._draw_prep()
        elif self.state == STATE_IGNITION:
            self._draw_ignition()
        elif self.state == STATE_BURNING:
            self._draw_burning()
        elif self.state == STATE_WIN:
            self._draw_end(win=True)
        elif self.state == STATE_FAIL:
            self._draw_end(win=False)

        self.btn_mute.draw(self.screen)

        if self.notif_t > 0:
            alpha = min(255, int(self.notif_t * 6))
            draw_notification(self.screen, self.notif, 115, color=self.notif_color, alpha=alpha)

        pygame.display.flip()

    def _draw_start(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "КОСТЁР", SCREEN_W // 2, 110,
                  size=FONT_SIZE_LARGE + 18, color=COLOR_TEXT_HIGHLIGHT,
                  anchor="center", shadow=True)
        draw_text(self.screen, "Тактильный симулятор выживания в ночном лесу",
                  SCREEN_W // 2, 175, size=FONT_SIZE_MEDIUM,
                  color=COLOR_TEXT_DIM, anchor="center")

        instructions = [
            "Розжиг: чиркай спичкой, крути колёсико зажигалки или высекай искры огнивом.",
            "Интерактив мышью: перетаскивай бересту, ветки и брёвна прямо в костёр!",
            "Води палкой-кочергой по углям и жарь зефирку над пламенем.",
            "Поддерживай яркий огонь 60 секунд, чтобы хищники из темноты не подошли близко.",
        ]
        y = 235
        for line in instructions:
            draw_text(self.screen, line, SCREEN_W // 2, y,
                      size=FONT_SIZE_SMALL, color=COLOR_TEXT_MAIN, anchor="center")
            y += 28

        self.btn_start.draw(self.screen)

    def _draw_prep(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "Подготовка снаряжения", SCREEN_W // 2, 28,
                  size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        draw_text(self.screen, "Выбери древесину:", SCREEN_W // 2, 142,
                  size=FONT_SIZE_SMALL, color=COLOR_TEXT_DIM, anchor="center")
        for c in self.mat_cards:
            c.draw(self.screen)

        draw_text(self.screen, "Выбери средство розжига:", SCREEN_W // 2, 345,
                  size=FONT_SIZE_SMALL, color=COLOR_TEXT_DIM, anchor="center")
        for b in self.tool_btns:
            b.draw(self.screen)

        if self.selected_tool:
            tool = TOOLS[self.selected_tool]
            draw_text(self.screen, tool["desc"], SCREEN_W // 2, 435,
                      size=FONT_SIZE_TINY, color=(220, 200, 160), anchor="center")

        self.btn_prep_confirm.draw(self.screen)

    def _draw_ignition(self):
        if self.ignition_game:
            self.ignition_game.draw(self.screen)

        if self.weather.label and self.weather.label != "Тихо":
            wc = COLOR_FAIL if (self.weather.is_raining or self.weather.is_strong_wind) else COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, f"Погода: {self.weather.label}", SCREEN_W // 2, 25,
                      size=FONT_SIZE_SMALL, color=wc, anchor="midtop")

    def _draw_burning(self):
        # 1. Компактная панель показателей сверху слева
        panel = Panel((10, 10, 220, 64), "")
        panel.draw(self.screen)
        self.bar_temp.draw(self.screen)
        self.bar_breath.draw(self.screen)

        # 2. Таймер и погода
        rem = max(0.0, BURN_GOAL_SECONDS - self.burn_timer)
        draw_text(self.screen, f"До рассвета: {int(rem)}с", SCREEN_W - 25, 48,
                  size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_HIGHLIGHT, anchor="topright", shadow=True)

        if self.weather.label and self.weather.label != "Тихо":
            wc = COLOR_FAIL if (self.weather.is_raining or self.weather.is_strong_wind) else COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, self.weather.label, SCREEN_W // 2, 18,
                      size=FONT_SIZE_SMALL, color=wc, anchor="midtop")

        # Предупреждение о глазах в темноте
        if self.temperature < 40.0:
            draw_text(self.screen, "Костёр гаснет... В темноте леса зажглись чьи-то глаза!",
                      SCREEN_W // 2, 45, size=FONT_SIZE_TINY, color=(255, 110, 80), anchor="midtop")

        # 3. Подсветка зоны костра при перетаскивании топлива
        if self.drag_item in ('tinder', 'kindling', 'log'):
            hl = pygame.Surface((self.fire_drop_zone.width, self.fire_drop_zone.height), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 200, 80, 45), (0, 0, self.fire_drop_zone.width, self.fire_drop_zone.height), 2)
            self.screen.blit(hl, self.fire_drop_zone.topleft)

        # 4. Визуальные стопки предметов на земле внизу экрана
        self._draw_ground_items()

        # 5. Отрисовка предмета, который сейчас в руке (на курсоре мыши)
        self._draw_dragged_item()

        hint = "ЛКМ: тащи дрова в огонь / води кочергой / жарь зефир  |  ПКМ или ПРОБЕЛ: дуть на угли"
        draw_text(self.screen, hint, SCREEN_W // 2, SCREEN_H - 14,
                  size=FONT_SIZE_TINY, color=(210, 190, 145), anchor="center")

    def _draw_ground_items(self):
        mx, my = self.mouse_pos

        # Хелпер для рамок слотов на земле
        def draw_slot(rect, title, subtitle, active=True):
            hovered = rect.collidepoint((mx, my)) and active
            bg = (52, 38, 24, 210) if hovered else (32, 24, 16, 185)
            border = COLOR_TEXT_HIGHLIGHT if hovered else (95, 70, 42)
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s, bg, (0, 0, rect.width, rect.height), border_radius=8)
            pygame.draw.rect(s, border, (0, 0, rect.width, rect.height), width=2, border_radius=8)
            self.screen.blit(s, rect.topleft)
            draw_text(self.screen, title, rect.centerx, rect.bottom - 24,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_MAIN if active else COLOR_TEXT_DIM, anchor="center")
            draw_text(self.screen, subtitle, rect.centerx, rect.bottom - 10,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT if active else COLOR_TEXT_DIM, anchor="center")

        # 1. Береста (Tinder)
        draw_slot(self.rect_tinder, f"Береста ({self.inv_tinder})", "+16° быстро", self.inv_tinder > 0)
        for i in range(min(self.inv_tinder, 3)):
            pygame.draw.ellipse(self.screen, (220, 200, 165), (self.rect_tinder.x + 28 + i * 16, self.rect_tinder.y + 14, 28, 16))
            pygame.draw.line(self.screen, (80, 70, 60), (self.rect_tinder.x + 34 + i * 16, self.rect_tinder.y + 20), (self.rect_tinder.x + 48 + i * 16, self.rect_tinder.y + 22), 2)

        # 2. Хворост (Kindling)
        draw_slot(self.rect_kindling, f"Хворост ({self.inv_kindling})", "+18° ветки", self.inv_kindling > 0)
        for i in range(min(self.inv_kindling, 4)):
            pygame.draw.line(self.screen, (140, 100, 55),
                             (self.rect_kindling.x + 25, self.rect_kindling.y + 15 + i * 6),
                             (self.rect_kindling.x + 95, self.rect_kindling.y + 22 - i * 4), 4)

        # 3. Поленья (Logs)
        draw_slot(self.rect_logs, f"Поленья ({self.inv_logs})", "Жар (нужно >25°)", self.inv_logs > 0)
        for i in range(min(self.inv_logs, 3)):
            lx = self.rect_logs.x + 28 + i * 12
            ly = self.rect_logs.y + 14 + (i % 2) * 8
            pygame.draw.rect(self.screen, (145, 110, 70), (lx, ly, 58, 16), border_radius=4)
            pygame.draw.circle(self.screen, (190, 165, 120), (lx + 58, ly + 8), 7)

        # 4. Кочерга (Poker)
        draw_slot(self.rect_poker, "Кочерга", "Водить по углям", True)
        pygame.draw.line(self.screen, (130, 135, 145),
                         (self.rect_poker.x + 25, self.rect_poker.y + 34),
                         (self.rect_poker.x + 90, self.rect_poker.y + 14), 4)
        pygame.draw.line(self.screen, (130, 135, 145),
                         (self.rect_poker.x + 90, self.rect_poker.y + 14),
                         (self.rect_poker.x + 96, self.rect_poker.y + 24), 4)

        # 5. Зефирка на палочке (Marshmallow)
        roast_txt = "ПКМ: съесть!" if 0.45 <= self.marsh_roast <= 0.95 else "Держать над огнём"
        draw_slot(self.rect_marsh, "Зефирка", roast_txt, True)
        pygame.draw.line(self.screen, (160, 125, 80),
                         (self.rect_marsh.x + 30, self.rect_marsh.y + 35),
                         (self.rect_marsh.x + 85, self.rect_marsh.y + 16), 3)
        m_col = self._get_marsh_color()
        pygame.draw.rect(self.screen, m_col, (self.rect_marsh.x + 80, self.rect_marsh.y + 10, 18, 14), border_radius=4)

    def _get_marsh_color(self):
        r = self.marsh_roast
        if r < 0.45:
            # От белого к нежно-кремовому
            t = r / 0.45
            return (250, int(248 - 30 * t), int(245 - 80 * t))
        elif r <= 0.95:
            # Золотисто-карамельная корочка
            t = (r - 0.45) / 0.50
            return (int(245 - 45 * t), int(218 - 85 * t), int(165 - 115 * t))
        else:
            # Сгорела в уголь
            return (35, 30, 28)

    def _draw_dragged_item(self):
        if not self.drag_item:
            return
        mx, my = self.mouse_pos

        if self.drag_item == 'tinder':
            pygame.draw.ellipse(self.screen, (230, 210, 175), (mx - 22, my - 12, 44, 24))
            draw_text(self.screen, "Брось в костёр", mx, my - 22, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'kindling':
            pygame.draw.line(self.screen, (150, 105, 60), (mx - 35, my - 8), (mx + 35, my + 8), 5)
            pygame.draw.line(self.screen, (135, 95, 50), (mx - 30, my + 10), (mx + 32, my - 10), 4)
            draw_text(self.screen, "Брось в костёр", mx, my - 24, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'log':
            pygame.draw.rect(self.screen, (150, 115, 75), (mx - 40, my - 12, 80, 24), border_radius=5)
            pygame.draw.circle(self.screen, (200, 175, 130), (mx + 40, my), 11)
            draw_text(self.screen, "Брось в костёр", mx, my - 26, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'poker':
            # Кочерга тянется от правой руки к курсору
            pygame.draw.line(self.screen, (150, 155, 165), (mx + 95, my + 75), (mx, my), 5)
            pygame.draw.line(self.screen, (200, 120, 60), (mx, my), (mx - 12, my + 10), 5)
            draw_text(self.screen, "Води по углям туда-сюда!", mx, my - 22, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'marshmallow':
            pygame.draw.line(self.screen, (170, 135, 85), (mx + 90, my + 70), (mx, my), 3)
            m_col = self._get_marsh_color()
            pygame.draw.rect(self.screen, m_col, (mx - 12, my - 10, 24, 18), border_radius=5)
            pygame.draw.rect(self.screen, (80, 60, 40), (mx - 12, my - 10, 24, 18), width=1, border_radius=5)

            if self.marsh_roast > 0.95:
                status = "СГОРЕЛА! (Нажми ПКМ, чтобы взять новую)"
                sc = COLOR_FAIL
            elif self.marsh_roast >= 0.45:
                status = f"ГОТОВА ({int(self.marsh_roast * 100)}%)! Нажми ПКМ, чтобы съесть!"
                sc = COLOR_WIN
            else:
                status = f"Жарится: {int((self.marsh_roast / 0.45) * 100)}% (держи над пламенем)"
                sc = COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, status, mx, my - 25, size=FONT_SIZE_TINY, color=sc, anchor="center")

    def _draw_end(self, win: bool):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        if win:
            draw_text(self.screen, "Ты пережил ночь у костра!", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 6, color=COLOR_WIN, anchor="center", shadow=True)
            draw_text(self.screen, f"Огонь согревал поляну 60 секунд. Съедено зефирок: {self.marsh_eaten_count}",
                      SCREEN_W // 2, 245, size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_MAIN, anchor="center")
        else:
            draw_text(self.screen, "Огонь угас в темноте...", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 8, color=COLOR_FAIL, anchor="center", shadow=True)
            fail_reason = ""
            if self.ignition_game and self.ignition_game.failed and self.ignition_game.fail_reason:
                fail_reason = self.ignition_game.fail_reason
            elif self.temperature <= 0:
                fail_reason = "Костру не хватило жара, угли остыли и ночной лес сомкнулся."
            draw_text(self.screen, fail_reason, SCREEN_W // 2, 245,
                      size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_MAIN, anchor="center")

        self.btn_play_again.draw(self.screen)
        self.btn_back_to_prep.draw(self.screen)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()