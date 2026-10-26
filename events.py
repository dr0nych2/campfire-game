"""
events.py — Weather event system: wind and rain particles.
All magic numbers are defined as named constants at the top.

Performance note: all particles are batched onto a single pre-allocated surface
per frame instead of creating one surface per particle.
"""
import pygame
import random

# ── Screen dimensions (passed in at runtime, defaults here) ──────────────────
SCREEN_W = 800
SCREEN_H = 600

# ── Weather timing (seconds) ─────────────────────────────────────────────────
WEATHER_CHECK_INTERVAL  = 8.0
WIND_DURATION_MIN       = 5.0
WIND_DURATION_MAX       = 15.0
RAIN_DURATION_MIN       = 8.0
RAIN_DURATION_MAX       = 20.0
CALM_CHANCE             = 0.45

# ── Wind ──────────────────────────────────────────────────────────────────────
WIND_GENTLE_STRENGTH    = 20.0
WIND_STRONG_STRENGTH    = 65.0
WIND_STRONG_THRESHOLD   = 40.0
WIND_PARTICLE_COUNT     = 14          # reduced for performance
WIND_PARTICLE_SPEED_MIN = 4.0
WIND_PARTICLE_SPEED_MAX = 9.0
WIND_PARTICLE_LENGTH    = 24
WIND_PARTICLE_ALPHA     = 140
WIND_PARTICLE_COLOR     = (210, 230, 255)

# ── Rain ──────────────────────────────────────────────────────────────────────
RAIN_PARTICLE_COUNT     = 70          # reduced from 120 for performance
RAIN_SPEED_Y            = 9.0
RAIN_SPEED_X            = -2.0
RAIN_LENGTH             = 14
RAIN_PARTICLE_ALPHA     = 150
RAIN_PARTICLE_COLOR     = (150, 190, 240)
RAIN_TEMP_PENALTY       = 0.25

# ── Effect multipliers ────────────────────────────────────────────────────────
GENTLE_WIND_FIRE_BOOST  = 0.05
STRONG_WIND_FIRE_DRAIN  = 0.20


class WeatherParticle:
    """A single animated streak (rain or wind). No drawing here — batched."""

    __slots__ = ("x", "y", "vx", "vy", "length", "color", "alpha")

    def __init__(self, x, y, vx, vy, length, color, alpha):
        self.x      = x
        self.y      = y
        self.vx     = vx
        self.vy     = vy
        self.length = length
        self.color  = color
        self.alpha  = alpha

    def update(self, w, h):
        self.x += self.vx
        self.y += self.vy
        if self.x > w + self.length:
            self.x = -self.length
        if self.x < -self.length:
            self.x = w + self.length
        if self.y > h + self.length:
            self.y = -self.length


