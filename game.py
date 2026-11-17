"""
game.py — Campfire Simulator with Inscryption-inspired atmosphere:
- Separate Stick & Marshmallow Bag (skewer a marshmallow onto the stick, eat once, stick becomes empty)
- "Forest Attention" mechanic: too cold (<25) attracts shadows, too bright (>75) attracts the Forest Entity!
"""
import pygame
import random
import math

from fire import FireSystem
from events import WeatherSystem
from sound_synth import sounds
from ignition import MatchIgnition, LighterIgnition, FlintIgnition
from textures import TextureManager
from ui import (
    Button, Card, Bar, Panel, draw_text, draw_notification,
    draw_vignette, draw_grain, draw_woodcut_border, draw_scratchy_text,
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

TEMP_DECAY_BASE          = 0.55
TEMP_BLOW_BOOST          = 4.50
BREATH_MAX               = 1.0
BREATH_DEPLETE_RATE      = 0.22
BREATH_REFILL_RATE       = 0.35
BREATH_EMPTY_PENALTY     = 1.20

BURN_GOAL_SECONDS = 180.0

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
#  Forest Scenery with Wind Sway, Small Eyes (Low Fire) & Tall Entity (High Fire)
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

        self.fireflies = []
        for _ in range(12):
            self.fireflies.append([
                random.uniform(40, SCREEN_W - 40),
                random.uniform(220, 480),
                random.uniform(0, math.pi * 2),
                random.uniform(0.4, 1.1)
            ])

        self.eye_spots = [
            (110, 325), (185, 315), (250, 330),
            (555, 328), (630, 318), (705, 332)
        ]

    def draw(self, surface, time_sec, wind_strength=0.0, fire_temp=50.0, attention=0.0):
        # 1. Night sky gradient
        for y in range(0, FIRE_CY + 15):
            ratio = y / (FIRE_CY + 15)
            r = int(5 + 12 * ratio)
            g = int(8 + 14 * ratio)
            b = int(18 + 16 * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

        # 2. Moon crescent
        pygame.draw.circle(surface, (220, 225, 200), (680, 85), 24)
        pygame.draw.circle(surface, (6, 10, 20), (670, 80), 22)

        # 3. Twinkling stars
        for s in self.stars:
            alpha = int(s[2] * (0.65 + 0.35 * math.sin(time_sec * s[3])))
            col = (alpha, alpha, min(255, int(alpha * 1.1)))
            pygame.draw.circle(surface, col, (s[0], s[1]), s[4])

        # 4. Swaying distant pines
        sway = math.sin(time_sec * 2.2) * (2.0 + abs(wind_strength) * 0.22) + (wind_strength * 0.15)
        self._draw_pines(surface, y_base=345, height=110, count=16, color=(10, 15, 18), sway=sway)

        # 5. Tall Horned Silhouette (Inscryption vibe) when fire attracts attention!
        if attention > 0.15:
            self._draw_forest_entity(surface, time_sec, attention)

        # 6. Closer side trees
        self._draw_side_trees(surface, sway * 1.3)

        # 7. Ground
        for y in range(FIRE_CY, SCREEN_H):
            ratio = (y - FIRE_CY) / (SCREEN_H - FIRE_CY)
            r = max(4, int(24 - 15 * ratio))
            g = max(3, int(18 - 11 * ratio))
            b = max(2, int(12 - 8 * ratio))
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_W, y))

        # 8. Small wolf eyes when fire is too weak (< 35 temp)
        if fire_temp < 35.0:
            danger = (35.0 - fire_temp) / 35.0
            num_eyes = int(danger * len(self.eye_spots)) + 1
            for idx in range(min(num_eyes, len(self.eye_spots))):
                ex, ey = self.eye_spots[idx]
                if math.sin(time_sec * 1.7 + idx * 2.1) > -0.7:
                    eye_col = (255, int(170 - 120 * danger), 40)
                    pygame.draw.circle(surface, eye_col, (ex - 4, ey), 2)
                    pygame.draw.circle(surface, eye_col, (ex + 4, ey), 2)

        # 9. Fireflies
        for ff in self.fireflies:
            ff[0] += math.cos(time_sec * ff[3] + ff[2]) * 0.35 + wind_strength * 0.01
            ff[1] += math.sin(time_sec * 1.3 + ff[2]) * 0.25
            if ff[0] < 20: ff[0] = SCREEN_W - 20
            if ff[0] > SCREEN_W - 20: ff[0] = 20
            glow = 0.5 + 0.5 * math.sin(time_sec * 3.5 + ff[2])
            if glow > 0.3:
                c = int(220 * glow)
                pygame.draw.circle(surface, (c, c, int(80 * glow)), (int(ff[0]), int(ff[1])), 2)

    def _draw_forest_entity(self, surface, time_sec, attention):
        """Зловещее присутствие Хозяина Леса в стиле Inscryption:
        Теневой силуэт с ветвистыми рогами и немигающими глазами между соснами."""
        if attention < 0.05:
            return

        frame = min(5, int(attention * 6))
        spirit_tex = TextureManager.get(f'forest_spirit_{frame + 1}')
        if not spirit_tex:
            return

        ex = 540 + int(math.sin(time_sec * 0.35) * 4)
        ey = 160 + int(math.cos(time_sec * 0.25) * 3)

        # Alpha fade in based on attention
        alpha = int(min(255, max(40, attention * 300)))
        spirit_s = spirit_tex.copy()
        spirit_s.set_alpha(alpha)
        surface.blit(spirit_s, (ex, ey))

        # Additional eerie glow when enraged
        if attention > 0.70:
            glow_r = int(40 * (attention - 0.7) / 0.3)
            if glow_r > 2:
                gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (80, 220, 255, 60), (glow_r, glow_r), glow_r)
                surface.blit(gs, (ex + 68 - glow_r, ey + 40 - glow_r), special_flags=pygame.BLEND_RGBA_ADD)

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
            pygame.draw.rect(surface, (14, 11, 8), (x + w // 2 - 12, 350, 24, 250))
            for tier in range(4):
                tw = int(w * (0.45 + tier * 0.18))
                th = int(h * 0.32)
                ty = 130 + tier * 55
                tier_sway = int(sway * (1.2 - tier * 0.25))
                pts = [(x + w // 2 + tier_sway, ty),
                       (x + w // 2 - tw // 2, ty + th),
                       (x + w // 2 + tw // 2, ty + th)]
                pygame.draw.polygon(surface, (12, 16, 14), pts)


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

        self.is_fullscreen = False
        self.paused        = False

        self.selected_mat  = "pine"
        self.selected_tool = "match"

        self._reset()

    def _reset(self):
        # Сохраняем выбор снаряжения (чтобы не сбрасывался при "Играть снова")
        saved_mat  = getattr(self, 'selected_mat',  'pine')
        saved_tool = getattr(self, 'selected_tool', 'match')

        self.state         = STATE_START
        self.temperature   = 0.0
        self.breath        = BREATH_MAX
        self.blowing       = False
        self.rmb_blowing   = False
        self.burn_timer    = 0.0

        # Внимание Леса (0.0 .. 1.0): растёт, если жечь костёр слишком ярко (>72°)!
        self.forest_attention = 0.0
        self.fail_custom_reason = ""

        # Запасы на поляне
        self.inv_tinder       = 4
        self.inv_kindling     = 6
        self.inv_bark         = 3   # Кора — между хворостом и поленом
        self.inv_moss         = 4   # Мох — медленное горение
        self.inv_logs         = 5
        self.inv_marshmallows = 4  # Количество зефирок в пакетике!
        self.poker_cooldown   = 0.0

        # Состояние палочки и зефирки
        self.stick_has_marsh  = False  # Наколота ли сейчас зефирка на палочку
        self.marsh_roast      = 0.0
        self.marsh_eaten_count = 0

        # Перетаскивание мышью: 'tinder', 'kindling', 'bark', 'moss', 'log', 'poker', 'stick', None
        self.drag_item = None
        self.mouse_pos = [400, 300]
        self.prev_mouse_pos = [400, 300]
        self.poke_accum = 0.0

        # 8 слотов предметов на земле внизу экрана (ширина ~88px, начинаются с y=480)
        SLOT_W = 88
        SLOT_H = 78
        SLOT_Y = 480
        SLOT_GAP = 4
        total_w = 8 * SLOT_W + 7 * SLOT_GAP
        slot_start_x = (SCREEN_W - total_w) // 2

        def slot_rect(idx):
            return pygame.Rect(slot_start_x + idx * (SLOT_W + SLOT_GAP), SLOT_Y, SLOT_W, SLOT_H)

        self.rect_tinder     = slot_rect(0)
        self.rect_kindling   = slot_rect(1)
        self.rect_bark       = slot_rect(2)
        self.rect_moss       = slot_rect(3)
        self.rect_logs       = slot_rect(4)
        self.rect_poker      = slot_rect(5)
        self.rect_stick      = slot_rect(6)
        self.rect_marsh_bag  = slot_rect(7)
        self.fire_drop_zone  = pygame.Rect(FIRE_CX - 95, FIRE_CY - 70, 190, 125)

        self.ignition_game = None

        self.notif       = ""
        self.notif_t     = 0.0
        self.notif_color = COLOR_TEXT_HIGHLIGHT

        self.fire.set_temperature(0)
        self.fire.clear_fuel()
        self.weather.force_calm()

        # Восстанавливаем выбор снаряжения
        self.selected_mat  = saved_mat
        self.selected_tool = saved_tool

        self._build_ui()

    def _build_ui(self):
        self.btn_start = Button((SCREEN_W // 2 - 110, 420, 220, 48),
                                "Начать симуляцию", size=FONT_SIZE_MEDIUM)

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

        # Показатели сверху слева
        self.bar_temp   = Bar((20, 16, 205, 18), "Жар (25..75°)")
        self.bar_breath = Bar((20, 39, 205, 18), "Дыхание",
                              lo_color=COLOR_BAR_BREATH,
                              mid_color=COLOR_BAR_BREATH,
                              hi_color=COLOR_BAR_BREATH)
        self.bar_attention = Bar((20, 62, 205, 18), "Внимание леса",
                                 lo_color=(70, 140, 90),
                                 mid_color=(220, 140, 30),
                                 hi_color=(220, 35, 35))

        self.btn_play_again   = Button((SCREEN_W // 2 - 110, 430, 220, 48),
                                       "Играть снова", size=FONT_SIZE_MEDIUM)
        self.btn_back_to_prep = Button((SCREEN_W // 2 - 110, 490, 220, 42),
                                       "Выбрать другое снаряжение", size=FONT_SIZE_SMALL)

        # ── Кнопки меню паузы (ESC) ──
        self.btn_pause_resume  = Button((SCREEN_W // 2 - 125, 175, 250, 44), "Продолжить (ESC)")
        self.btn_pause_fs      = Button((SCREEN_W // 2 - 125, 230, 250, 44), "Экран: ПОЛНЫЙ (F11)")
        self.btn_pause_mute    = Button((SCREEN_W // 2 - 125, 285, 250, 44), "Звук: ВКЛ (M)")
        self.btn_pause_restart = Button((SCREEN_W // 2 - 125, 340, 250, 44), "Начать заново")
        self.btn_pause_prep    = Button((SCREEN_W // 2 - 125, 395, 250, 44), "Сменить снаряжение")
        self.btn_pause_quit    = Button((SCREEN_W // 2 - 125, 450, 250, 44), "Выйти из игры")

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        try:
            pygame.display.toggle_fullscreen()
        except Exception as e:
            print(f"Fullscreen toggle error: {e}")
        self.btn_pause_fs.label = "Экран: ОКОННЫЙ (F11)" if self.is_fullscreen else "Экран: ПОЛНЫЙ (F11)"

    def _toggle_mute(self):
        sounds.enabled = not sounds.enabled
        self.btn_mute.label = "Звук: ВКЛ (M)" if sounds.enabled else "Звук: ВЫКЛ (M)"
        self.btn_pause_mute.label = "Звук: ВКЛ (M)" if sounds.enabled else "Звук: ВЫКЛ (M)"

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
        self.forest_attention = 0.0
        self.fail_custom_reason = ""
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
        self.temperature = 28.0
        self.burn_timer  = 0.0
        self.forest_attention = 0.0
        self.fire.set_temperature(self.temperature)
        self.fire.add_fuel_visual('tinder')
        self.fire.add_fuel_visual('kindling')
        self.fire.burst_embers(25)
        sounds.play('match_light')
        self._notify("Поддерживай огонь, но не жги >75° слишком долго — привлечёшь Нечто из леса!", 4.2)

    # ── Fuel & Item actions ───────────────────────────────────────────────────
    def _add_tinder(self):
        if self.inv_tinder <= 0:
            self._notify("Береста закончилась!", color=COLOR_FAIL)
            return
        self.inv_tinder -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('tinder')
        self.temperature = min(100.0, self.temperature + 15.0)
        self.fire.burst_embers(12)
        self._notify("Береста вспыхнула! (+15° жара)")

    def _add_kindling(self):
        if self.inv_kindling <= 0:
            self._notify("Хворост закончился!", color=COLOR_FAIL)
            return
        self.inv_kindling -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('kindling')
        self.temperature = min(100.0, self.temperature + 18.0)
        self.fire.burst_embers(16)
        self._notify("Сухие ветки весело затрещали! (+18° жара)")

    def _add_bark(self):
        if self.inv_bark <= 0:
            self._notify("Кора закончилась!", color=COLOR_FAIL)
            return
        self.inv_bark -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('kindling')  # кора визуально как хворост
        self.temperature = min(100.0, self.temperature + 12.0)
        self.fire.burst_embers(10)
        self._notify("Кора занялась! (+12° жара)")

    def _add_moss(self):
        if self.inv_moss <= 0:
            self._notify("Мох закончился!", color=COLOR_FAIL)
            return
        self.inv_moss -= 1
        sounds.play('wood_drop')
        self.fire.add_fuel_visual('tinder')  # мох визуально как трут
        self.temperature = min(100.0, self.temperature + 8.0)
        self.fire.burst_embers(6)
        self._notify("Влажный мох медленно тлеет... (+8° жара)")

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
            gain = int(25.0 * mat_mult)
            self.temperature = min(100.0, self.temperature + gain)
            self.fire.burst_embers(22)
            self._notify(f"Бревно занялось жаром! (+{gain}°)")

    def _use_poker(self):
        if self.poker_cooldown > 0:
            return
        self.poker_cooldown = 2.2
        sounds.play('poker_poke')
        self.fire.burst_embers(25)
        self.temperature = min(100.0, self.temperature + 6.5)
        self._notify("Угли разворошены кочергой! (+6.5° жара)")

    def _try_skewer_marshmallow(self):
        """Накалывает одну зефирку из пакетика на пустую палочку."""
        if self.stick_has_marsh:
            return
        if self.inv_marshmallows <= 0:
            self._notify("Пакетик пуст! Зефирок больше не осталось.", color=COLOR_FAIL)
            return
        self.inv_marshmallows -= 1
        self.stick_has_marsh = True
        self.marsh_roast = 0.0
        sounds.play('wood_drop')
        self._notify(f"Наколол зефирку на палочку! (В пакетике осталось: {self.inv_marshmallows})")

    # ── Event handling ────────────────────────────────────────────────────────
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.MOUSEMOTION:
                self.prev_mouse_pos = list(self.mouse_pos)
                self.mouse_pos = list(event.pos)

                # Если держим пустую палочку и провели ей над пакетиком с зефирками — накалываем!
                if self.state == STATE_BURNING and self.drag_item == 'stick' and not self.stick_has_marsh:
                    if self.rect_marsh_bag.collidepoint(event.pos):
                        self._try_skewer_marshmallow()

                # Если держим мох над кострищем при перетаскивании — ничего (сбросим в MOUSEBUTTONUP)

            if self.btn_mute.handle_event(event):
                self._toggle_mute()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue
                if event.key == pygame.K_ESCAPE:
                    if self.state in (STATE_BURNING, STATE_IGNITION):
                        self.paused = not self.paused
                        continue
                    elif self.paused:
                        self.paused = False
                        continue
                    else:
                        self.running = False
                        return
                if event.key == pygame.K_m:
                    self._toggle_mute()

                if self.state == STATE_BURNING and not self.paused:
                    if event.key == pygame.K_SPACE:
                        self.blowing = True
                    elif event.key == pygame.K_1:
                        self._add_tinder()
                    elif event.key == pygame.K_2:
                        self._add_kindling()
                    elif event.key == pygame.K_3:
                        self._add_bark()
                    elif event.key == pygame.K_4:
                        self._add_moss()
                    elif event.key == pygame.K_5:
                        self._add_log()
                    elif event.key == pygame.K_6 or event.key == pygame.K_f:
                        self._use_poker()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.blowing = False

            if self.paused:
                if self.btn_pause_resume.handle_event(event):
                    self.paused = False
                elif self.btn_pause_fs.handle_event(event):
                    self._toggle_fullscreen()
                elif self.btn_pause_mute.handle_event(event):
                    self._toggle_mute()
                elif self.btn_pause_restart.handle_event(event):
                    self.paused = False
                    self._reset()
                    self._go_ignition()
                elif self.btn_pause_prep.handle_event(event):
                    self.paused = False
                    self._reset()
                    self._go_prep()
                elif self.btn_pause_quit.handle_event(event):
                    self.running = False
                continue

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
                elif self.rect_bark.collidepoint(pos) and self.inv_bark > 0:
                    self.drag_item = 'bark'
                elif self.rect_moss.collidepoint(pos) and self.inv_moss > 0:
                    self.drag_item = 'moss'
                elif self.rect_logs.collidepoint(pos) and self.inv_logs > 0:
                    self.drag_item = 'log'
                elif self.rect_poker.collidepoint(pos):
                    self.drag_item = 'poker'
                    self.poke_accum = 0.0
                elif self.rect_stick.collidepoint(pos):
                    self.drag_item = 'stick'
                elif self.rect_marsh_bag.collidepoint(pos):
                    # Если кликнули по пакетику — берём палочку и сразу накалываем зефирку
                    self.drag_item = 'stick'
                    self._try_skewer_marshmallow()

            elif event.button == 3:  # ПКМ — съесть зефирку с палочки ИЛИ дуть на костёр
                if self.drag_item == 'stick' and self.stick_has_marsh:
                    if 0.45 <= self.marsh_roast <= 0.95:
                        # Съели! Палочка становится ПУСТОЙ и возвращается на место
                        self.stick_has_marsh = False
                        self.marsh_roast = 0.0
                        self.marsh_eaten_count += 1
                        self.drag_item = None  # кладём палочку обратно!
                        self.breath = BREATH_MAX
                        self.forest_attention = max(0.0, self.forest_attention - 0.20)
                        sounds.play('match_light')
                        self._notify("Зефирка съедена! Дыхание 100%, страх отступил! Наколи новую из пачки.", color=COLOR_WIN)
                    elif self.marsh_roast > 0.95:
                        # Стряхнули уголёк — палочка пустая!
                        self.stick_has_marsh = False
                        self.marsh_roast = 0.0
                        self._notify("Сгоревший уголёк стряхнут с палочки. Наколи новую зефирку из пакетика!", color=COLOR_FAIL)
                    else:
                        self._notify("Зефирка ещё сырая! Подержи её над огнём.", color=COLOR_TEXT_DIM)
                else:
                    self.rmb_blowing = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.drag_item:
                if self.fire_drop_zone.collidepoint(event.pos):
                    if self.drag_item == 'tinder':
                        self._add_tinder()
                    elif self.drag_item == 'kindling':
                        self._add_kindling()
                    elif self.drag_item == 'bark':
                        self._add_bark()
                    elif self.drag_item == 'moss':
                        self._add_moss()
                    elif self.drag_item == 'log':
                        self._add_log()
                self.drag_item = None

            elif event.button == 3:
                self.rmb_blowing = False

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        if self.paused:
            return

        self.time_sec += dt
        self.weather.update(dt)
        self.fire.set_wind(self.weather.wind_strength)
        self.fire.is_raining = self.weather.is_raining

        # Физическая реакция костра на дождь: пар и шипение от капель
        if self.weather.is_raining and self.state == STATE_BURNING and self.temperature > 12.0:
            if random.random() < 0.35:
                self.fire.trigger_rain_hit()

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
        # Плавное, реалистичное остывание с учётом времени (секунды, а не кадры!)
        decay = (TEMP_DECAY_BASE * mat["decay_mul"] - self.weather.temp_modifier) * dt
        self.temperature -= decay

        # Интерактив кочергой
        mx, my = self.mouse_pos
        if self.drag_item == 'poker' and self.fire_drop_zone.collidepoint((mx, my)):
            dist = math.hypot(mx - self.prev_mouse_pos[0], my - self.prev_mouse_pos[1])
            self.poke_accum += dist
            if dist > 4 and random.random() < 0.35:
                self.fire.burst_embers(2)
            if self.poke_accum > 95:
                self.poke_accum = 0.0
                self._use_poker()

        # Жарка зефирки (только если она наколота на палочку!)
        if self.drag_item == 'stick' and self.stick_has_marsh:
            dist_x = abs(mx - FIRE_CX)
            if dist_x < 75 and (FIRE_CY - 140 < my < FIRE_CY + 10) and self.temperature > 10:
                if my > FIRE_CY - 35:
                    self.marsh_roast += dt * 0.18
                else:
                    self.marsh_roast += dt * 0.08 * (self.temperature / 50.0)

        # Раздувание
        is_blowing = self.blowing or self.rmb_blowing
        if is_blowing and self.breath > 0:
            self.breath = max(0.0, self.breath - BREATH_DEPLETE_RATE * dt)
            if random.random() < 0.12:
                sounds.play('blow')
            if self.breath <= 0:
                self.temperature -= BREATH_EMPTY_PENALTY * dt
            else:
                self.temperature += (TEMP_BLOW_BOOST * mat["heat_mul"]) * dt
                if random.random() < 0.22:
                    self.fire.burst_embers(2)
        else:
            self.breath = min(BREATH_MAX, self.breath + BREATH_REFILL_RATE * dt)

        self.temperature = max(0.0, min(100.0, self.temperature))
        self.fire.set_temperature(self.temperature)

        # ── Механика "Внимание Леса" (Чем ярче жжёшь >72°, тем сильнее привлекаешь Сущность!) ──
        if self.temperature > 72.0:
            excess = (self.temperature - 72.0) / 28.0
            self.forest_attention = min(1.0, self.forest_attention + dt * (0.09 + 0.14 * excess))
        else:
            self.forest_attention = max(0.0, self.forest_attention - dt * 0.06)

        if self.forest_attention >= 1.0:
            self.fail_custom_reason = "Твой огромный костёр привлёк Хозяина Леса из чащи..."
            self.state = STATE_FAIL
            sounds.play('blow')
            return

        if self.temperature > 5.0:
            self.burn_timer += dt

        if self.burn_timer >= BURN_GOAL_SECONDS:
            self.state = STATE_WIN
            sounds.play('match_light')
        elif self.temperature <= 0.0:
            self.fail_custom_reason = "Костёр погас, и ночные тени сомкнулись вокруг поляны."
            self.state = STATE_FAIL
            sounds.play('blow')

        self.bar_temp.set_value(self.temperature / 100.0)
        self.bar_breath.set_value(self.breath)
        self.bar_attention.set_value(self.forest_attention)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        fire_vis_temp = self.temperature if self.state == STATE_BURNING else 45.0
        att = self.forest_attention if self.state == STATE_BURNING else 0.0
        # 1. Ночное небо, луна, звёзды и дальние сосны
        self.scenery.draw(self.screen, self.time_sec, self.weather.wind_strength, fire_vis_temp, att)

        # 2. 2.5D Перспективная земля диорамы с честным затуханием света (без жёлтого круга!)
        self.fire.draw_ground(self.screen)

        # 3. 2.5D Костёр: задние камни -> угли -> пламя -> наклонные дрова -> передние камни -> искры -> пар
        self.fire.draw(self.screen)

        # 4. Погодные частицы
        self.weather.draw(self.screen)

        # 5. Мягкая подсветка нижних стволов леса
        self.fire.draw_ambient_light(self.screen)

        # Виньетка и лёгкое зерно накладываются ТОЛЬКО на игровой мир (под UI!),
        # чтобы кнопки, текст и слоты инвентаря оставались яркими и чёткими!
        draw_vignette(self.screen)
        draw_grain(self.screen, self.time_sec)

        # Мерцание экрана при высоком внимании леса (>0.65)
        if self.state == STATE_BURNING and self.forest_attention > 0.65:
            fear_alpha = int(20 * ((self.forest_attention - 0.65) / 0.35) * (0.6 + 0.4 * math.sin(self.time_sec * 8.0)))
            if fear_alpha > 0:
                fear_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                fear_surf.fill((160, 10, 10, fear_alpha))
                self.screen.blit(fear_surf, (0, 0))

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

        # Меню паузы и настроек на ESC
        if self.paused:
            self._draw_pause_menu()

        pygame.display.flip()

    def _draw_start(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "КОСТЁР", SCREEN_W // 2, 110,
                  size=FONT_SIZE_LARGE + 18, color=COLOR_TEXT_HIGHLIGHT,
                  anchor="center", shadow=True)
        draw_text(self.screen, "Выживание у огня в ночной чаще",
                  SCREEN_W // 2, 175, size=FONT_SIZE_MEDIUM,
                  color=COLOR_TEXT_DIM, anchor="center")

        instructions = [
            "Поддерживай огонь, но следи за шкалой «Внимание леса»!",
            "Слишком слабый огонь (<35°) манит волков, слишком яркий (>72°) зовёт Хозяина Леса.",
            "Бери пустую палочку, накалывай зефирку из пакетика и жарь над углями.",
            "Съеденная золотистая зефирка успокаивает нервы и снижает Внимание леса!",
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
        # 1. Панель показателей сверху слева
        panel = Panel((10, 8, 225, 80), "")
        panel.draw(self.screen)
        draw_woodcut_border(self.screen, panel.rect, (100, 75, 45))
        self.bar_temp.draw(self.screen)
        self.bar_breath.draw(self.screen)
        self.bar_attention.draw(self.screen)

        # 2. Таймер и погода
        rem = max(0.0, BURN_GOAL_SECONDS - self.burn_timer)
        draw_text(self.screen, f"До рассвета: {int(rem)}с", SCREEN_W - 25, 48,
                  size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_HIGHLIGHT, anchor="topright", shadow=True)

        if self.weather.label and self.weather.label != "Тихо":
            wc = COLOR_FAIL if (self.weather.is_raining or self.weather.is_strong_wind) else COLOR_TEXT_HIGHLIGHT
            draw_text(self.screen, self.weather.label, SCREEN_W // 2, 18,
                      size=FONT_SIZE_SMALL, color=wc, anchor="midtop")

        # Предупреждения
        if self.forest_attention > 0.5:
            draw_text(self.screen, "Огонь слишком яркий! Между соснами кто-то стоит и смотрит на пламя!",
                      SCREEN_W // 2, 44, size=FONT_SIZE_TINY, color=(255, 80, 80), anchor="midtop")
        elif self.temperature < 35.0:
            draw_text(self.screen, "Костёр гаснет... В кустах зажглись волчьи глаза!",
                      SCREEN_W // 2, 44, size=FONT_SIZE_TINY, color=(255, 160, 80), anchor="midtop")

        # 3. Подсветка зоны костра при перетаскивании топлива
        if self.drag_item in ('tinder', 'kindling', 'bark', 'moss', 'log'):
            hl = pygame.Surface((self.fire_drop_zone.width, self.fire_drop_zone.height), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 200, 80, 45), (0, 0, self.fire_drop_zone.width, self.fire_drop_zone.height), 2)
            self.screen.blit(hl, self.fire_drop_zone.topleft)

        # 4. Слоты предметов на земле
        self._draw_ground_items()

        # 5. Предмет в руке
        self._draw_dragged_item()

        hint = "ЛКМ: тащи предметы / ткни палочкой в зефир  |  ПКМ: съесть зефир / дуть  |  1..5: быстрый подброс"
        draw_text(self.screen, hint, SCREEN_W // 2, SCREEN_H - 14,
                  size=FONT_SIZE_TINY, color=(210, 190, 145), anchor="center")

    def _draw_ground_items(self):
        mx, my = self.mouse_pos

        def draw_slot(rect, title, subtitle, active=True, highlight_target=False):
            hovered = rect.collidepoint((mx, my)) and active
            bg = (58, 42, 26, 220) if (hovered or highlight_target) else (30, 22, 15, 190)
            border = (100, 230, 120) if highlight_target else (COLOR_TEXT_HIGHLIGHT if hovered else (90, 65, 40))
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(s, bg, (0, 0, rect.width, rect.height), border_radius=8)
            pygame.draw.rect(s, border, (0, 0, rect.width, rect.height), width=2, border_radius=8)
            self.screen.blit(s, rect.topleft)
            draw_text(self.screen, title, rect.centerx, rect.bottom - 24,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_MAIN if active else COLOR_TEXT_DIM, anchor="center")
            draw_text(self.screen, subtitle, rect.centerx, rect.bottom - 10,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT if active else COLOR_TEXT_DIM, anchor="center")

        # 1. Береста (1)
        draw_slot(self.rect_tinder, f"Береста ({self.inv_tinder})", "[1] +15°", self.inv_tinder > 0)
        if self.inv_tinder > 0:
            self.screen.blit(TextureManager.get('tinder', (44, 30)), (self.rect_tinder.centerx - 22, self.rect_tinder.y + 8))

        # 2. Хворост (2)
        draw_slot(self.rect_kindling, f"Хворост ({self.inv_kindling})", "[2] +18°", self.inv_kindling > 0)
        if self.inv_kindling > 0:
            self.screen.blit(TextureManager.get('kindling', (44, 30)), (self.rect_kindling.centerx - 22, self.rect_kindling.y + 8))

        # 3. Кора (3)
        draw_slot(self.rect_bark, f"Кора ({self.inv_bark})", "[3] +12°", self.inv_bark > 0)
        if self.inv_bark > 0:
            self.screen.blit(TextureManager.get('bark', (44, 30)), (self.rect_bark.centerx - 22, self.rect_bark.y + 8))

        # 4. Мох (4)
        draw_slot(self.rect_moss, f"Мох ({self.inv_moss})", "[4] +8°", self.inv_moss > 0)
        if self.inv_moss > 0:
            self.screen.blit(TextureManager.get('moss', (44, 30)), (self.rect_moss.centerx - 22, self.rect_moss.y + 8))

        # 5. Поленья (5)
        draw_slot(self.rect_logs, f"Поленья ({self.inv_logs})", "[5] Жар >25°", self.inv_logs > 0)
        if self.inv_logs > 0:
            self.screen.blit(TextureManager.get('log', (48, 30)), (self.rect_logs.centerx - 24, self.rect_logs.y + 8))

        # 6. Кочерга
        draw_slot(self.rect_poker, "Кочерга", "Ворошить", True)
        self.screen.blit(TextureManager.get('poker', (44, 30)), (self.rect_poker.centerx - 22, self.rect_poker.y + 8))

        # 7. Палочка (Рогатина для зефира)
        stick_sub = "С зефиркой!" if self.stick_has_marsh else "Пустая"
        draw_slot(self.rect_stick, "Палочка", stick_sub, True)
        pygame.draw.line(self.screen, (160, 125, 80),
                         (self.rect_stick.x + 16, self.rect_stick.y + 35),
                         (self.rect_stick.x + 68, self.rect_stick.y + 15), 3)
        if self.stick_has_marsh:
            m_col = self._get_marsh_color()
            pygame.draw.rect(self.screen, m_col, (self.rect_stick.x + 62, self.rect_stick.y + 9, 14, 12), border_radius=3)

        # 8. Пакетик с зефирками
        need_skewer = (self.drag_item == 'stick' and not self.stick_has_marsh and self.inv_marshmallows > 0)
        bag_sub = "Ткни палкой!" if need_skewer else "Пачка"
        draw_slot(self.rect_marsh_bag, f"Зефир ({self.inv_marshmallows})", bag_sub,
                  self.inv_marshmallows > 0, highlight_target=need_skewer)
        if self.inv_marshmallows > 0:
            self.screen.blit(TextureManager.get('marsh_bag', (44, 30)), (self.rect_marsh_bag.centerx - 22, self.rect_marsh_bag.y + 8))

    def _get_marsh_color(self):
        r = self.marsh_roast
        if r < 0.45:
            t = r / 0.45
            return (250, int(248 - 30 * t), int(245 - 80 * t))
        elif r <= 0.95:
            t = (r - 0.45) / 0.50
            return (int(245 - 45 * t), int(218 - 85 * t), int(165 - 115 * t))
        else:
            return (35, 30, 28)

    def _draw_dragged_item(self):
        if not self.drag_item:
            return
        mx, my = self.mouse_pos

        if self.drag_item in ('tinder', 'kindling', 'bark', 'moss', 'log'):
            tex = TextureManager.get(self.drag_item, (52, 34))
            self.screen.blit(tex, (mx - 26, my - 17))
            draw_text(self.screen, "Брось в костёр", mx, my - 26, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'poker':
            tex = TextureManager.get('poker', (56, 38))
            self.screen.blit(tex, (mx - 15, my - 15))
            draw_text(self.screen, "Води по углям туда-сюда!", mx, my - 22, size=FONT_SIZE_TINY, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        elif self.drag_item == 'stick':
            if not self.stick_has_marsh:
                stick_tex = TextureManager.get('stick', (120, 36))
                if stick_tex:
                    self.screen.blit(stick_tex, (mx - 60, my - 18))
                else:
                    pygame.draw.line(self.screen, (170, 135, 85), (mx + 80, my + 60), (mx, my), 4)
                draw_text(self.screen, "Палочка пустая! Наведи на ПАЧКУ ЗЕФИРА справа внизу, чтобы наколоть!",
                          mx, my - 26, size=FONT_SIZE_TINY, color=(130, 240, 150), anchor="center", shadow=True)
            else:
                if self.marsh_roast >= 0.95:
                    stage = 4
                    status = "СГОРЕЛА! Нажми ПКМ, чтобы стряхнуть уголёк с палочки"
                    sc = COLOR_FAIL
                elif self.marsh_roast >= 0.65:
                    stage = 3
                    status = f"КАРАМЕЛЬНАЯ ({int(self.marsh_roast * 100)}%)! Нажми ПКМ, чтобы съесть!"
                    sc = COLOR_WIN
                elif self.marsh_roast >= 0.35:
                    stage = 2
                    status = f"ЗОЛОТИСТАЯ ({int(self.marsh_roast * 100)}%)! Нажми ПКМ, чтобы съесть!"
                    sc = COLOR_WIN
                else:
                    stage = 1
                    status = f"Жарится: {int((self.marsh_roast / 0.35) * 100)}% (держи над пламенем)"
                    sc = COLOR_TEXT_HIGHLIGHT

                tex = TextureManager.get(f'marshmallow_{stage}', (110, 68))
                if tex:
                    self.screen.blit(tex, (mx - 55, my - 34))
                else:
                    m_col = self._get_marsh_color()
                    pygame.draw.rect(self.screen, m_col, (mx - 12, my - 10, 24, 18), border_radius=5)

                draw_text(self.screen, status, mx, my - 28, size=FONT_SIZE_TINY, color=sc, anchor="center", shadow=True)

    def _draw_pause_menu(self):
        """Отрисовка меню паузы и настроек на ESC."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        self.screen.blit(overlay, (0, 0))

        # Деревянная рамка меню паузы
        menu_panel = Panel((SCREEN_W // 2 - 150, 110, 300, 395), "")
        menu_panel.draw(self.screen)
        draw_woodcut_border(self.screen, menu_panel.rect, (130, 95, 55))

        draw_text(self.screen, "ПАУЗА / НАСТРОЙКИ", SCREEN_W // 2, 135,
                  size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_HIGHLIGHT, anchor="center")

        self.btn_pause_resume.draw(self.screen)
        self.btn_pause_fs.draw(self.screen)
        self.btn_pause_mute.draw(self.screen)
        self.btn_pause_restart.draw(self.screen)
        self.btn_pause_prep.draw(self.screen)
        self.btn_pause_quit.draw(self.screen)

    def _draw_end(self, win: bool):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        if win:
            draw_text(self.screen, "Ты пережил эту ночь!", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 6, color=COLOR_WIN, anchor="center", shadow=True)
            draw_text(self.screen, f"Рассвет отпугнул тени леса. Съедено зефирок: {self.marsh_eaten_count}",
                      SCREEN_W // 2, 245, size=FONT_SIZE_MEDIUM, color=COLOR_TEXT_MAIN, anchor="center")
        else:
            draw_text(self.screen, "Ночной лес поглотил тебя...", SCREEN_W // 2, 180,
                      size=FONT_SIZE_LARGE + 6, color=COLOR_FAIL, anchor="center", shadow=True)
            fail_reason = self.fail_custom_reason
            if self.ignition_game and self.ignition_game.failed and self.ignition_game.fail_reason:
                fail_reason = self.ignition_game.fail_reason
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