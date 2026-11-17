"""
ui.py — Reusable UI components: buttons, bars, text helpers, card selectors.
All magic numbers are defined as named constants at the top.
"""
import pygame
import math
import random

# ── Colours ───────────────────────────────────────────────────────────────────
COLOR_BG_DARK        = (20,  15,  10)
COLOR_PANEL          = (40,  30,  20)
COLOR_PANEL_BORDER   = (90,  65,  40)
COLOR_TEXT_MAIN      = (245, 220, 170)
COLOR_TEXT_DIM       = (160, 130,  90)
COLOR_TEXT_HIGHLIGHT = (255, 200,  50)
COLOR_BTN_NORMAL     = (60,  45,  25)
COLOR_BTN_HOVER      = (90,  65,  35)
COLOR_BTN_ACTIVE     = (120,  85,  40)
COLOR_BTN_BORDER     = (140, 100,  50)
COLOR_BAR_BG         = (30,  22,  12)
COLOR_BAR_TEMP_LOW   = (180,  40,  10)
COLOR_BAR_TEMP_MID   = (220, 120,  20)
COLOR_BAR_TEMP_HIGH  = (255, 220,  50)
COLOR_BAR_BREATH     = ( 60, 160, 220)
COLOR_BAR_BORDER     = (100,  75,  40)
COLOR_CARD_SELECTED  = (160, 110,  40)
COLOR_WIN            = ( 50, 200,  80)
COLOR_FAIL           = (200,  50,  40)

# ── Layout ────────────────────────────────────────────────────────────────────
BTN_CORNER_RADIUS    = 6
BAR_HEIGHT           = 22
BAR_CORNER           = 4
CARD_CORNER          = 8
CARD_PADDING         = 10

# ── Typography ────────────────────────────────────────────────────────────────
FONT_SIZE_LARGE      = 36
FONT_SIZE_MEDIUM     = 22
FONT_SIZE_SMALL      = 16
FONT_SIZE_TINY       = 13

# ── Inscryption effects: pre-allocated surfaces ───────────────────────────────
_vignette_surf = None   # created once on first call, reused every frame
_grain_surf    = None   # pre-allocated grain surface
_grain_frame   = 0      # counts rendered frames so we regenerate grain every 3


class FontCache:
    """Lazily loads and caches pygame fonts."""
    _cache: dict = {}

    @classmethod
    def get(cls, size: int) -> pygame.font.Font:
        if size not in cls._cache:
            # Try a system font that supports Cyrillic, fall back to default
            font = pygame.font.SysFont("segoeui", size)
            cls._cache[size] = font
        return cls._cache[size]

    @classmethod
    def clear(cls):
        cls._cache.clear()


def draw_text(surface, text, x, y, size=FONT_SIZE_SMALL,
              color=COLOR_TEXT_MAIN, anchor="topleft", shadow=False):
    """Render a single line of text. anchor: topleft / center / topright."""
    font   = FontCache.get(size)
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        sr = sh.get_rect(**{anchor: (x + 1, y + 1)})
        surface.blit(sh, sr)
    surf   = font.render(text, True, color)
    rect   = surf.get_rect(**{anchor: (x, y)})
    surface.blit(surf, rect)
    return rect


def draw_wrapped_text(surface, text, rect, size=FONT_SIZE_SMALL,
                      color=COLOR_TEXT_MAIN, line_spacing=4):
    """Word-wrap text inside a pygame.Rect."""
    font   = FontCache.get(size)
    words  = text.split()
    lines  = []
    line   = ""
    for word in words:
        test = (line + " " + word).strip()
        if font.size(test)[0] <= rect.width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    y = rect.top
    for l in lines:
        surf = font.render(l, True, color)
        surface.blit(surf, (rect.left, y))
        y += surf.get_height() + line_spacing
    return y


