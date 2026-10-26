"""
game.py — Core game loop, tactile ignition, multi-tier campfire survival, and forest scenery.
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
    FontCache,
    COLOR_BG_DARK, COLOR_PANEL, COLOR_PANEL_BORDER,
    COLOR_TEXT_MAIN, COLOR_TEXT_DIM, COLOR_TEXT_HIGHLIGHT,
    COLOR_WIN, COLOR_FAIL, COLOR_BAR_BREATH,
    FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL, FONT_SIZE_TINY
)

SCREEN_W = 800
SCREEN_H = 600
FPS      = 60

FIRE_CX  = SCREEN_W // 2
FIRE_CY  = 410
LOG_W    = 130
LOG_H    = 24

TEMP_DECAY_BASE          = 0.075
TEMP_BLOW_BOOST          = 0.52
BREATH_MAX               = 1.0
BREATH_DEPLETE_RATE      = 0.016
BREATH_REFILL_RATE       = 0.024
BREATH_EMPTY_PENALTY     = 0.16

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
        "decay_mul": 1.35,
        "heat_mul":  0.75,
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
        "decay_mul": 0.70,
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
#  Forest & Scenery Drawing
# ─────────────────────────────────────────────────────────────────────────────
class ForestScenery:
    def __init__(self):
        # Generate persistent stars
        self.stars = []
        for _ in range(65):
            x = random.randint(0, SCREEN_W)
            y = random.randint(0, int(SCREEN_H * 0.55))
            brightness = random.randint(120, 255)
            twinkle_speed = random.uniform(1.2, 3.5)
            size = 1 if random.random() < 0.8 else 2
            self.stars.append([x, y, brightness, twinkle_speed, size])

    def draw(self, surface, time_sec):
        # 1. Dark night gradient
        for y in range(0, FIRE_CY + 15):
            ratio = y / (FIRE_CY + 15)
            r = int(6 + 14 * ratio)
            g = int(10 + 16 * ratio)
            b = int(22 + 18 * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

        # 2. Twinkling stars
        for s in self.stars:
            alpha = int(s[2] * (0.65 + 0.35 * math.sin(time_sec * s[3])))
            col = (alpha, alpha, min(255, int(alpha * 1.1)))
            pygame.draw.circle(surface, col, (s[0], s[1]), s[4])

        # 3. Distant pine silhouettes (Back row)
        self._draw_pines(surface, y_base=340, height=110, count=16, color=(12, 18, 22))

        # 4. Closer pine silhouettes (Left and right framing)
        self._draw_side_trees(surface)

        # 5. Forest ground
        for y in range(FIRE_CY + 10, SCREEN_H):
            ratio = (y - FIRE_CY - 10) / (SCREEN_H - FIRE_CY - 10)
            r = max(5, int(26 - 16 * ratio))
            g = max(4, int(20 - 12 * ratio))
            b = max(3, int(14 - 9 * ratio))
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

    def _draw_pines(self, surface, y_base, height, count, color):
        step = SCREEN_W // count
        for i in range(count + 1):
            x = i * step + ((i * 37) % 23)
            h = height + ((i * 47) % 35)
            w = int(h * 0.42)
            pts = [(x, y_base - h), (x - w // 2, y_base), (x + w // 2, y_base)]
            pygame.draw.polygon(surface, color, pts)

    def _draw_side_trees(self, surface):
        # Big trees on borders to create a cozy forest clearing
        for (x, w, h) in [(-30, 90, 320), (30, 80, 290), (740, 85, 300), (810, 95, 330)]:
            # Trunk
            pygame.draw.rect(surface, (16, 13, 10), (x + w // 2 - 12, 360, 24, 240))
            # Foliage tiers
            for tier in range(4):
                tw = int(w * (0.45 + tier * 0.18))
                th = int(h * 0.32)
                ty = 130 + tier * 55
                pts = [(x + w // 2, ty), (x + w // 2 - tw // 2, ty + th), (x + w // 2 + tw // 2, ty + th)]
                pygame.draw.polygon(surface, (14, 19, 16), pts)


def draw_stones_and_logs(surface, material_key):
    cx, cy = FIRE_CX, FIRE_CY + 12
    # Stone ring around fire
    stone_positions = [
        (-56, 4), (-40, 16), (-20, 22), (0, 24), (20, 22), (40, 16), (56, 4),
        (-62, -4), (62, -4), (-48, -10), (48, -10)
    ]
    for (ox, oy) in stone_positions:
        sx, sy = cx + ox, cy + oy
        pygame.draw.ellipse(surface, (55, 50, 44), (sx - 12, sy - 7, 24, 14))
        pygame.draw.ellipse(surface, (78, 70, 60), (sx - 11, sy - 6, 22, 12))
        pygame.draw.ellipse(surface, (40, 35, 30), (sx - 12, sy - 7, 24, 14), 1)

    # Crossed Logs
    colors = {
        "newspaper": (135, 105, 75),
        "pine":      (95, 70, 45),
        "birch":     (175, 170, 160),
    }
    log_col = colors.get(material_key, (100, 75, 50))
    for angle in (-26, 26):
        rad = math.radians(angle)
        hw = LOG_W // 2
        x1 = int(cx - hw * math.cos(rad))
        y1 = int(cy + hw * math.sin(rad) - 4)
        x2 = int(cx + hw * math.cos(rad))
        y2 = int(cy - hw * math.sin(rad) - 4)
        pygame.draw.line(surface, log_col, (x1, y1), (x2, y2), LOG_H)
        pygame.draw.line(surface, tuple(min(255, c + 25) for c in log_col), (x1, y1 - 2), (x2, y2 - 2), 4)
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
        self.selected_mat  = "pine"
        self.selected_tool = "match"
        self.burn_timer    = 0.0

        # Multi-tiered inventory during burning
        self.inv_tinder   = 3    # Береста / растопка (легкая, быстрый жар)
        self.inv_kindling = 5    # Хворост / ветки (средний жар)
        self.inv_logs     = 4    # Поленья (тяжелые, долго горят, но душат слабый огонь)
        self.poker_cooldown = 0.0

        self.ignition_game = None

        self.notif       = ""
        self.notif_t     = 0.0
        self.notif_color = COLOR_TEXT_HIGHLIGHT

        self.fire.set_temperature(0)
        self.weather.force_calm()

        self._build_ui()

    def _build_ui(self):
        # 1. Start screen
        self.btn_start = Button((SCREEN_W // 2 - 110, 420, 220, 48),
                                "Начать симуляцию", size=FONT_SIZE_MEDIUM)

        # 2. Prep screen — material cards
        card_w, card_h = 220, 165
        gap = 18
        start_x = (SCREEN_W - (3 * card_w + 2 * gap)) // 2
        self.mat_cards = []
        for i, (k, mat) in enumerate(MATERIALS.items()):
            c = Card((start_x + i * (card_w + gap), 170, card_w, card_h),
                     mat["name"], mat["subtitle"], mat["desc"], tag=k)
            self.mat_cards.append(c)

        # Tool buttons
        tw = 190
        start_tx = (SCREEN_W - (3 * tw + 2 * gap)) // 2
        self.tool_btns = []
        for i, (k, tool) in enumerate(TOOLS.items()):
            b = Button((start_tx + i * (tw + gap), 370, tw, 46), tool["name"])
            b.tag = k
            self.tool_btns.append(b)

        self.btn_prep_confirm = Button((SCREEN_W // 2 - 110, 490, 220, 46),
                                      "К розжигу!", size=FONT_SIZE_MEDIUM)

        # 3. Burning HUD
        self.bar_temp   = Bar((20, 20, 210, 22), "Температура")
        self.bar_breath = Bar((20, 50, 210, 22), "Дыхание",
                              lo_color=COLOR_BAR_BREATH,
                              mid_color=COLOR_BAR_BREATH,
                              hi_color=COLOR_BAR_BREATH)

        # Interactive item buttons during burning
        bx = 20
        self.btn_use_tinder   = Button((bx, 80, 210, 32), "1: Растопка (быстро)", size=FONT_SIZE_TINY)
        self.btn_use_kindling = Button((bx, 116, 210, 32), "2: Хворост (пламя)", size=FONT_SIZE_TINY)
        self.btn_use_logs     = Button((bx, 152, 210, 32), "3: Полено (жар)", size=FONT_SIZE_TINY)
        self.btn_use_poker    = Button((bx, 188, 210, 32), "4: Ворошить угли", size=FONT_SIZE_TINY)

        # Retry buttons
        self.btn_play_again   = Button((SCREEN_W // 2 - 110, 430, 220, 48),
                                       "Играть снова", size=FONT_SIZE_MEDIUM)
        self.btn_back_to_prep = Button((SCREEN_W // 2 - 110, 490, 220, 42),
                                       "Выбрать другое снаряжение", size=FONT_SIZE_SMALL)

    def _notify(self, text, duration=2.8, color=COLOR_TEXT_HIGHLIGHT):
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

        # Launch the dedicated tactical mini-game
        if self.selected_tool == "match":
            self.ignition_game = MatchIgnition(self.selected_mat, self.weather)
        elif self.selected_tool == "lighter":
            self.ignition_game = LighterIgnition(self.selected_mat, self.weather)
        else:
            self.ignition_game = FlintIgnition(self.selected_mat, self.weather)

    def _go_burning(self):
        self.state       = STATE_BURNING
        self.temperature = 14.0
        self.burn_timer  = 0.0
        self.fire.set_temperature(self.temperature)
        self.fire.burst_embers(25)
        sounds.play('match_light')

    # ── Fuel & Item actions ───────────────────────────────────────────────────
    def _add_tinder(self):
        if self.inv_tinder <= 0:
            self._notify("Растопка закончилась!", color=COLOR_FAIL)
            return
        self.inv_tinder -= 1
        sounds.play('wood_drop')
        self.temperature = min(100.0, self.temperature + 16.0)
        self.fire.burst_embers(10)
        self._notify(f"Береста вспыхнула! (+16° тепла)  Осталось: {self.inv_tinder}")

    def _add_kindling(self):
        if self.inv_kindling <= 0:
            self._notify("Хворост закончился!", color=COLOR_FAIL)
            return
        self.inv_kindling -= 1
        sounds.play('wood_drop')
        self.temperature = min(100.0, self.temperature + 18.0)
        self.fire.burst_embers(15)
        self._notify(f"Хворост трещит в огне! (+18° тепла)  Осталось: {self.inv_kindling}")

    def _add_log(self):
        if self.inv_logs <= 0:
            self._notify("Поленья закончились!", color=COLOR_FAIL)
            return

        sounds.play('wood_drop')
        # Realistic penalty: heavy logs smother a weak fire!
        if self.temperature < 25.0:
            self.inv_logs -= 1
            self.temperature = max(1.0, self.temperature - 9.0)
            self._notify("Тяжёлое полено задавило слабый огонёк! Нужно было сначала прогреть костёр!", color=COLOR_FAIL)
        else:
            self.inv_logs -= 1
            mat_mult = MATERIALS[self.selected_mat]["heat_mul"]
            gain = int(26.0 * mat_mult)
            self.temperature = min(100.0, self.temperature + gain)
            self.fire.burst_embers(20)
            self._notify(f"Полено занялось жаром! (+{gain}° тепла)  Осталось: {self.inv_logs}")

    def _use_poker(self):
        if self.poker_cooldown > 0:
            self._notify("Угли уже расшевелены, дай разгореться!", color=COLOR_TEXT_DIM)
            return
        self.poker_cooldown = 4.0
        sounds.play('poker_poke')
        self.fire.burst_embers(25)
        self.temperature = min(100.0, self.temperature + 6.0)
        self._notify("Разворошил угли: пепел осел, пламя ожило! (+6°)")

    # ── Event handling ────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

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

            # Forward events to ignition mini-game
            if self.state == STATE_IGNITION and self.ignition_game:
                self.ignition_game.handle_event(event)

            # UI clicks
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
                if self.btn_use_tinder.handle_event(event):
                    self._add_tinder()
                elif self.btn_use_kindling.handle_event(event):
                    self._add_kindling()
                elif self.btn_use_logs.handle_event(event):
                    self._add_log()
                elif self.btn_use_poker.handle_event(event):
                    self._use_poker()

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
                self._notify("Костёр занялся пламенем!", color=COLOR_WIN)
                self._go_burning()
            elif self.ignition_game.failed:
                self.state = STATE_FAIL

        elif self.state == STATE_BURNING:
            self._update_burning(dt)

        self.fire.update()
        sounds.update_fire_audio(self.temperature, dt)

    def _update_burning(self, dt):
        mat = MATERIALS[self.selected_mat]
        decay = TEMP_DECAY_BASE * mat["decay_mul"]
        decay -= self.weather.temp_modifier
        self.temperature -= decay

        # Blowing mechanic
        if self.blowing and self.breath > 0:
            self.breath = max(0.0, self.breath - BREATH_DEPLETE_RATE)
            if random.random() < 0.12:
                sounds.play('blow')
            if self.breath <= 0:
                self.temperature -= BREATH_EMPTY_PENALTY
            else:
                self.temperature += TEMP_BLOW_BOOST * mat["heat_mul"]
                if random.random() < 0.2:
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

        # Update button labels with remaining counts
        self.btn_use_tinder.label   = f"1: Растопка ({self.inv_tinder})"
        self.btn_use_kindling.label = f"2: Хворост ({self.inv_kindling})"
        self.btn_use_logs.label     = f"3: Полено ({self.inv_logs})"
        self.btn_use_poker.label    = "4: Ворошить (кд...)" if self.poker_cooldown > 0 else "4: Ворошить угли"

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        self.scenery.draw(self.screen, self.time_sec)
        draw_stones_and_logs(self.screen, self.selected_mat)
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

        # Notifications
        if self.notif_t > 0:
            alpha = min(255, int(self.notif_t * 6))
            draw_notification(self.screen, self.notif, 145, color=self.notif_color, alpha=alpha)

        pygame.display.flip()

    def _draw_start(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "КОСТЁР", SCREEN_W // 2, 110,
                  size=FONT_SIZE_LARGE + 18, color=COLOR_TEXT_HIGHLIGHT,
                  anchor="center", shadow=True)
        draw_text(self.screen, "Атмосферный симулятор выживания у огня",
                  SCREEN_W // 2, 175, size=FONT_SIZE_MEDIUM,
                  color=COLOR_TEXT_DIM, anchor="center")

        instructions = [
            "Тактильный розжиг: чиркай спичкой, крути колёсико зажигалки или бей огнивом.",
            "Прячь пламя от ветра и дождя (ПКМ), пока несёшь огонь к растопке.",
            "Не бросай тяжелое бревно в слабый огонь — оно задушит его!",
            "Подкладывай растопку и хворост, вороши угли и продержись 60 секунд.",
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
        # Draw the active ignition game on top of the campfire clearing
        if self.ignition_game:
            self.ignition_game.draw(self.screen)

        # Weather status in corner
        if self.weather.label and self.weather.label != "Тихо":
            wc = COLOR_FAIL if (self.weather.is_raining or self.weather.is_strong_wind) else COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, f"Погода: {self.weather.label}", SCREEN_W // 2, 25,
                      size=FONT_SIZE_SMALL, color=wc, anchor="midtop")

    def _draw_burning(self):
        # HUD Panel
        panel = Panel((10, 10, 230, 220), "")
        panel.draw(self.screen)

        self.bar_temp.draw(self.screen)
        self.bar_breath.draw(self.screen)
        self.btn_use_tinder.draw(self.screen)
        self.btn_use_kindling.draw(self.screen)
        self.btn_use_logs.draw(self.screen)
        self.btn_use_poker.draw(self.screen)

        # Timer
        rem = max(0.0, BURN_GOAL_SECONDS - self.burn_timer)
        draw_text(self.screen, f"Выжить: {int(rem)}с", SCREEN_W - 25, 20,
                  size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_HIGHLIGHT, anchor="topright", shadow=True)

        temp_label = ("Угли" if self.temperature < 25 else
                      "Разгорается" if self.temperature < 55 else
                      "Яркое пламя" if self.temperature < 82 else "Жаркий костёр!")
        draw_text(self.screen, temp_label, SCREEN_W - 25, 52,
                  size=FONT_SIZE_SMALL, color=COLOR_TEXT_DIM, anchor="topright")

        if self.weather.label and self.weather.label != "Тихо":
            wc = COLOR_FAIL if (self.weather.is_raining or self.weather.is_strong_wind) else COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, self.weather.label, SCREEN_W // 2, 20,
                      size=FONT_SIZE_SMALL, color=wc, anchor="midtop")

        # Controls hint bar at bottom
        hint = "ПРОБЕЛ: дуть на угли  |  1: Береста  |  2: Хворост  |  3: Полено  |  4: Ворошить"
        draw_text(self.screen, hint, SCREEN_W // 2, SCREEN_H - 24,
                  size=FONT_SIZE_TINY, color=(200, 180, 140), anchor="center")

    def _draw_end(self, win: bool):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        if win:
            draw_text(self.screen, "Костёр покорился тебе!", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 8, color=COLOR_WIN, anchor="center", shadow=True)
            draw_text(self.screen, "Ты продержал огонь 60 секунд сквозь лесную ночь.",
                      SCREEN_W // 2, 245, size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_MAIN, anchor="center")
        else:
            draw_text(self.screen, "Огонь угас в темноте...", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 8, color=COLOR_FAIL, anchor="center", shadow=True)
            fail_reason = ""
            if self.ignition_game and self.ignition_game.failed and self.ignition_game.fail_reason:
                fail_reason = self.ignition_game.fail_reason
            elif self.temperature <= 0:
                fail_reason = "Костру не хватило жара, и угли остыли."
            draw_text(self.screen, fail_reason, SCREEN_W // 2, 245,
                      size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_MAIN, anchor="center")
            draw_text(self.screen, "Внимательно следи за ветром и не бросай тяжёлые поленья в слабый огонёк.",
                      SCREEN_W // 2, 290, size=FONT_SIZE_SMALL, color=COLOR_TEXT_DIM, anchor="center")

        self.btn_play_again.draw(self.screen)
        self.btn_back_to_prep.draw(self.screen)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
