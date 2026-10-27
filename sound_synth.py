"""
sound_synth.py — Soft, filtered procedural audio generator for Campfire Simulator.
Uses low-pass filtering (brown/pink noise) instead of harsh raw white noise.
"""
import pygame
import math
import random
import struct

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

        # 7. Подкидывание дров (глухой деревянный стук)
        thud_len = int(SAMPLE_RATE * 0.12)
        raw = []
        for i in range(thud_len):
            t = i / SAMPLE_RATE
            env = math.exp(-i / (SAMPLE_RATE * 0.02))
            sine = math.sin(2 * math.pi * 95 * t) * 0.8
            noise = random.uniform(-0.4, 0.4) * 0.3
            raw.append((sine + noise) * env)
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

        # 9. Выдох / дутьё на угли (очень мягкий тёплый воздух)
        blow_len = int(SAMPLE_RATE * 0.35)
        raw = []
        for i in range(blow_len):
            env = math.sin(math.pi * (i / blow_len)) ** 1.5
            raw.append(random.uniform(-1.0, 1.0) * env)
        samples = lowpass(lowpass(raw, alpha=0.06), alpha=0.08)
        self._cache['blow'] = pygame.mixer.Sound(buffer=self._pack_mono(samples, 0.45))

        # 10. Уютное потрескивание костра (короткие мягкие деревянные щелчки без синусоид!)
        self._crackles = []
        for _ in range(6):
            c_len = int(SAMPLE_RATE * random.uniform(0.008, 0.022))
            raw = []
            for i in range(c_len):
                env = math.exp(-i / (SAMPLE_RATE * 0.003))
                raw.append(random.uniform(-1.0, 1.0) * env)
            samples = lowpass(raw, alpha=random.uniform(0.20, 0.40))
            vol = random.uniform(0.20, 0.45)
            self._crackles.append(pygame.mixer.Sound(buffer=self._pack_mono(samples, vol)))

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
        """Plays soft fire crackle pops based on temperature."""
        if not self.enabled or temp < 5:
            return

        self._last_crackle_time += dt
        rate = max(0.18, 1.5 - (temp / 100.0) * 1.2)
        if self._last_crackle_time >= rate:
            self._last_crackle_time = 0.0
            if random.random() < 0.75:
                self.play_crackle()


# Global sound instance
sounds = SoundEngine()