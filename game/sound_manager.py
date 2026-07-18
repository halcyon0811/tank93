"""
Tank 90 Enhanced - Battle City Authentic Sound Manager
Uses 11 original NES Battle City SFX from feichao93/battle-city (CC0 NES rip):
- bullet_shot.ogg = fire (weapon)
- bullet_hit_1/2.ogg = brick/steel hit
- explosion_1/2.ogg = explosion (tank death)
- powerup_appear/pick.ogg = powerup spawn/pick
- stage_start.ogg = stage intro jingle (35 maps)
- game_over.ogg = game over BGM
- statistics_1.ogg = stage clear scoring
- pause.ogg = pause jingle

Plus authentic intro music from user downloaded:
- "Battle City _ Tank 1990 NES _ Intro _ Live _ 8bit - id deegee (D.G.).m4a"
  renamed to battle_city_intro_final.wav / intro.m4a (5.59 sec authentic NES intro live 8bit)
  Played on new game start for first stage (Stage 1/35) – true retro NES tribute.

Battle City NES original had NO background music during battle (only SFX for tank move treads),
so silly battle BGM loop removed – authentic NES had only intro jingle + SFX.

All 35 maps share same authentic NES audio set.

Source: https://github.com/feichao93/battle-city/tree/master/sound (11 OGGs) + user downloaded intro m4a.
Tile UI matching downloaded_maps 35-stage maps (red brick, white steel blue water green forest gray ice etc).
"""

import pygame
import os
import pathlib
import random
import math

# Pygame mixer sounds
SOUND_DIR = pathlib.Path(__file__).parent / "assets" / "sounds"

# NES Battle City authentic sound list + real tank sounds from freesound community
# Authentic + user intro - intro m4a is real Battle City Tank 1990 NES Intro 8bit Live by deegee (D.G.)
# We prioritize wav for compatibility (intro.m4a converted to battle_city_intro_final.wav 5.59 sec)
# NEW: Real distant tank shots from freesound_community-distant-tank-shots-33735.mp3 (17.6s, 7 shots)
# Extracted to real/ folder: tank_shot_single.wav, tank_shot_power.wav, brick_hit_real.wav, tank_shot_close.wav
AUTHENTIC_SOUNDS = {
    'shoot': 'bullet_shot.ogg',          # weapon fire SFX (tank fire) - will be overridden by real
    'hit_brick': 'bullet_hit_1.ogg',     # brick break / hit (tile destroy) - will be overridden by real
    'hit_steel': 'bullet_hit_2.ogg',     # steel clang - will be overridden by real
    'explosion': 'explosion_1.ogg',      # explosion (tank death)
    'explosion_big': 'explosion_2.ogg',  # base / big explosion
    'powerup_appear': 'powerup_appear.ogg',
    'powerup_pick': 'powerup_pick.ogg',
    'stage_start': 'stage_start.ogg',    # 35 stages start jingle (short)
    'game_over': 'game_over.ogg',        # game over BGM
    'stage_clear': 'statistics_1.ogg',   # stage clear BGM
    'pause': 'pause.ogg',
    # User downloaded authentic intro - real Battle City Tank 1990 NES Intro Live 8bit by deegee
    'battle_intro': 'battle_city_intro_final.wav',  # 5.59 sec authentic intro, used for new game start
    'battle_intro_m4a': 'intro.m4a',      # backup original m4a
    'battle_intro_wav_classic': 'battle_city_intro_classic.wav',
    # Real tank sounds from freesound community (distant tank shots) - user provided
    'real_distant': 'distant_tank_shots.mp3',  # original 17.6s file with 7 shots
    'real_tank_single': 'real/tank_shot_single.wav',  # 0.8s single shot - for normal attack
    'real_tank_power': 'real/tank_shot_power.wav',    # 1.0s power shot - for power level
    'real_tank_close': 'real/tank_shot_close.wav',    # 0.7s close shot
    'real_brick': 'real/brick_hit_real.wav',          # 0.6s brick hit - for brick destruction
}

