"""
sound_synth.py — Soft, filtered procedural audio generator for Campfire Simulator.
Uses low-pass filtering (brown/pink noise) instead of harsh raw white noise.
"""
import pygame
import math
import random
import struct
import os

SAMPLE_RATE = 22050


def lowpass(samples, alpha=0.15):
    """Простой фильтр нижних частот: убирает резкий цифровой песок и визг, делает звук мягким и глухим."""
    out = []
    prev = 0.0
    for s in samples:
        prev = prev + alpha * (s - prev)
        out.append(prev)
    return out


class SoundEngine:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception as e:
            print(f"SoundEngine: Failed to init mixer: {e}")
            return

        self._cache = {}
        self._init_sounds()
        self._last_crackle_time = 0.0

        # Таймеры для окружения
        self._owl_timer  = random.uniform(20.0, 40.0)
        self._wind_timer = random.uniform(8.0, 15.0)

        # Флаг фонового звука костра
        self._fire_loop_playing = False

    def _pack_mono(self, samples, volume=1.0):
        """Convert list of floats in [-1.0, 1.0] to stereo 16-bit PCM bytes."""
        buf = bytearray()
        for s in samples:
            val = max(-32767, min(32767, int(s * volume * 32767)))
            b = struct.pack('<h', val)
            buf.extend(b)  # L
            buf.extend(b)  # R
        return bytes(buf)

    def _init_sounds(self):
        if not self.enabled:
            return

        # 1. Чирк спички (мягкое шуршание по коробку без писка)
        scratch_len = int(SAMPLE_RATE * 0.11)
        raw = []
        for i in range(scratch_len):
            env = math.sin(math.pi * (i / scratch_len)) ** 0.8
            # Импульсный шорох песчинок
            grain = random.uniform(-1.0, 1.0) if random.random() < 0.6 else 0.0
            raw.append(grain * env)
        samples = lowpass(raw, alpha=0.25)
        self._cache['match_scratch'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.35))

        # 2. Вспышка спички / костра (мягкий тёплый "пых")
        flare_len = int(SAMPLE_RATE * 0.35)
        raw = []
        for i in range(flare_len):
            t = i / flare_len
            env = (t / 0.15) if t < 0.15 else math.exp(-(t - 0.15) * 4.5)
            raw.append(random.uniform(-1.0, 1.0) * env)
        samples = lowpass(lowpass(raw, alpha=0.08), alpha=0.12)
        self._cache['match_light'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.6))

        # 3. Хруст сломанной спички (короткий деревянный щелчок)
        snap_len = int(SAMPLE_RATE * 0.04)
        raw = [random.uniform(-1.0, 1.0) * math.exp(-i / (SAMPLE_RATE * 0.005)) for i in range(snap_len)]
        samples = lowpass(raw, alpha=0.35)
        self._cache['match_break'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.5))

        # 4. Колёсико зажигалки (короткий сухой "чирк" из 3 микро-щелчков)
        spin_len = int(SAMPLE_RATE * 0.06)
        raw = []
        for i in range(spin_len):
            click = 1.0 if (i % 350 < 40) else 0.1
            env = math.exp(-i / (SAMPLE_RATE * 0.025))
            raw.append(random.uniform(-1.0, 1.0) * click * env)
        samples = lowpass(raw, alpha=0.45)
        self._cache['lighter_spin'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.35))

        # 5. Зажигалка: воспламенение газа (очень мягкий глухой пуф)
        whoosh_len = int(SAMPLE_RATE * 0.20)
        raw = []
        for i in range(whoosh_len):
            env = math.sin(math.pi * (i / whoosh_len)) ** 1.5
            raw.append(random.uniform(-1.0, 1.0) * env)
        samples = lowpass(raw, alpha=0.10)
        self._cache['lighter_whoosh'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.4))

        # 6. Кремень и кресало (короткий удар камня без противного ультразвука)
        clink_len = int(SAMPLE_RATE * 0.07)
        raw = []
        for i in range(clink_len):
            t = i / SAMPLE_RATE
            env = math.exp(-i / (SAMPLE_RATE * 0.008))
            tone = math.sin(2 * math.pi * 1650 * t) * 0.4 + math.sin(2 * math.pi * 2400 * t) * 0.2
            noise = random.uniform(-0.5, 0.5) * math.exp(-i / (SAMPLE_RATE * 0.003))
            raw.append((tone + noise) * env)
        samples = lowpass(raw, alpha=0.5)
        self._cache['flint_clink'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.35))

        # 7. Подкидывание дров — более глухой и "тяжёлый" удар
        # Добавлен низкочастотный синус 65 Гц + более длинный env decay
        thud_len = int(SAMPLE_RATE * 0.18)
        raw = []
        for i in range(thud_len):
            t = i / SAMPLE_RATE
            env = math.exp(-i / (SAMPLE_RATE * 0.045))  # более длинный decay
            sine_low  = math.sin(2 * math.pi * 65 * t) * 0.55   # 65 Гц — глухая нота
            sine_body = math.sin(2 * math.pi * 95 * t) * 0.5
            noise = random.uniform(-0.4, 0.4) * 0.3
            raw.append((sine_low + sine_body + noise) * env)
        samples = lowpass(raw, alpha=0.18)
        self._cache['wood_drop'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.6))

        # 8. Ворошение углей (мягкий шорох пепла и угольков)
        poke_len = int(SAMPLE_RATE * 0.18)
        raw = []
        for i in range(poke_len):
            env = math.sin(math.pi * (i / poke_len))
            raw.append(random.uniform(-1.0, 1.0) * env)
        samples = lowpass(raw, alpha=0.15)
        self._cache['poker_poke'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.35))

        # 9. Выдох / дутьё на угли (двойной lowpass — совсем мягкий)
        blow_len = int(SAMPLE_RATE * 0.35)
        raw = []
        for i in range(blow_len):
            env = math.sin(math.pi * (i / blow_len)) ** 1.5
            raw.append(random.uniform(-1.0, 1.0) * env)
        samples = lowpass(lowpass(raw, alpha=0.04), alpha=0.06)  # двойной мягкий фильтр
        self._cache['blow'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.45))

        # 10. Уютное потрескивание костра — 8 вариантов, более разнообразные
        self._crackles = []
        for _ in range(8):
            c_len = int(SAMPLE_RATE * random.uniform(0.015, 0.045))  # шире диапазон
            raw = []
            for i in range(c_len):
                env = math.exp(-i / (SAMPLE_RATE * random.uniform(0.002, 0.006)))
                raw.append(random.uniform(-1.0, 1.0) * env)
            samples = lowpass(raw, alpha=random.uniform(0.20, 0.40))
            vol = random.uniform(0.18, 0.48)
            self._crackles.append(pygame.mixer.Sound(buffer=self._pack_mono(samples, vol)))

        # 11. Фоновый шум костра — длинный (3 секунды), зацикленный
        # Несколько слоёв lowpass filtered noise разных частот (имитирует шум пламени)
        fire_loop_len = int(SAMPLE_RATE * 3.0)
        raw_fire = [0.0] * fire_loop_len

        # Слой 1: широкополосный шум (alpha=0.08) — основной шум горения
        layer1 = [random.uniform(-1.0, 1.0) for _ in range(fire_loop_len)]
        layer1 = lowpass(layer1, alpha=0.08)

        # Слой 2: более узкий шум (alpha=0.04) — низкочастотное гудение
        layer2 = [random.uniform(-1.0, 1.0) for _ in range(fire_loop_len)]
        layer2 = lowpass(layer2, alpha=0.04)

        # Слой 3: очень низкий (alpha=0.025) — глубокое дыхание огня
        layer3 = [random.uniform(-1.0, 1.0) for _ in range(fire_loop_len)]
        layer3 = lowpass(layer3, alpha=0.025)

        # Микшируем слои с разными весами
        for i in range(fire_loop_len):
            raw_fire[i] = layer1[i] * 0.50 + layer2[i] * 0.35 + layer3[i] * 0.25

        # Сглаживаем начало/конец для бесшовного зацикливания
        fade_len = int(SAMPLE_RATE * 0.05)
        for i in range(fade_len):
            t = i / fade_len
            raw_fire[i] *= t
            raw_fire[fire_loop_len - 1 - i] *= t

        self._fire_loop = pygame.mixer.Sound(buffer=self._pack_mono(raw_fire, 0.22))

        # ── Загрузка реальных высококачественных аудиофайлов (если доступны) ──
        base_dir = os.path.dirname(__file__)
        real_fire = os.path.join(base_dir, 'assets', 'sounds', 'campfire_real.ogg')
        if os.path.exists(real_fire):
            try:
                self._fire_loop = pygame.mixer.Sound(real_fire)
            except Exception as e:
                print(f"Failed to load campfire_real.ogg: {e}")

        self._forest_ambience = None
        real_forest = os.path.join(base_dir, 'assets', 'sounds', 'night_forest.ogg')
        if os.path.exists(real_forest):
            try:
                self._forest_ambience = pygame.mixer.Sound(real_forest)
                self._forest_ambience.set_volume(0.28)
                self._forest_ambience.play(-1)
            except Exception as e:
                print(f"Failed to load night_forest.ogg: {e}")

        # 12. Уханье совы (синус 400 Гц + вибрато, медленный env, 1.2 сек)
        owl_len = int(SAMPLE_RATE * 1.2)
        raw = []
        for i in range(owl_len):
            t = i / SAMPLE_RATE
            # Огибающая: медленный нарастание + затухание
            env = math.sin(math.pi * (i / owl_len)) ** 0.5
            # Вибрато: 5 Гц модуляция частоты
            vibrato = math.sin(2 * math.pi * 5.0 * t) * 18.0
            freq = 400.0 + vibrato
            # Нисходящая модуляция тона (сова понижает голос)
            freq *= (1.0 - 0.15 * (i / owl_len))
            tone = math.sin(2 * math.pi * freq * t) * 0.6
            # Небольшой обертон
            tone += math.sin(2 * math.pi * freq * 1.5 * t) * 0.15
            raw.append(tone * env)
        samples = lowpass(raw, alpha=0.35)
        self._cache['owl_hoot'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.5))

        # 13. Шелест листьев (узкополосный шум, 0.8 сек, очень тихий)
        wind_len = int(SAMPLE_RATE * 0.8)
        raw = []
        for i in range(wind_len):
            env = math.sin(math.pi * (i / wind_len)) ** 0.8
            raw.append(random.uniform(-1.0, 1.0) * env)
        # Двойная фильтрация для очень узкой полосы
        samples = lowpass(lowpass(raw, alpha=0.06), alpha=0.09)
        self._cache['wind_rustle'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.28))

    def play(self, sound_name):
        if not self.enabled:
            return
        snd = self._cache.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def play_crackle(self):
        if not self.enabled or not self._crackles:
            return
        try:
            random.choice(self._crackles).play()
        except Exception:
            pass

    def update_fire_audio(self, temp, dt):
        """Обновляет аудио костра: фоновый шум, потрескивание, сова, ветер."""
        if not self.enabled:
            return

        # ── Фоновый зацикленный шум костра ──────────────────────────────────
        if temp > 15:
            if not self._fire_loop_playing:
                try:
                    self._fire_loop.play(-1)  # зацикливаем
                    self._fire_loop_playing = True
                except Exception:
                    pass
            # Громкость пропорциональна температуре (0.0 .. 0.6)
            vol = min(0.6, (temp - 15.0) / 85.0 * 0.6)
            try:
                self._fire_loop.set_volume(vol)
            except Exception:
                pass
        elif temp <= 5:
            if self._fire_loop_playing:
                try:
                    self._fire_loop.stop()
                    self._fire_loop_playing = False
                except Exception:
                    pass

        # ── Потрескивание ────────────────────────────────────────────────────
        if temp < 5:
            return

        self._last_crackle_time += dt
        rate = max(0.18, 1.5 - (temp / 100.0) * 1.2)
        if self._last_crackle_time >= rate:
            self._last_crackle_time = 0.0
            if random.random() < 0.75:
                self.play_crackle()

        # ── Уханье совы — раз в 20-40 секунд (только при слабом/среднем огне) ──
        self._owl_timer -= dt
        if self._owl_timer <= 0:
            self._owl_timer = random.uniform(20.0, 40.0)
            if temp < 60:
                self.play('owl_hoot')

        # ── Шелест листьев — раз в 8-15 секунд ──────────────────────────────
        self._wind_timer -= dt
        if self._wind_timer <= 0:
            self._wind_timer = random.uniform(8.0, 15.0)
            self.play('wind_rustle')


# Global sound instance
sounds = SoundEngine()
