"""
sound_synth.py — Procedural audio generator for Campfire Simulator.
Generates sound effects and ambient noise directly using math and pygame.mixer.
Zero external assets needed.
"""
import pygame
import math
import random
import struct

SAMPLE_RATE = 22050

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

    def _pack_mono(self, samples):
        """Convert list of floats in [-1.0, 1.0] to stereo 16-bit PCM bytes."""
        buf = bytearray()
        for s in samples:
            val = max(-32767, min(32767, int(s * 32767)))
            b = struct.pack('<h', val)
            buf.extend(b) # L
            buf.extend(b) # R
        return bytes(buf)

    def _init_sounds(self):
        if not self.enabled:
            return

        # 1. Match scratch (friction sound)
        scratch_len = int(SAMPLE_RATE * 0.12)
        samples = []
        for i in range(scratch_len):
            env = math.sin(math.pi * (i / scratch_len))
            noise = random.uniform(-1.0, 1.0) * 0.7
            sine = math.sin(2 * math.pi * 750 * (i / SAMPLE_RATE)) * 0.3
            samples.append((noise + sine) * env * 0.6)
        self._cache['match_scratch'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 2. Match light / sulfur whoosh
        flare_len = int(SAMPLE_RATE * 0.35)
        samples = []
        for i in range(flare_len):
            env = math.sin(math.pi * (i / flare_len)) ** 1.5
            noise = random.uniform(-1.0, 1.0) * 0.6
            sub = math.sin(2 * math.pi * 180 * (i / SAMPLE_RATE)) * 0.4
            samples.append((noise + sub) * env * 0.7)
        self._cache['match_light'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 3. Match break snap
        snap_len = int(SAMPLE_RATE * 0.08)
        samples = []
        for i in range(snap_len):
            env = math.exp(-i / (SAMPLE_RATE * 0.015))
            noise = random.uniform(-1.0, 1.0)
            samples.append(noise * env * 0.8)
        self._cache['match_break'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 4. Lighter flint spin (ratchet click)
        spin_len = int(SAMPLE_RATE * 0.09)
        samples = []
        for i in range(spin_len):
            t = i / SAMPLE_RATE
            # periodic clicks
            pulse = (math.sin(2 * math.pi * 3200 * t) > 0.6) * 0.7
            noise = random.uniform(-0.3, 0.3)
            env = math.exp(-i / (SAMPLE_RATE * 0.04))
            samples.append((pulse + noise) * env * 0.6)
        self._cache['lighter_spin'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 5. Lighter flame whoosh
        whoosh_len = int(SAMPLE_RATE * 0.25)
        samples = []
        for i in range(whoosh_len):
            env = math.sin(math.pi * (i / whoosh_len))
            noise = random.uniform(-1.0, 1.0) * 0.8
            samples.append(noise * env * 0.4)
        self._cache['lighter_whoosh'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 6. Flint clink (metallic spark strike)
        clink_len = int(SAMPLE_RATE * 0.15)
        samples = []
        for i in range(clink_len):
            t = i / SAMPLE_RATE
            env = math.exp(-i / (SAMPLE_RATE * 0.025))
            metal = math.sin(2 * math.pi * 2800 * t) * 0.5 + math.sin(2 * math.pi * 4200 * t) * 0.3
            noise = random.uniform(-0.4, 0.4)
            samples.append((metal + noise) * env * 0.7)
        self._cache['flint_clink'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 7. Wood / item placed
        thud_len = int(SAMPLE_RATE * 0.18)
        samples = []
        for i in range(thud_len):
            t = i / SAMPLE_RATE
            env = math.exp(-i / (SAMPLE_RATE * 0.035))
            sine = math.sin(2 * math.pi * 120 * t) * 0.7
            noise = random.uniform(-0.3, 0.3) * 0.3
            samples.append((sine + noise) * env * 0.8)
        self._cache['wood_drop'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 8. Poker poke / coal shuffle
        poke_len = int(SAMPLE_RATE * 0.20)
        samples = []
        for i in range(poke_len):
            t = i / SAMPLE_RATE
            env = math.sin(math.pi * (i / poke_len))
            noise = random.uniform(-0.6, 0.6)
            crunch = (random.random() < 0.04) * random.uniform(0.6, 1.0)
            samples.append((noise * 0.5 + crunch) * env * 0.5)
        self._cache['poker_poke'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 9. Breath blow
        blow_len = int(SAMPLE_RATE * 0.4)
        samples = []
        for i in range(blow_len):
            env = math.sin(math.pi * (i / blow_len)) ** 1.3
            noise = random.uniform(-0.7, 0.7)
            sub = math.sin(2 * math.pi * 130 * (i / SAMPLE_RATE)) * 0.2
            samples.append((noise + sub) * env * 0.35)
        self._cache['blow'] = pygame.mixer.Sound(buffer=self._pack_mono(samples))

        # 10. Fire crackle clicks (a set of 4 micro-pops)
        self._crackles = []
        for _ in range(4):
            c_len = int(SAMPLE_RATE * random.uniform(0.015, 0.04))
            samps = []
            freq = random.uniform(1200, 3400)
            for i in range(c_len):
                env = math.exp(-i / (SAMPLE_RATE * 0.007))
                wave = math.sin(2 * math.pi * freq * (i / SAMPLE_RATE))
                noise = random.uniform(-0.5, 0.5)
                samps.append((wave * 0.7 + noise * 0.3) * env * random.uniform(0.4, 0.75))
            self._crackles.append(pygame.mixer.Sound(buffer=self._pack_mono(samps)))

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
        """Plays fire crackle pops based on temperature."""
        if not self.enabled or temp < 5:
            return

        self._last_crackle_time += dt
        # Higher temperature -> more frequent crackles
        rate = max(0.12, 1.8 - (temp / 100.0) * 1.5)
        if self._last_crackle_time >= rate:
            self._last_crackle_time = 0.0
            if random.random() < 0.85:
                self.play_crackle()

# Global sound instance
sounds = SoundEngine()