class Button:
    """A clickable rectangular button with hover / active states."""

    def __init__(self, rect, label, size=FONT_SIZE_SMALL):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.size    = size
        self.hovered = False
        self.active  = False   # visually "pressed / selected"
        self.enabled = True

    def handle_event(self, event):
        """Returns True on click."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface):
        if not self.enabled:
            bg = COLOR_PANEL
            bc = COLOR_PANEL_BORDER
            tc = COLOR_TEXT_DIM
        elif self.active:
            bg = COLOR_BTN_ACTIVE
            bc = COLOR_TEXT_HIGHLIGHT
            tc = COLOR_TEXT_HIGHLIGHT
        elif self.hovered:
            bg = COLOR_BTN_HOVER
            bc = COLOR_BTN_BORDER
            tc = COLOR_TEXT_MAIN
        else:
            bg = COLOR_BTN_NORMAL
            bc = COLOR_BTN_BORDER
            tc = COLOR_TEXT_DIM

        pygame.draw.rect(surface, bg,  self.rect, border_radius=BTN_CORNER_RADIUS)
        pygame.draw.rect(surface, bc,  self.rect, width=2, border_radius=BTN_CORNER_RADIUS)
        cx = self.rect.centerx
        cy = self.rect.centery
        draw_text(surface, self.label, cx, cy, size=self.size,
                  color=tc, anchor="center")


class Card:
    """A selectable card with title, subtitle and description."""

    def __init__(self, rect, title, subtitle, desc, tag=None):
        self.rect     = pygame.Rect(rect)
        self.title    = title
        self.subtitle = subtitle
        self.desc     = desc
        self.tag      = tag        # arbitrary data attached to this card
        self.selected = False
        self.hovered  = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface):
        border_color = COLOR_CARD_SELECTED if self.selected else (
            COLOR_BTN_BORDER if self.hovered else COLOR_PANEL_BORDER)
        bg_color = (70, 50, 25) if self.selected else (
            (55, 40, 20) if self.hovered else COLOR_PANEL)
        pygame.draw.rect(surface, bg_color,  self.rect, border_radius=CARD_CORNER)
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=CARD_CORNER)

        tx = self.rect.x + CARD_PADDING
        ty = self.rect.y + CARD_PADDING
        draw_text(surface, self.title,    tx, ty,       size=FONT_SIZE_MEDIUM,
                  color=COLOR_TEXT_HIGHLIGHT)
        draw_text(surface, self.subtitle, tx, ty + 26,  size=FONT_SIZE_TINY,
                  color=COLOR_TEXT_DIM)
        wrap_rect = pygame.Rect(tx, ty + 46,
                                self.rect.width - CARD_PADDING * 2,
                                self.rect.height - 56)
        draw_wrapped_text(surface, self.desc, wrap_rect,
                          size=FONT_SIZE_TINY, color=COLOR_TEXT_MAIN)


class Bar:
    """A horizontal progress bar."""

    def __init__(self, rect, label="", lo_color=COLOR_BAR_TEMP_LOW,
                 mid_color=COLOR_BAR_TEMP_MID, hi_color=COLOR_BAR_TEMP_HIGH,
                 show_value=True):
        self.rect       = pygame.Rect(rect)
        self.label      = label
        self.lo_color   = lo_color
        self.mid_color  = mid_color
        self.hi_color   = hi_color
        self.show_value = show_value
        self.value      = 0.0    # 0–1

    def set_value(self, v):
        self.value = max(0.0, min(1.0, v))

    def _lerp3(self, t):
        if t < 0.5:
            r = t * 2
            a, b = self.lo_color, self.mid_color
        else:
            r = (t - 0.5) * 2
            a, b = self.mid_color, self.hi_color
        return tuple(int(a[i] + (b[i] - a[i]) * r) for i in range(3))

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_BAR_BG, self.rect, border_radius=BAR_CORNER)
        fill_w = int(self.rect.width * self.value)
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            color = self._lerp3(self.value)
            pygame.draw.rect(surface, color, fill_rect, border_radius=BAR_CORNER)
        pygame.draw.rect(surface, COLOR_BAR_BORDER, self.rect, width=2, border_radius=BAR_CORNER)

        # Label left, value right
        if self.label:
            draw_text(surface, self.label,
                      self.rect.x + 5, self.rect.centery,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_DIM, anchor="midleft")
        if self.show_value:
            draw_text(surface, f"{int(self.value * 100)}",
                      self.rect.right - 5, self.rect.centery,
                      size=FONT_SIZE_TINY, color=COLOR_TEXT_MAIN, anchor="midright")


class Panel:
    """A simple dark background panel with optional border."""

    def __init__(self, rect, title=""):
        self.rect  = pygame.Rect(rect)
        self.title = title

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_PANEL,        self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=2, border_radius=8)
        if self.title:
            draw_text(surface, self.title,
                      self.rect.centerx, self.rect.y + 10,
                      size=FONT_SIZE_SMALL, color=COLOR_TEXT_DIM, anchor="midtop")


def draw_notification(surface, text, y, color=COLOR_TEXT_MAIN,
                      size=FONT_SIZE_MEDIUM, alpha=255):
    """Centred notification text with shadow."""
    w, h = surface.get_size()
    surf = FontCache.get(size).render(text, True, color)
    surf.set_alpha(alpha)
    r    = surf.get_rect(centerx=w // 2, y=y)
    # shadow
    sh = FontCache.get(size).render(text, True, (0, 0, 0))
    sh.set_alpha(alpha)
    surface.blit(sh, (r.x + 2, r.y + 2))
    surface.blit(surf, r)


# ── Inscryption-style visual effects ─────────────────────────────────────────

def draw_vignette(surface):
    """Рисует тёмную виньетку по краям экрана (Inscryption-стиль).
    Поверхность создаётся один раз и кешируется для производительности."""
    global _vignette_surf
    w, h = surface.get_size()

    if _vignette_surf is None or _vignette_surf.get_size() != (w, h):
        _vignette_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        _vignette_surf.fill((0, 0, 0, 0))

        # Рисуем тёмные углы — несколько концентрических эллипсов от краёв к центру
        cx, cy = w // 2, h // 2
        steps = 32
        for i in range(steps, 0, -1):
            ratio = i / steps
            # Альфа убывает к центру (максимум у краёв)
            alpha = int(200 * (ratio ** 2.2))
            # Прямоугольник чуть больше экрана уменьшается к центру
            margin_x = int(cx * (1.0 - ratio))
            margin_y = int(cy * (1.0 - ratio))
            rect = pygame.Rect(margin_x, margin_y, w - margin_x * 2, h - margin_y * 2)
            pygame.draw.rect(_vignette_surf, (0, 0, 0, alpha), rect, border_radius=max(1, int(60 * ratio)))

    surface.blit(_vignette_surf, (0, 0))


def draw_grain(surface, time_sec, intensity=0.04):
    """Добавляет редкую зернистость плёнки (тёмные пиксели).
    Генерируется раз в 3 кадра для производительности (не более 300 пикселей)."""
    global _grain_surf, _grain_frame
    w, h = surface.get_size()

    _grain_frame += 1

    if _grain_surf is None or _grain_surf.get_size() != (w, h):
        _grain_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        _grain_frame = 0  # force regeneration

    if _grain_frame % 3 == 0:
        _grain_surf.fill((0, 0, 0, 0))
        num_pixels = min(300, int(w * h * intensity * 0.001))
        for _ in range(num_pixels):
            px = random.randint(0, w - 1)
            py = random.randint(0, h - 1)
            darkness = random.randint(60, 140)
            _grain_surf.set_at((px, py), (0, 0, 0, darkness))

    surface.blit(_grain_surf, (0, 0))


def draw_woodcut_border(surface, rect, color=(90, 65, 40)):
    """Рисует «рваную деревянную рамку» вокруг rect — имитация гравюры на дереве.
    Несколько нерегулярных линий с небольшим смещением."""
    rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height

    # Рисуем 3 слоя слегка смещённых линий, имитируя волокна дерева
    for layer in range(3):
        offset = layer * 1
        alpha_mult = 1.0 - layer * 0.25
        col = tuple(max(0, min(255, int(c * alpha_mult))) for c in color)

        # Количество «зазубрин» — маленьких отклонений по каждой стороне
        segs = 8
        # Верхняя сторона
        pts_top = []
        for s in range(segs + 1):
            t = s / segs
            x = rx + int(rw * t)
            jitter = random.randint(-2, 2) if 0 < s < segs else 0
            pts_top.append((x + offset, ry + jitter + offset))
        pygame.draw.lines(surface, col, False, pts_top, 1)

        # Нижняя сторона
        pts_bot = []
        for s in range(segs + 1):
            t = s / segs
            x = rx + int(rw * t)
            jitter = random.randint(-2, 2) if 0 < s < segs else 0
            pts_bot.append((x + offset, ry + rh + jitter + offset))
        pygame.draw.lines(surface, col, False, pts_bot, 1)

        # Левая сторона
        pts_left = []
        for s in range(segs + 1):
            t = s / segs
            y = ry + int(rh * t)
            jitter = random.randint(-2, 2) if 0 < s < segs else 0
            pts_left.append((rx + jitter + offset, y + offset))
        pygame.draw.lines(surface, col, False, pts_left, 1)

        # Правая сторона
        pts_right = []
        for s in range(segs + 1):
            t = s / segs
            y = ry + int(rh * t)
            jitter = random.randint(-2, 2) if 0 < s < segs else 0
            pts_right.append((rx + rw + jitter + offset, y + offset))
        pygame.draw.lines(surface, col, False, pts_right, 1)


def draw_scratchy_text(surface, text, x, y, size, color, anchor="center"):
    """Рисует текст с лёгким смещением тени — имитирует напечатанный на старой машинке.
    Две тени: основная (+2,+1) и дополнительная (+1,0) более тусклая."""
    font = FontCache.get(size)

    # Дополнительная тень (+1, 0) — совсем тусклая
    dim_col = tuple(max(0, int(c * 0.18)) for c in color)
    sh2 = font.render(text, True, dim_col)
    r2 = sh2.get_rect(**{anchor: (x + 1, y)})
    surface.blit(sh2, r2)

    # Основная тень (+2, +1) — тёмная
    sh1 = font.render(text, True, (0, 0, 0))
    r1 = sh1.get_rect(**{anchor: (x + 2, y + 1)})
    surface.blit(sh1, r1)

    # Основной текст
    surf = font.render(text, True, color)
    rect = surf.get_rect(**{anchor: (x, y)})
    surface.blit(surf, rect)
    return rect