class WeatherSystem:
    """Manages random weather events and their visual particles."""

    CALM        = "calm"
    WIND_GENTLE = "wind_gentle"
    WIND_STRONG = "wind_strong"
    RAIN        = "rain"

    def __init__(self, screen_w=SCREEN_W, screen_h=SCREEN_H):
        self.screen_w        = screen_w
        self.screen_h        = screen_h
        self.event           = self.CALM
        self.event_timer     = 0.0
        self.event_duration  = WEATHER_CHECK_INTERVAL
        self.particles       = []
        self._wind_strength  = 0.0

        # Pre-allocated batch surface — reused every frame (no per-frame alloc)
        self._batch_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

    # ── Public read-only properties ───────────────────────────────────────────

    @property
    def wind_strength(self):
        return self._wind_strength

    @property
    def is_raining(self):
        return self.event == self.RAIN

    @property
    def is_strong_wind(self):
        return self.event == self.WIND_STRONG

    @property
    def is_gentle_wind(self):
        return self.event == self.WIND_GENTLE

    @property
    def temp_modifier(self):
        if self.event == self.RAIN:
            return -RAIN_TEMP_PENALTY
        if self.event == self.WIND_GENTLE:
            return GENTLE_WIND_FIRE_BOOST
        if self.event == self.WIND_STRONG:
            return -STRONG_WIND_FIRE_DRAIN
        return 0.0

    @property
    def label(self):
        labels = {
            self.CALM:        "Тихо",
            self.WIND_GENTLE: "Лёгкий ветер",
            self.WIND_STRONG: "Сильный ветер!",
            self.RAIN:        "Дождь!",
        }
        return labels.get(self.event, "")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _roll_event(self):
        roll = random.random()
        if roll < CALM_CHANCE:
            return self.CALM
        roll -= CALM_CHANCE
        remaining = 1.0 - CALM_CHANCE
        if roll < remaining * 0.35:
            return self.WIND_GENTLE
        if roll < remaining * 0.65:
            return self.WIND_STRONG
        return self.RAIN

    def _build_wind_particles(self, count):
        self.particles = []
        for _ in range(count):
            x   = random.uniform(0, self.screen_w)
            y   = random.uniform(0, self.screen_h)
            spd = random.uniform(WIND_PARTICLE_SPEED_MIN, WIND_PARTICLE_SPEED_MAX)
            vx  = spd if self._wind_strength > 0 else -spd
            vy  = random.uniform(-0.5, 0.5)
            a   = random.randint(80, WIND_PARTICLE_ALPHA)
            self.particles.append(
                WeatherParticle(x, y, vx, vy, WIND_PARTICLE_LENGTH,
                                WIND_PARTICLE_COLOR, a))

    def _build_rain_particles(self, count):
        self.particles = []
        for _ in range(count):
            x = random.uniform(0, self.screen_w)
            y = random.uniform(-self.screen_h, self.screen_h)
            self.particles.append(
                WeatherParticle(x, y, RAIN_SPEED_X, RAIN_SPEED_Y,
                                RAIN_LENGTH, RAIN_PARTICLE_COLOR,
                                random.randint(100, RAIN_PARTICLE_ALPHA)))

    def _start_event(self, event):
        self.event = event
        if event == self.CALM:
            self.event_duration = WEATHER_CHECK_INTERVAL
            self._wind_strength = 0.0
            self.particles = []
        elif event == self.WIND_GENTLE:
            self._wind_strength = random.uniform(WIND_GENTLE_STRENGTH * 0.5,
                                                 WIND_GENTLE_STRENGTH)
            self.event_duration = random.uniform(WIND_DURATION_MIN, WIND_DURATION_MAX)
            self._build_wind_particles(WIND_PARTICLE_COUNT)
        elif event == self.WIND_STRONG:
            self._wind_strength = random.uniform(WIND_STRONG_THRESHOLD,
                                                 WIND_STRONG_STRENGTH)
            self.event_duration = random.uniform(WIND_DURATION_MIN, WIND_DURATION_MAX)
            self._build_wind_particles(WIND_PARTICLE_COUNT * 2)
        elif event == self.RAIN:
            self._wind_strength = random.uniform(-15, 15)
            self.event_duration = random.uniform(RAIN_DURATION_MIN, RAIN_DURATION_MAX)
            self._build_rain_particles(RAIN_PARTICLE_COUNT)

    # ── Public methods ────────────────────────────────────────────────────────

    def update(self, dt):
        self.event_timer += dt
        if self.event_timer >= self.event_duration:
            self.event_timer = 0.0
            self._start_event(self._roll_event())
        for p in self.particles:
            p.update(self.screen_w, self.screen_h)

    def draw(self, surface):
        """Batch-draw all particles onto a single pre-allocated surface."""
        if not self.particles:
            return
        # Clear the reusable surface (fill with transparent black)
        self._batch_surf.fill((0, 0, 0, 0))
        for p in self.particles:
            end_x = int(p.x - p.vx * 3)
            end_y = int(p.y - p.vy * 3)
            pygame.draw.line(self._batch_surf,
                             (p.color[0], p.color[1], p.color[2], p.alpha),
                             (int(p.x), int(p.y)),
                             (end_x, end_y), 2)
        surface.blit(self._batch_surf, (0, 0))

    def force_calm(self):
        self._start_event(self.CALM)
        self.event_timer = 0.0

    def get_ignition_modifier(self):
        if self.event == self.RAIN:
            return 0.3
        if self.event == self.WIND_STRONG:
            return 0.6
        if self.event == self.WIND_GENTLE:
            return 1.1
        return 1.0
