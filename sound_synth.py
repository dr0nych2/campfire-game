"""
sound_synth.py — 100% Authentic Acoustic Audio Engine for Campfire Simulator.
All sounds are real, recorded studio foley and field audio files.
ZERO procedural sine waves or synthetic digital noise.
"""
import pygame
import os
import random

SAMPLE_RATE = 44100
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), 'assets', 'sounds')


class SoundEngine:
    def __init__(self):
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=1024)
            self.enabled = True
        except Exception as e:
            print(f"SoundEngine: Failed to init mixer: {e}")
            return

        self._cache = {}
        self._crackles = []
        self._fire_loop = None
        self._forest_ambience = None
        self._fire_loop_playing = False
        self._last_crackle_time = 0.0
        self._ambient_timer = random.uniform(15.0, 30.0)

        self._load_all_real_sounds()

    def _load_all_real_sounds(self):
        if not self.enabled or not os.path.isdir(SOUNDS_DIR):
            return

        # 1. Load all available audio files into cache
        for fname in os.listdir(SOUNDS_DIR):
            ext = os.path.splitext(fname)[1].lower()
            if ext in ('.wav', '.ogg', '.mp3'):
                sname = os.path.splitext(fname)[0]
                fpath = os.path.join(SOUNDS_DIR, fname)
                try:
                    snd = pygame.mixer.Sound(fpath)
                    self._cache[sname] = snd
                    if sname.startswith('crackle_'):
                        self._crackles.append(snd)
                except Exception as e:
                    print(f"Could not load {fname}: {e}")

        # 2. Wire logical game sound keys to authentic recordings
        # Match
        if 'match_scratch' in self._cache:
            self._cache['match_scratch'].set_volume(0.85)
        if 'match_light' in self._cache:
            self._cache['match_light'].set_volume(0.80)
        if 'match_break' in self._cache:
            self._cache['match_break'].set_volume(0.75)

        # Lighter
        if 'lighter_real' in self._cache:
            self._cache['lighter_spin'] = self._cache['lighter_real']
            self._cache['lighter_whoosh'] = self._cache['lighter_real']
            self._cache['lighter_real'].set_volume(0.80)

        # Flint & Steel
        if 'flint_strike' in self._cache:
            self._cache['flint_clink'] = self._cache['flint_strike']
            self._cache['flint_strike'].set_volume(0.90)

        # Wood & Poker
        if 'wood_drop' in self._cache:
            self._cache['wood_drop'].set_volume(0.70)
        if 'sticks_handle' in self._cache:
            self._cache['sticks'] = self._cache['sticks_handle']
            self._cache['sticks_handle'].set_volume(0.65)
        if 'poker_poke' in self._cache:
            self._cache['poker_poke'].set_volume(0.60)
        if 'paper_rustle' in self._cache:
            self._cache['paper'] = self._cache['paper_rustle']
            self._cache['paper_rustle'].set_volume(0.70)
        if 'bag_rustle' in self._cache:
            self._cache['marshmallow'] = self._cache['bag_rustle']
            self._cache['bag_rustle'].set_volume(0.70)

        # Breath & Steam
        if 'blow' in self._cache:
            self._cache['blow'].set_volume(0.70)
        if 'steam_hiss' in self._cache:
            self._cache['steam_hiss'].set_volume(0.55)
        if 'wind_rustle' in self._cache:
            self._cache['wind_rustle'].set_volume(0.35)

        # Main Real Campfire Ambient Loop (60 seconds)
        if 'campfire_real' in self._cache:
            self._fire_loop = self._cache['campfire_real']
            self._fire_loop.set_volume(0.0)

    def play(self, sound_name):
        """Play a real one-shot acoustic sound by key."""
        if not self.enabled:
            return
        snd = self._cache.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def play_crackle(self):
        """Play a real recorded campfire snap/pop."""
        if not self.enabled or not self._crackles:
            return
        try:
            snd = random.choice(self._crackles)
            snd.set_volume(random.uniform(0.35, 0.75))
            snd.play()
        except Exception:
            pass

    def update_fire_audio(self, temp, dt):
        """Dynamic volume scaling for real fire loop and natural pops based on fire heat."""
        if not self.enabled:
            return

        # ── Real Campfire Audio Loop ─────────────────────────────────────────
        if self._fire_loop:
            if temp > 10:
                if not self._fire_loop_playing:
                    try:
                        self._fire_loop.play(-1)
                        self._fire_loop_playing = True
                    except Exception:
                        pass
                # Smooth volume scaling from 0.05 to 0.75 based on temperature
                target_vol = min(0.75, max(0.08, (temp - 10.0) / 90.0 * 0.70))
                try:
                    self._fire_loop.set_volume(target_vol)
                except Exception:
                    pass
            elif temp <= 5:
                if self._fire_loop_playing:
                    try:
                        self._fire_loop.stop()
                        self._fire_loop_playing = False
                    except Exception:
                        pass

        # ── Real Crackle Pops ─────────────────────────────────────────────────
        if temp < 10:
            return

        self._last_crackle_time += dt
        rate = max(0.25, 2.0 - (temp / 100.0) * 1.6)
        if self._last_crackle_time >= rate:
            self._last_crackle_time = 0.0
            if random.random() < 0.80:
                self.play_crackle()

        # Natural soft wind rustle in the trees
        self._ambient_timer -= dt
        if self._ambient_timer <= 0:
            self._ambient_timer = random.uniform(16.0, 32.0)
            self.play('wind_rustle')


# Global sound engine instance
sounds = SoundEngine()