class SoundManager:
    def __init__(self):
        self.enabled = True
        self.music_enabled = True
        self.sounds = {}  # name -> pygame Sound
        self.bg_music_playing = False
        self.muted = False
        self.volume = 0.7
        self.brick_break_count = 0

        # Retro fallback sounds (generated)
        self.use_authentic = True

        # Tank move looping
        self.move_channel = None
        self.move_sound = None
        self.move_timer = 0

        # Explosion pool
        self.explosion_sounds = []

        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            # Load authentic NES sounds
            self.load_sounds()
            # Generate additional retro sounds
            self.generate_retro_sounds()
            print(f"[Sound] Loaded {len(self.sounds)} authentic NES sounds (35-stage pack) from {SOUND_DIR}")
            print(f"[Sound] Maps: {list(self.sounds.keys())}")
        except Exception as e:
            print(f"[Sound] Mixer init failed, using silent mode (no sounds): {e}")
            self.enabled = False

        # Music
        self.current_bgm = None
        # For loop BGM (simple 8-bit loop background we generate)

    def load_sounds(self):
        if not SOUND_DIR.exists():
            print(f"[Sound] Sound dir missing {SOUND_DIR}, using procedural fallback")
            self.use_authentic = False
            return

        for name, filename in AUTHENTIC_SOUNDS.items():
            path = SOUND_DIR / filename
            if path.exists():
                try:
                    snd = pygame.mixer.Sound(str(path))
                    self.sounds[name] = snd
                    # Lower volume a bit for not too loud
                    snd.set_volume(0.7 if 'explosion' not in name else 0.8)
                except Exception as e:
                    print(f"[Sound] Failed to load {path}: {e}")
            else:
                print(f"[Sound] Missing {path}, will generate fallback")

        # For convenience aliases
        if 'shoot' not in self.sounds:
            print("[Sound] Warning: Missing authentic bullet_shot, generating")
        if 'hit_brick' in self.sounds:
            self.sounds['hit_enemy'] = self.sounds['hit_brick']
        if 'explosion' in self.sounds:
            self.explosion_sounds = [self.sounds['explosion']]
            if 'explosion_big' in self.sounds:
                self.explosion_sounds.append(self.sounds['explosion_big'])

    def generate_retro_sounds(self):
        """Generate 8-bit retro fallback sounds that sound like NES Battle City, using pygame sound synthesis."""
        try:
            # Tank move loop - low engine hum
            self.move_sound = self.generate_tone(frequency=80, duration=0.3, volume=0.15, waveform='saw', noise=True)
            if self.move_sound:
                self.sounds['move_loop'] = self.move_sound

            # Brick break - cracking noise
            crack = self.generate_noise_burst(duration=0.3, low=200, high=1200, volume=0.6)
            if crack:
                self.sounds['brick_break'] = crack

            # Steel clang - high metallic
            clang = self.generate_tone(frequency=600, duration=0.2, volume=0.5, waveform='square', decay=True)
            if clang and 'hit_steel' not in self.sounds:
                self.sounds['hit_steel'] = clang

            # Powerup spawn additional
            if 'powerup_appear' not in self.sounds:
                pu = self.generate_arpeggio([400, 600, 800, 1000], duration=0.6)
                if pu:
                    self.sounds['powerup_appear'] = pu

            # Spawn sound
            spawn = self.generate_arpeggio([200, 400, 600, 800], duration=0.5, volume=0.5)
            if spawn:
                self.sounds['spawn'] = spawn

            # Background battle city theme - simple 8-bit melody loop
            bgm = self.generate_bgm_loop()
            if bgm:
                self.sounds['bgm_battle'] = bgm

            # === NEW: Better shooting sounds - punchy, modern, satisfying ===
            # Generate multiple shooting variants and replace the default 'shoot' with better one
            print("[Sound] Generating better shooting sounds (punchy, modern, realistic tank)...")

            # First, keep authentic as backup
            if 'shoot' in self.sounds:
                self.sounds['shoot_authentic_nes'] = self.sounds['shoot']

            # Punchy retro - improved over authentic
            better_shoot = self.generate_punchy_shoot(f0=1200, f1=180, duration=0.18, volume=0.85, punch_freq=90, punch_vol=0.9)
            if better_shoot:
                self.sounds['shoot_punchy'] = better_shoot
                # Use punchy as intermediate
                self.sounds['shoot'] = better_shoot
                print("[Sound] -> Upgraded 'shoot' to punchy version (1200->180Hz sweep + 90Hz punch)")

            # REALISTIC TANK CANNON - close to real life, deep boom + crack + reverb
            # This is what user asked for: "close real life tank shooting sound"
            real_cannon = self.generate_real_tank_cannon(volume=0.92)
            if real_cannon:
                self.sounds['shoot_real'] = real_cannon
                self.sounds['shoot_realistic'] = real_cannon
                self.sounds['shoot_tank_real'] = real_cannon
                # Make realistic the DEFAULT for shooting (most satisfying, close to real tank)
                self.sounds['shoot'] = real_cannon
                print("[Sound] -> Upgraded 'shoot' to REALISTIC TANK CANNON (40-55Hz boom + 120Hz body + blast)")

            # Power shoot (for power level 2, can break steel) - even more beefy real
            power_shoot = self.generate_punchy_shoot(f0=900, f1=120, duration=0.22, volume=0.95, punch_freq=70, punch_vol=1.0, add_second_layer=True)
            real_power = self.generate_real_tank_cannon(volume=1.0)
            if power_shoot:
                self.sounds['shoot_power'] = power_shoot
                self.sounds['shoot_strong'] = power_shoot
            if real_power:
                self.sounds['shoot_power_real'] = real_power
                # Use real power as power shoot
                self.sounds['shoot_power'] = real_power
                self.sounds['shoot_strong'] = real_power

            # Rapid fire - very short, snappy
            rapid_shoot = self.generate_punchy_shoot(f0=1500, f1=500, duration=0.08, volume=0.65, punch_freq=120, punch_vol=0.6, short=True)
            if rapid_shoot:
                self.sounds['shoot_rapid'] = rapid_shoot
                self.sounds['shoot_rapid_3x'] = rapid_shoot

            # Spread shot - chord-like, 8 directions
            spread_shoot = self.generate_spread_shoot()
            if spread_shoot:
                self.sounds['shoot_spread'] = spread_shoot
                self.sounds['shoot_8way'] = spread_shoot

            # Homing missile - rising pitch with tail
            homing_shoot = self.generate_homing_shoot()
            if homing_shoot:
                self.sounds['shoot_homing'] = homing_shoot
                self.sounds['shoot_missile'] = homing_shoot
                self.sounds['shoot_tracker'] = homing_shoot

            # Laser / plasma for variety
            plasma = self.generate_plasma_shoot()
            if plasma:
                self.sounds['shoot_plasma'] = plasma
                self.sounds['shoot_laser'] = plasma

            # === REALISTIC BRICK AND STEEL HITS ===
            print("[Sound] Generating realistic brick/steel hit sounds (close to real tank vs brick)...")
            real_brick = self.generate_real_brick_hit(volume=0.85)
            if real_brick:
                if 'hit_brick' in self.sounds:
                    self.sounds['hit_brick_authentic'] = self.sounds['hit_brick']
                self.sounds['hit_brick'] = real_brick
                self.sounds['hit_brick_real'] = real_brick
                self.sounds['brick_real'] = real_brick
                print("[Sound] -> Upgraded 'hit_brick' to realistic concrete crack + debris")

            real_steel = self.generate_real_steel_hit(volume=0.9)
            if real_steel:
                if 'hit_steel' in self.sounds:
                    self.sounds['hit_steel_authentic'] = self.sounds['hit_steel']
                self.sounds['hit_steel'] = real_steel
                self.sounds['hit_steel_real'] = real_steel
                self.sounds['steel_real'] = real_steel
                print("[Sound] -> Upgraded 'hit_steel' to realistic clang + ricochet whine")

            # === USE REAL RECORDED DISTANT TANK SHOTS FROM USER PROVIDED FILE ===
            # User: /Users/lida/Downloads/freesound_community-distant-tank-shots-33735.mp3 for tank attack and hitting bricks
            # This file was copied to game/assets/sounds/distant_tank_shots.mp3 and extracted to real/ folder
            print("[Sound] Applying user-provided real distant tank shots for attack and brick hit...")
            if 'real_tank_single' in self.sounds:
                # Backup current shoot as synthetic
                if 'shoot' in self.sounds and 'shoot_synthetic_real' not in self.sounds:
                    self.sounds['shoot_synthetic_real'] = self.sounds['shoot']
                self.sounds['shoot'] = self.sounds['real_tank_single']
                self.sounds['shoot_real_recorded'] = self.sounds['real_tank_single']
                print("[Sound] -> FINAL 'shoot' now uses REAL recorded distant tank shot (single) from freesound_community-distant-tank-shots-33735.mp3")
                print("[Sound]    File: game/assets/sounds/real/tank_shot_single.wav (0.8s extracted from 17.6s)")
            if 'real_tank_power' in self.sounds:
                self.sounds['shoot_power'] = self.sounds['real_tank_power']
                self.sounds['shoot_strong'] = self.sounds['real_tank_power']
                self.sounds['shoot_power_real_recorded'] = self.sounds['real_tank_power']
                print("[Sound] -> 'shoot_power' now uses REAL power shot (1.0s)")

            # For brick hitting: user wants real tank sound for attack, but brick hit should be realistic brick breaking
            # Previously we overrode hit_brick with real_brick which is actually tank shot, not brick - that was wrong
            # Now keep hit_brick as improved synthetic realistic (concrete crack + debris + thud) for close-to-real brick
            # And keep real recorded as alternative, plus create hybrid: tank shot low-end + brick crack high-end
            if 'real_brick' in self.sounds:
                # Keep synthetic improved as primary for brick (more correct)
                # Save real recorded as alternative
                self.sounds['hit_brick_real_recorded'] = self.sounds['real_brick']
                self.sounds['brick_real_recorded'] = self.sounds['real_brick']
                print("[Sound] Real brick recorded kept as 'hit_brick_real_recorded' (0.6s tank shot)")

            # Create hybrid brick hit: Real tank shot low-end (boom) + synthetic brick crack high-end (debris)
            # This makes hitting brick sound like tank shell hitting brick wall - both explosion and brick shattering
            try:
                if 'real_tank_single' in self.sounds and 'hit_brick' in self.sounds:
                    import numpy as np
                    # Get arrays from sounds
                    # real_tank_single is 0.8s, hit_brick synthetic is 0.65s improved
                    # Mix them: low frequencies from tank shot, high from brick crack
                    # For simplicity, we will generate a new hybrid via method
                    hybrid = self.generate_brick_hit_hybrid()
                    if hybrid:
                        # Keep previous hit_brick as backup
                        if 'hit_brick' in self.sounds:
                            self.sounds['hit_brick_synthetic_improved'] = self.sounds['hit_brick']
                        self.sounds['hit_brick'] = hybrid
                        self.sounds['hit_brick_hybrid_real'] = hybrid
                        print("[Sound] -> 'hit_brick' now uses HYBRID: real tank low boom + synthetic brick crack (improved)")
            except Exception as e:
                print(f"[Sound] Hybrid brick gen failed: {e}")

            # Also set distant original as alternative for variety
            if 'real_distant' in self.sounds:
                self.sounds['shoot_distant_original'] = self.sounds['real_distant']
                print("[Sound] Original 17.6s distant shots kept as 'shoot_distant_original'")

            # Ensure shoot still uses real recorded as user requested for attack
            # (already set above to real_tank_single)

        except Exception as e:
            print(f"[Sound] Retro generation failed: {e}")
            import traceback
            traceback.print_exc()

    def generate_tone(self, frequency=440, duration=0.5, volume=0.5, waveform='sine', decay=False, noise=False):
        """Generate a simple tone as pygame Sound (8-bit style)."""
        try:
            import numpy as np
            sr = 22050
            t = np.linspace(0, duration, int(sr*duration), False)

            if waveform == 'sine':
                wave = np.sin(frequency * 2 * np.pi * t)
            elif waveform == 'square':
                wave = np.sign(np.sin(frequency * 2 * np.pi * t))
            elif waveform == 'saw':
                wave = 2 * (t * frequency - np.floor(t * frequency + 0.5))
            elif waveform == 'triangle':
                wave = 2 * np.abs(2 * (t * frequency - np.floor(t * frequency + 0.5))) - 1
            else:
                wave = np.sin(frequency * 2 * np.pi * t)

            if noise:
                # add some noise for engine rumble
                wave += np.random.uniform(-0.3, 0.3, len(t)) * 0.5

            if decay:
                # exponential decay for explosion-like
                env = np.exp(-3 * t)
                wave = wave * env

            # 16-bit
            audio = (wave * 32767 * volume).astype(np.int16)
            # stereo
            stereo = np.column_stack([audio, audio])

            sound = pygame.sndarray.make_sound(stereo)
            return sound
        except ImportError:
            # No numpy, try with pygame.mixer.Sound buffer without numpy? We'll skip
            return None
        except Exception as e:
            print(f"gen tone failed {e}")
            return None

    def generate_noise_burst(self, duration=0.3, low=100, high=2000, volume=0.5):
        try:
            import numpy as np
            sr = 22050
            t = np.linspace(0, duration, int(sr*duration), False)
            noise = np.random.uniform(-1, 1, len(t))
            # filter? simple lowpass via moving average
            # envelope decay
            env = np.exp(-4 * t) * (1 - t/duration)
            wave = noise * env
            audio = (wave * 32767 * volume).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except:
            return None

    def generate_arpeggio(self, freqs, duration=0.6, volume=0.5):
        try:
            import numpy as np
            sr = 22050
            total = np.array([], dtype=np.float32)
            for freq in freqs:
                d = duration / len(freqs)
                t = np.linspace(0, d, int(sr*d), False)
                wave = np.sin(freq * 2 * np.pi * t) * np.exp(-2*t)
                total = np.concatenate([total, wave])
            audio = (total * 32767 * volume).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except:
            return None

    def generate_bgm_loop(self):
        """Generate simple 8-bit battle city background loop (catchy)."""
        try:
            import numpy as np
            sr = 22050
            # Simple melody: repeating pattern like original Battle City BGM
            notes = [262, 294, 330, 349, 392, 440, 494, 523, 392, 330, 262]  # C D E F G A B C
            duration_note = 0.18
            melody = np.array([], dtype=np.float32)
            for freq in notes:
                t = np.linspace(0, duration_note, int(sr*duration_note), False)
                wave = np.sign(np.sin(freq * 2 * np.pi * t))  # square wave 8-bit
                wave = wave * 0.3 * np.exp(-1*t)
                melody = np.concatenate([melody, wave])
            # Add rest
            rest = np.zeros(int(sr*0.3))
            melody = np.concatenate([melody, rest, melody])
            audio = (melody * 32767 * 0.25).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except:
            return None

    def generate_punchy_shoot(self, f0=1200, f1=180, duration=0.18, volume=0.85, punch_freq=90, punch_vol=0.9, add_second_layer=False, short=False):
        """
        Generate a punchy, satisfying shooting sound - much better than authentic NES beep.
        Features:
        - Frequency sweep from high to low (pew)
        - Low-end punch at start (80-120Hz) for impact
        - Initial click/white noise transient
        - Square wave for retro but beefy feel
        - Exponential decay envelope
        """
        try:
            import numpy as np
            sr = 22050
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)

            # Exponential frequency sweep: f(t) = f0 * (f1/f0)^(t/duration)
            # Avoid log(0) issues
            if f1 <= 0:
                f1 = 20
            # Create sweep
            freq = f0 * np.power(f1 / f0, t / duration)

            # Phase integration for accurate sweep
            phase = np.cumsum(2 * np.pi * freq / sr)
            # Square wave (retro but punchy)
            wave = np.sign(np.sin(phase))

            # ADSR envelope: fast attack, quick decay, short sustain, quick release
            attack = int(0.001 * sr)  # 1ms attack
            decay = int(0.08 * sr)
            # Envelope
            env = np.ones(N)
            # Attack: 0 to 1 in 1ms
            if attack > 0:
                env[:attack] = np.linspace(0, 1, attack)
            # Decay: exponential
            decay_env = np.exp(-5 * np.linspace(0, 1, N - attack))
            env[attack:] = decay_env[:N-attack] if len(decay_env) >= N-attack else np.concatenate([decay_env, np.zeros(N-attack-len(decay_env))])

            # Apply envelope to main wave
            wave = wave * env

            # Punch layer: low frequency sine with fast decay at start - gives thump
            if punch_vol > 0 and punch_freq > 0:
                punch_duration = min(duration, 0.08)  # punch only first 80ms
                punch_N = int(sr * punch_duration)
                punch_t = np.linspace(0, punch_duration, punch_N, False)
                punch_phase = 2 * np.pi * punch_freq * punch_t
                punch_wave = np.sin(punch_phase) * np.exp(-15 * punch_t)  # fast decay
                # Add punch to main wave (first part)
                wave[:punch_N] += punch_wave * punch_vol

            # Click/transient at very start: short white noise burst 0-5ms for extra snap
            click_duration = int(0.006 * sr)
            if click_duration > 0 and N > click_duration:
                click_noise = np.random.uniform(-1, 1, click_duration) * 0.6
                # Fade out click
                click_env = np.exp(-100 * np.linspace(0, 0.006, click_duration))
                wave[:click_duration] += click_noise * click_env * 0.8

            # Second layer for power shots: add an octave lower square for extra beef
            if add_second_layer:
                # Second layer: f0/2 to f1/2
                freq2 = freq * 0.5
                phase2 = np.cumsum(2 * np.pi * freq2 / sr)
                wave2 = np.sign(np.sin(phase2)) * env * 0.5
                wave += wave2

            # For rapid fire short version, make it even snappier
            if short:
                wave = wave * 0.9  # slightly quieter for rapid

            # Normalize to prevent clipping
            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.9

            # Convert to 16-bit
            audio = (wave * 32767 * volume).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except ImportError:
            return None
        except Exception as e:
            print(f"[Sound] Punchy shoot gen failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_spread_shoot(self):
        """Generate spread shot - 8-way firing sound: chord-like, slightly bigger"""
        try:
            import numpy as np
            sr = 22050
            duration = 0.22
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)

            # Chord: multiple frequencies at once for spread feel
            freqs = [800, 1000, 1200]  # major chord-ish
            wave = np.zeros(N)
            for i, f in enumerate(freqs):
                # Each voice sweeps down slightly
                f0 = f
                f1 = f * 0.3
                freq = f0 * np.power(f1 / f0, t / duration)
                phase = np.cumsum(2 * np.pi * freq / sr)
                voice = np.sign(np.sin(phase)) * np.exp(-6*t) * (0.5 - i*0.1)
                wave += voice

            # Add noise burst for spread
            noise = np.random.uniform(-1, 1, N) * np.exp(-20*t) * 0.3
            wave += noise

            # Normalize
            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.85

            audio = (wave * 32767 * 0.8).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Spread shoot gen failed: {e}")
            return None

    def generate_homing_shoot(self):
        """Generate homing missile sound: rising pitch with long tail, futuristic"""
        try:
            import numpy as np
            sr = 22050
            duration = 0.35
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)

            # Rising sweep for missile launch: 200Hz -> 1200Hz
            f0 = 200
            f1 = 1200
            freq = f0 * np.power(f1 / f0, t / duration)
            phase = np.cumsum(2 * np.pi * freq / sr)
            # Saw wave for missile whine
            wave = 2 * (phase / (2*np.pi) - np.floor(phase / (2*np.pi) + 0.5))
            # Envelope: slow attack, sustain, long release
            env = np.ones(N)
            attack = int(0.05 * sr)
            env[:attack] = np.linspace(0, 1, attack)
            env = env * np.exp(-1.5 * t) + 0.2 * (1 - np.exp(-3*t))
            wave = wave * env

            # Add high frequency beep for tracking
            beep_freq = 2000
            beep = np.sin(2 * np.pi * beep_freq * t) * np.exp(-8*t) * 0.3
            wave += beep

            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.8

            audio = (wave * 32767 * 0.75).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Homing shoot gen failed: {e}")
            return None

    def generate_plasma_shoot(self):
        """Generate plasma/laser sound: high-energy, bright"""
        try:
            import numpy as np
            sr = 22050
            duration = 0.18
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)

            # Fast sweep 1500 -> 300 with vibrato
            f0 = 1500
            f1 = 300
            base_freq = f0 * np.power(f1 / f0, t / duration)
            # Add vibrato
            vibrato = 1 + 0.1 * np.sin(2 * np.pi * 30 * t)
            freq = base_freq * vibrato
            phase = np.cumsum(2 * np.pi * freq / sr)
            wave = np.sin(phase)  # sine for plasma smooth

            # Add square layer for edge
            wave2 = np.sign(np.sin(phase)) * 0.3

            env = np.exp(-6*t)
            wave = (wave * 0.7 + wave2 * 0.3) * env

            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.85

            audio = (wave * 32767 * 0.8).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Plasma shoot gen failed: {e}")
            return None

    def generate_real_tank_cannon(self, volume=0.9):
        """
        Generate realistic tank cannon fire - close to real life
        Layers:
        - Sub-bass 35-50Hz boom with long decay (0.6s) - chest thump
        - Low-mid 120Hz body
        - Mid punch 250Hz square
        - High crack 3000Hz transient 0-30ms
        - Blast white noise low-passed 0-150ms
        - Reverb echo at 120ms
        """
        try:
            import numpy as np
            sr = 44100  # higher quality for realism
            duration = 0.75
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)

            wave = np.zeros(N)

            # 1. Sub-bass boom 40Hz - long, powerful, chest feel
            # Use sine with exponential decay, slight pitch drop 50->35Hz
            f_sub_start, f_sub_end = 55, 32
            freq_sub = f_sub_start * np.power(f_sub_end / f_sub_start, t / duration)
            phase_sub = np.cumsum(2 * np.pi * freq_sub / sr)
            sub = np.sin(phase_sub) * np.exp(-5 * t) * 1.2
            wave += sub * 0.9

            # 2. Low-mid body 120Hz
            f_body = 120
            body = np.sin(2 * np.pi * f_body * t) * np.exp(-7 * t) * 0.7
            wave += body * 0.6

            # 3. Mid punch 250Hz square with distortion
            f_mid_start, f_mid_end = 300, 120
            freq_mid = f_mid_start * np.power(f_mid_end / f_mid_start, t / duration)
            phase_mid = np.cumsum(2 * np.pi * freq_mid / sr)
            mid = np.sign(np.sin(phase_mid)) * np.exp(-12 * t)
            # Add slight distortion (clip)
            mid = np.clip(mid * 1.5, -1, 1) * 0.5
            wave += mid

            # 4. Blast - white noise low-passed 0-0.15s, high energy
            blast_dur = int(0.15 * sr)
            if blast_dur < N:
                noise = np.random.uniform(-1, 1, blast_dur)
                # Simple low-pass via moving average (box filter)
                window = 20
                if len(noise) > window:
                    # Moving average to low-pass at ~1000Hz
                    kernel = np.ones(window) / window
                    noise = np.convolve(noise, kernel, mode='same')
                blast_env = np.exp(-25 * np.linspace(0, 0.15, blast_dur))  # fast decay
                blast = noise * blast_env * 1.1
                wave[:blast_dur] += blast * 0.8

            # 5. High crack - 3000Hz transient 0-0.03s for initial snap
            crack_dur = int(0.03 * sr)
            if crack_dur < N:
                crack_t = np.linspace(0, 0.03, crack_dur, False)
                crack = np.sin(2 * np.pi * 3000 * crack_t) * np.exp(-150 * crack_t) * 0.5
                # Add second harmonic for brightness
                crack += np.sin(2 * np.pi * 6000 * crack_t) * np.exp(-150 * crack_t) * 0.25
                wave[:crack_dur] += crack

            # 6. Shell ejection clink - small metallic tick at 0.1s
            clink_time = int(0.12 * sr)
            clink_dur = int(0.02 * sr)
            if clink_time + clink_dur < N:
                clink_t = np.linspace(0, 0.02, clink_dur, False)
                clink = np.sin(2 * np.pi * 2500 * clink_t) * np.exp(-80 * clink_t) * 0.15
                # Add with slight randomness
                wave[clink_time:clink_time+clink_dur] += clink

            # 7. Reverb - delayed quiet copy at 120ms with echo
            delay = int(0.12 * sr)
            if delay + N//3 < N:
                reverb = np.zeros(N)
                # Quiet copy of wave with low-pass and delay
                reverb[delay:] = wave[:N-delay] * 0.25 * np.exp(-2 * t[:N-delay])
                wave += reverb * 0.6

            # 8. Ground reflection - very low frequency rumble at 60ms
            ground_delay = int(0.06 * sr)
            if ground_delay < N:
                ground = np.sin(2 * np.pi * 60 * t) * np.exp(-4 * (t-0.06)) * 0.3
                ground[:ground_delay] = 0
                wave += ground * 0.4

            # Normalize with headroom for punch
            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.92

            # Slight distortion for realism (soft clipping)
            wave = np.tanh(wave * 1.2) * 0.9

            audio = (wave * 32767 * volume).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except ImportError:
            return None
        except Exception as e:
            print(f"[Sound] Real tank cannon gen failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_real_brick_hit(self, volume=0.9):
        """
        Realistic brick/concrete hit - when tank shell hits brick wall - IMPROVED
        User feedback: previous brick hit still not correct, needs more realistic
        Layers for close-to-real-life brick wall hit by tank shell:
        - 0-3ms: Ultra-sharp transient crack (4000Hz + 8000Hz) - initial shell impact
        - 3-30ms: Main loud crack - broadband noise + 1200Hz + 2500Hz resonances - brick shattering
        - 10-150ms: Heavy thud - 80Hz + 150Hz low boom from wall mass
        - 30-400ms: Multiple secondary cracks - random high-freq pops mimicking bricks breaking apart
        - 100-500ms: Debris crumble - small pieces falling, granular noise
        - 200-600ms: Dust hiss - high-freq filtered noise tail
        """
        try:
            import numpy as np
            sr = 44100
            duration = 0.65  # slightly longer for more realistic tail
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)
            wave = np.zeros(N)

            # 1. Ultra-sharp initial impact - 0-3ms, very high freq, mimics shell hitting hard brick
            click_dur = int(0.003 * sr)
            if click_dur < N:
                click_t = np.linspace(0, 0.003, click_dur, False)
                # Combination of 4000Hz and 8000Hz for sharp crack
                click = np.sin(2 * np.pi * 4000 * click_t) * 0.6
                click += np.sin(2 * np.pi * 8000 * click_t) * 0.3
                click *= np.exp(-600 * click_t)  # ultra-fast decay
                wave[:click_dur] += click * 1.2

            # 2. Main loud crack - 3-80ms, broadband with resonances at 1200Hz and 2500Hz
            # This is the core brick shattering sound
            crack_start = int(0.003 * sr)
            crack_dur = int(0.08 * sr)
            if crack_start + crack_dur < N:
                crack_N = crack_dur
                crack_t = np.linspace(0, 0.08, crack_N, False)
                # White noise burst
                noise = np.random.uniform(-1, 1, crack_N)
                # Bandpass around 1200Hz and 2500Hz via sine modulation + filtering
                # Create two resonant cracks
                env = np.exp(-18 * crack_t)  # fast decay for main crack
                crack1 = noise * env * 0.7
                # Add tonal resonances for brick size (bricks resonate around 1-2.5kHz when breaking)
                res1 = np.sin(2 * np.pi * 1200 * crack_t) * env * 0.5
                res2 = np.sin(2 * np.pi * 2500 * crack_t) * np.exp(-25 * crack_t) * 0.35
                crack = crack1 + res1 + res2
                wave[crack_start:crack_start+crack_N] += crack * 1.0

            # 3. Heavy thud - low frequency from wall mass and tank shell energy
            # 80Hz and 150Hz with slower decay, starts slightly after impact (5ms delay)
            thud_start = int(0.005 * sr)
            thud_dur = int(0.18 * sr)
            if thud_start + thud_dur < N:
                thud_t = np.linspace(0, 0.18, thud_dur, False)
                thud = np.sin(2 * np.pi * 80 * thud_t) * np.exp(-10 * thud_t) * 0.9
                thud += np.sin(2 * np.pi * 150 * thud_t) * np.exp(-12 * thud_t) * 0.5
                # Add slight distortion for weight
                thud = np.tanh(thud * 1.3) * 0.8
                wave[thud_start:thud_start+thud_dur] += thud * 0.7

            # 4. Secondary cracks - multiple random high-freq pops 20-200ms
            # Real brick wall doesn't break cleanly, it has multiple secondary fractures
            num_secondary = 12
            for _ in range(num_secondary):
                sec_time = np.random.uniform(0.02, 0.20)
                sec_idx = int(sec_time * sr)
                sec_dur = int(np.random.uniform(0.015, 0.04) * sr)
                if sec_idx + sec_dur < N:
                    sec_freq = np.random.uniform(1800, 4500)
                    sec_t = np.linspace(0, sec_dur/sr, sec_dur, False)
                    sec = np.sin(2 * np.pi * sec_freq * sec_t) * np.exp(-35 * sec_t)
                    # Add noise for roughness
                    sec_noise = np.random.uniform(-1, 1, sec_dur) * np.exp(-30 * sec_t) * 0.3
                    wave[sec_idx:sec_idx+sec_dur] += (sec + sec_noise) * np.random.uniform(0.15, 0.4)

            # 5. Debris crumble - granular, random small pieces 80-450ms
            num_debris = 15
            for _ in range(num_debris):
                deb_time = np.random.uniform(0.08, 0.45)
                deb_idx = int(deb_time * sr)
                deb_dur = int(np.random.uniform(0.02, 0.06) * sr)
                if deb_idx + deb_dur < N:
                    deb_freq = np.random.uniform(400, 2200)
                    deb_t = np.linspace(0, deb_dur/sr, deb_dur, False)
                    # Debris is more noisy, less tonal
                    deb = np.sin(2 * np.pi * deb_freq * deb_t) * np.exp(-20 * deb_t) * 0.5
                    deb += np.random.uniform(-1, 1, deb_dur) * np.exp(-15 * deb_t) * 0.3
                    wave[deb_idx:deb_idx+deb_dur] += deb * np.random.uniform(0.1, 0.28)

            # 6. Dust hiss - high-frequency filtered noise tail 150-600ms
            # Fine dust after bricks break
            dust_start = int(0.15 * sr)
            dust_dur = int(0.45 * sr)
            if dust_start + dust_dur < N:
                dust_t = np.linspace(0, 0.45, dust_dur, False)
                # High-freq hiss: white noise with high-pass feel (modulate with high freq)
                dust_noise = np.random.uniform(-1, 1, dust_dur)
                # High-pass via differencing (simple)
                dust_noise = np.diff(np.concatenate([[0], dust_noise]))
                dust_env = np.exp(-4 * dust_t) * 0.25
                dust = dust_noise * dust_env * (0.3 + 0.3 * np.sin(2 * np.pi * 6000 * dust_t * 0.1))
                wave[dust_start:dust_start+dust_dur] += dust * 0.35

            # 7. Add slight stereo variation for realism (delay one channel by 1ms)
            # We'll handle in final stereo conversion with slight pan

            # Normalize with headroom, keep punch
            max_val = np.max(np.abs(wave))
            if max_val > 0:
                # Leave headroom for punch, but make it loud
                wave = wave / max_val * 0.88

            # Soft clipping for extra punch and warmth
            wave = np.tanh(wave * 1.15) * 0.92

            # Create stereo with slight difference for width (delay right channel by 2ms for spaciousness)
            # Convert to float for processing to avoid int16 casting issues
            audio_float = wave * 32767 * volume
            # Create stereo float
            stereo_float = np.column_stack([audio_float, audio_float])
            # Add slight pan variation for debris to feel spatial - Haas effect
            delay_samples = int(0.002 * sr)  # 2ms delay
            if len(stereo_float) > delay_samples:
                delay_end = int(0.1 * sr)
                if delay_end < len(stereo_float):
                    orig_right = stereo_float[:delay_end, 1].copy()
                    # Apply with float operations
                    stereo_float[delay_samples:delay_end, 1] = orig_right[:-delay_samples] * 0.9
                    stereo_float[:delay_samples, 1] *= 0.5

            # Convert to int16 for pygame
            # Clip to prevent overflow
            stereo_float = np.clip(stereo_float, -32767, 32767)
            stereo = stereo_float.astype(np.int16)

            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Real brick hit gen failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_brick_hit_hybrid(self, volume=0.9):
        """
        Hybrid brick hit: Mix real tank shot low-end boom with synthetic brick crack high-end
        This sounds like a tank shell actually hitting a brick wall - both explosion and brick shattering
        Much more realistic than just tank shot or just crack alone
        """
        try:
            import numpy as np
            # Try to get the two source sounds if already loaded
            tank_sound = None
            brick_sound = None

            # Try to use already generated or loaded sounds
            if 'real_tank_single' in self.sounds:
                tank_sound = self.sounds['real_tank_single']
            elif 'shoot' in self.sounds:
                tank_sound = self.sounds['shoot']

            # For brick, use the synthetic improved version that is currently in hit_brick or generate fresh
            if 'hit_brick' in self.sounds:
                # This should be the improved synthetic at this point
                brick_sound = self.sounds['hit_brick']

            # If we don't have both, try to generate fresh synthetic brick
            if brick_sound is None:
                brick_sound = self.generate_real_brick_hit(volume=0.8)

            if tank_sound is None or brick_sound is None:
                print("[Sound] Hybrid: missing source sounds, generating fresh")
                return self.generate_real_brick_hit(volume=volume)

            # Get arrays
            try:
                tank_arr = pygame.sndarray.array(tank_sound)
                brick_arr = pygame.sndarray.array(brick_sound)
            except Exception as e:
                print(f"[Sound] Hybrid array conversion failed: {e}, using brick only")
                return brick_sound

            # Convert to mono float for mixing
            if len(tank_arr.shape) == 2:
                tank_mono = np.mean(tank_arr, axis=1).astype(np.float32)
            else:
                tank_mono = tank_arr.astype(np.float32)

            if len(brick_arr.shape) == 2:
                brick_mono = np.mean(brick_arr, axis=1).astype(np.float32)
            else:
                brick_mono = brick_arr.astype(np.float32)

            # Make same length - use max length, pad shorter with zeros
            max_len = max(len(tank_mono), len(brick_mono))
            # Pad both to max_len
            tank_padded = np.zeros(max_len, dtype=np.float32)
            brick_padded = np.zeros(max_len, dtype=np.float32)
            tank_padded[:len(tank_mono)] = tank_mono[:max_len]
            brick_padded[:len(brick_mono)] = brick_mono[:max_len]

            # Mix: tank low frequencies (boom) + brick high frequencies (crack/debris)
            # For tank, keep mostly low frequencies: we can low-pass by smoothing
            # Simple low-pass for tank: moving average to keep low end
            # For brick, keep high frequencies: subtract moving average
            # But for simplicity, mix with volumes: tank 0.5 (for boom) + brick 0.9 (for crack)
            # Tank has strong low-end, brick has strong high-end, so they complement

            # Normalize each first
            tank_max = np.max(np.abs(tank_padded))
            brick_max = np.max(np.abs(brick_padded))
            if tank_max > 0:
                tank_norm = tank_padded / tank_max
            else:
                tank_norm = tank_padded

            if brick_max > 0:
                brick_norm = brick_padded / brick_max
            else:
                brick_norm = brick_padded

            # Mix: 35% tank (for thump) + 75% brick (for crack) - brick should be more prominent for hit feedback
            hybrid = tank_norm * 0.35 + brick_norm * 0.85

            # Add extra punch - emphasize initial transient from both
            # Find initial 50ms and boost by 1.2x
            attack_samples = int(44100 * 0.05)
            if len(hybrid) > attack_samples:
                hybrid[:attack_samples] *= 1.25

            # Normalize final
            max_val = np.max(np.abs(hybrid))
            if max_val > 0:
                hybrid = hybrid / max_val * 0.92

            # Convert to int16 stereo
            # Slight stereo width: left slightly more brick, right slightly more tank
            left = hybrid * 0.95 + tank_norm[:len(hybrid)] * 0.05
            right = hybrid * 0.95 + brick_norm[:len(hybrid)] * 0.05

            # Normalize stereo together
            stereo_max = max(np.max(np.abs(left)), np.max(np.abs(right)))
            if stereo_max > 0:
                left = left / stereo_max * 0.9
                right = right / stereo_max * 0.9

            stereo = np.column_stack([
                (left * 32767 * volume).astype(np.int16),
                (right * 32767 * volume).astype(np.int16)
            ])

            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Hybrid brick hit gen failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_real_steel_hit(self, volume=0.85):
        """
        Realistic steel armor hit - ricochet, clang
        """
        try:
            import numpy as np
            sr = 44100
            duration = 0.6
            N = int(sr * duration)
            t = np.linspace(0, duration, N, False)
            wave = np.zeros(N)

            # 1. Very sharp initial impact - high freq
            click_dur = int(0.003 * sr)
            if click_dur < N:
                click = np.random.uniform(-1, 1, click_dur) * np.exp(-200 * np.linspace(0, 0.003, click_dur)) * 0.9
                wave[:click_dur] += click

            # 2. Main steel clang - 800Hz + 1600Hz + 2400Hz harmonics, long decay with beating
            # Steel has long metallic ring
            for i, (freq, amp, decay) in enumerate([(800, 0.8, 3), (1600, 0.5, 2.5), (2400, 0.3, 3.5), (3200, 0.2, 4)]):
                clang = np.sin(2 * np.pi * freq * t + i*0.5) * np.exp(-decay * t) * amp
                # Add slight frequency modulation for realistic beating
                clang *= (1 + 0.1 * np.sin(2 * np.pi * 15 * t))
                wave += clang

            # 3. Ricochet whine - rising pitch 1000->3000Hz whine after impact
            whine_dur = int(0.25 * sr)
            whine_start = int(0.05 * sr)
            if whine_start + whine_dur < N:
                whine_t = np.linspace(0, 0.25, whine_dur, False)
                f0, f1 = 800, 2500
                freq = f0 * np.power(f1/f0, whine_t/0.25)
                phase = np.cumsum(2 * np.pi * freq / sr)
                whine = np.sin(phase) * np.exp(-6 * whine_t) * 0.35
                wave[whine_start:whine_start+whine_dur] += whine

            # Normalize
            max_val = np.max(np.abs(wave))
            if max_val > 0:
                wave = wave / max_val * 0.9

            audio = (wave * 32767 * volume).astype(np.int16)
            stereo = np.column_stack([audio, audio])
            return pygame.sndarray.make_sound(stereo)
        except Exception as e:
            print(f"[Sound] Real steel hit gen failed: {e}")
            return None

    # ---- Playback ----

    def play(self, name, volume=None, pitch_random=False):
        if self.muted or not self.enabled:
            return
        if name not in self.sounds:
            # fallback alias
            if name == 'shoot' and 'hit_brick' in self.sounds:
                name = 'hit_brick'
            else:
                return
        try:
            snd = self.sounds[name]
            if volume is not None:
                orig_vol = snd.get_volume()
                snd.set_volume(volume * self.volume)
            else:
                snd.set_volume(self.volume)

            # For some classic NES sounds, original game had randomization of pitch for variety
            if pitch_random:
                # We don't pitch shift easily, just play as is
                pass

            snd.play()

            if volume is not None:
                # restore?
                pass
        except Exception as e:
            print(f"[Sound] play {name} failed: {e}")

    def play_shoot(self, shoot_type='normal'):
        """
        Play shooting sound - now with better variants
        shoot_type: 'normal', 'power', 'rapid', 'spread', 'homing', 'plasma', 'punchy'
        """
        # Map shoot_type to sound name, with fallback chain
        type_map = {
            'normal': ['shoot', 'shoot_punchy', 'shoot_plasma'],
            'power': ['shoot_power', 'shoot_strong', 'shoot_punchy', 'shoot'],
            'rapid': ['shoot_rapid', 'shoot_rapid_3x', 'shoot'],
            'spread': ['shoot_spread', 'shoot_8way', 'shoot'],
            'homing': ['shoot_homing', 'shoot_missile', 'shoot_tracker', 'shoot'],
            'missile': ['shoot_homing', 'shoot_missile', 'shoot'],
            'plasma': ['shoot_plasma', 'shoot_laser', 'shoot'],
            'punchy': ['shoot_punchy', 'shoot'],
            'beefy': ['shoot_power', 'shoot_punchy', 'shoot'],
        }

        # Determine which list to try
        candidates = type_map.get(shoot_type, type_map['normal'])

        for snd_name in candidates:
            if snd_name in self.sounds:
                # Adjust volume based on type
                vol = 0.7
                if shoot_type in ('power', 'plasma'):
                    vol = 0.85
                elif shoot_type == 'rapid':
                    vol = 0.6  # rapid is quieter but snappy
                elif shoot_type in ('spread', 'homing'):
                    vol = 0.8
                self.play(snd_name, volume=vol)
                return

        # Fallback to normal shoot
        self.play('shoot', volume=0.7)

    def play_hit_brick(self):
        self.play('hit_brick', volume=0.6)

    def play_hit_steel(self):
        self.play('hit_steel', volume=0.7)

    def play_explosion(self, big=False):
        # Random between explosion_1/2 for variety, 700 enemies destroyed
        if big:
            self.play('explosion_big', volume=0.9)
        else:
            # Random among explosion sounds
            if self.explosion_sounds:
                try:
                    import random
                    snd = random.choice(self.explosion_sounds)
                    snd.set_volume(0.8 * self.volume)
                    snd.play()
                except:
                    self.play('explosion', volume=0.8)
            else:
                self.play('explosion', volume=0.8)

    def play_brick_break(self):
        # Original NES had same as hit but with extra crack
        self.play('brick_break' if 'brick_break' in self.sounds else 'hit_brick', volume=0.8)

    def play_powerup_appear(self):
        self.play('powerup_appear', volume=0.9)

    def play_powerup_pick(self):
        self.play('powerup_pick', volume=0.9)

    def play_spawn(self):
        self.play('spawn' if 'spawn' in self.sounds else 'powerup_appear', volume=0.6)

    def play_stage_start(self):
        self.play('stage_start', volume=0.9)

    def play_game_over(self):
        self.play('game_over', volume=0.8)

    def play_stage_clear(self):
        self.play('stage_clear', volume=0.8)

    def play_move_loop(self):
        """Tank move rolling loop - authentic Battle City had continuous tread sound when moving."""
        if self.muted or not self.enabled:
            return
        # For performance, only play occasionally, not every frame
        self.move_timer += 1
        if self.move_timer % 12 == 0:  # every 12 frames
            if 'move_loop' in self.sounds:
                self.sounds['move_loop'].set_volume(0.15 * self.volume)
                self.sounds['move_loop'].play()

    def play_battle_intro(self):
        """Play the authentic Battle City Tank 1990 NES Intro 8bit Live by deegee (5.59 sec).
        This is user downloaded: 'Battle City _ Tank 1990 NES _ Intro _ Live _ 8bit - id deegee (D.G.).m4a'
        Converted to battle_city_intro_final.wav (PCM 44100) for pygame compatibility.
        Used when new game starts.
        """
        if self.muted or not self.enabled:
            return
        # Try realistic intro files in order of preference (wav final is most compatible)
        for name in ['battle_intro', 'battle_intro_wav_classic', 'battle_intro_m4a']:
            if name in self.sounds:
                try:
                    # Stop any previous
                    # self.sounds[name].stop()  # dont stop all, just play
                    self.sounds[name].set_volume(0.85 * self.volume)
                    self.sounds[name].play()
                    print(f"[Sound] 🎵 Playing authentic NES intro: {name} (Battle City Tank 1990 Intro Live 8bit by deegee)")
                    return True
                except Exception as e:
                    print(f"[Sound] Intro play {name} failed: {e}")
                    continue

        # Fallback: try pygame.music load of the m4a original if pygame.mixer can handle it via music channel
        try:
            # Search for original m4a in various places
            candidates = [
                SOUND_DIR.parent / "music" / "intro.m4a",
                pathlib.Path("/Users/yuzhoubrother/Documents/tank93/Battle City _ Tank 1990 NES _ Intro _ Live _ 8bit - id deegee (D.G.).m4a"),
                SOUND_DIR / "intro.m4a",
                SOUND_DIR.parent / "music" / "intro.wav",
            ]
            for cand in candidates:
                if cand.exists():
                    pygame.mixer.music.load(str(cand))
                    pygame.mixer.music.set_volume(0.8 * self.volume)
                    pygame.mixer.music.play()
                    print(f"[Sound] 🎵 Playing intro via music channel: {cand.name}")
                    return True
        except Exception as e:
            print(f"[Sound] Intro music channel failed: {e}")

        # Last fallback to stage_start jingle
        self.play_stage_start()
        return False

    # ---- Music ----

    def play_bgm(self, name='bgm_battle'):
        """Authentic NES had NO battlefield BGM (only SFX during fight). This silly loop is disabled by default.
        Only intro BGM (battle_intro) is played at new game start.
        """
        # Disable silly battle loop – keep authenticity
        if name == 'bgm_battle':
            # Do nothing, original NES had no music during battle, only SFX
            # Print once
            if not hasattr(self, '_bgm_silly_warned'):
                print("[Sound] 🚫 Battlefield BGM disabled - authentic NES Battle City had no BGM during battle, only SFX (your request: remove silly BGM).")
                self._bgm_silly_warned = True
            return

        if self.muted or not self.enabled:
            return
        if name in self.sounds:
            try:
                pygame.mixer.music.stop()
                self.sounds[name].play(loops=-1)
                self.bg_music_playing = True
                self.current_bgm = name
            except:
                pass

    def stop_bgm(self):
        try:
            for snd in self.sounds.values():
                # Don't stop the intro if it's still playing? We'll stop all for now except we keep music channel separate
                if snd not in [self.sounds.get('battle_intro'), self.sounds.get('battle_intro_wav_classic')]:
                    snd.stop()
            pygame.mixer.music.stop()
        except:
            pass
        self.bg_music_playing = False

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.stop_bgm()
        print(f"[Sound] {'MUTED' if self.muted else 'UNMUTED'} - {'🔇' if self.muted else '🔊'} 35-stage authentic NES sounds + Battle City Tank 1990 Intro by deegee")

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))

# Singleton
sound_manager = SoundManager()
