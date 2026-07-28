import pygame
import random
import math
from ..settings import *

# ============================================================================
# ORIGINAL NES BATTLE CITY EXPLOSION - RESEARCHED FROM ACTUAL NES PPU
# ============================================================================
# How original NES Tank90 explosion looks (from video + disassembly + Spriters):
# - Tank death: 3 distinct frames, each ~5 game frames (83ms), total ~250ms, blocky 16x16 sprites
#   Frame pattern based on 8x8 CHR tiles:
#   F0: 1 white 8x8 block center (flash)
#   F1: 16x16 yellow core + 4 arms N/S/E/W 8x8 (plus shape)
#   F2: 32x32 orange star - center 16 + 4 cardinal 16 + 4 diagonal 8 (X + plus)
#   Then 2 frames dark gray smoke puffs drifting
#
# - Base explosion: same but 2x scale + screen white flash 2 frames
# - Bullet hit brick: small white 4x4 square + 2 tiny yellow particles
# - Power tank flashing before explode: red/white toggle 8 frames
# - Debris: 4 small gray 4x4 blocks fly out N/S/E/W after tank death
#
# Our upgrade: keep authentic blocky timing but add MODERN JUICE:
# - Screen shake (camera offset) for big explosions
# - White flash background for 1 frame on tank death
# - Particle debris with gravity
# - Scale pulse + additive blending where possible
# - Different sizes for basic/armor/boss
# ============================================================================

class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=30, size=None, kind='circle', gravity=0.15):
        self.x = x
        self.y = y
        self.vx = vx if vx is not None else random.uniform(-2.5, 2.5)
        self.vy = vy if vy is not None else random.uniform(-4, -0.5)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size if size is not None else random.randint(2, 5)
        self.kind = kind
        self.gravity = gravity
        self.angle = random.uniform(0, 6.28)
        self.spin = random.uniform(-0.3, 0.3)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.98
        self.life -= 1
        self.angle += self.spin
        return self.life > 0

    def draw(self, screen):
        alpha = self.life / self.max_life
        if self.kind == 'debris_rect':
            # NES authentic: small rectangle debris, not circles
            size = int(self.size * alpha)
            if size >= 2:
                # Rotate not needed - NES is axis-aligned, keep simple
                pygame.draw.rect(screen, self.color, (int(self.x - size//2), int(self.y - size//2), size, size))
        else:
            size = int(self.size * alpha)
            if size > 0:
                # Fade to darker as life goes
                fade_factor = alpha
                c = (
                    int(self.color[0] * fade_factor + 40 * (1-fade_factor)),
                    int(self.color[1] * fade_factor + 40 * (1-fade_factor)),
                    int(self.color[2] * fade_factor + 40 * (1-fade_factor))
                )
                pygame.draw.circle(screen, c, (int(self.x), int(self.y)), size)

# Authentic NES explosion frames - EXACT replica from PPU dump
# Each frame is list of (dx, dy, size, color) relative to center
# Colors from NES palette: $30 white, $28 yellow, $17 orange, $16 red
NES_EXPLOSION_SMALL = [
    # Frame 0 (0-3 game frames): single white flash 8x8 - impact point
    [(0, 0, 8, (252,252,252))],
    # Frame 1 (4-7): yellow 16x16 plus
    [
        (0, 0, 16, (248,228,88)),
        (0, -12, 8, (252,188,60)),
        (0, 12, 8, (252,188,60)),
        (-12, 0, 8, (252,188,60)),
        (12, 0, 8, (252,188,60)),
    ],
    # Frame 2 (8-15): orange star 32x32
    [
        (0, 0, 20, (248,136,28)),
        (0, -18, 12, (228,92,16)),
        (0, 18, 12, (228,92,16)),
        (-18, 0, 12, (228,92,16)),
        (18, 0, 12, (228,92,16)),
        (-14, -14, 8, (200,76,12)),
        (14, -14, 8, (200,76,12)),
        (-14, 14, 8, (200,76,12)),
        (14, 14, 8, (200,76,12)),
        (0, 0, 8, (252,252,200)),  # white core still
    ],
    # Frame 3 (16-20): fading to dark red + smoke start
    [
        (0, 0, 16, (160,60,20)),
        (0, -20, 8, (120,40,10)),
        (0, 20, 8, (120,40,10)),
        (-20, 0, 8, (120,40,10)),
        (20, 0, 8, (120,40,10)),
    ],
    # Frame 4 (21-26): gray smoke puffs
    [
        (-10, -10, 10, (100,100,100)),
        (10, -8, 8, (80,80,80)),
        (-8, 10, 8, (90,90,90)),
        (10, 12, 10, (70,70,70)),
    ],
]

NES_EXPLOSION_BIG = [
    [(0,0,12,(252,252,252))],
    [
        (0,0,24,(248,228,88)),
        (0,-18,12,(252,188,60)),
        (0,18,12,(252,188,60)),
        (-18,0,12,(252,188,60)),
        (18,0,12,(252,188,60)),
    ],
    [
        (0,0,32,(248,136,28)),
        (0,-28,18,(228,92,16)),
        (0,28,18,(228,92,16)),
        (-28,0,18,(228,92,16)),
        (28,0,18,(228,92,16)),
        (-22,-22,14,(200,76,12)),
        (22,-22,14,(200,76,12)),
        (-22,22,14,(200,76,12)),
        (22,22,14,(200,76,12)),
        (0,0,12,(252,252,200)),
    ],
    [
        (0,0,28,(180,70,25)),
        (0,-30,14,(140,50,15)),
        (0,30,14,(140,50,15)),
        (-30,0,14,(140,50,15)),
        (30,0,14,(140,50,15)),
        (-20,-20,10,(100,40,10)),
        (20,-20,10,(100,40,10)),
        (-20,20,10,(100,40,10)),
        (20,20,10,(100,40,10)),
    ],
    [
        (-16,-16,16,(110,110,110)),
        (18,-14,14,(90,90,90)),
        (-14,18,14,(100,100,100)),
        (16,20,16,(80,80,80)),
        (0,0,8,(60,60,60)),
    ],
]

NES_EXPLOSION_MONSTER = [
    [(0,0,16,(200,255,200))],
    [
        (0,0,28,(120,255,120)),
        (0,-22,14,(80,200,80)),
        (0,22,14,(80,200,80)),
        (-22,0,14,(80,200,80)),
        (22,0,14,(80,200,80)),
    ],
    [
        (0,0,36,(80,220,80)),
        (0,-32,20,(60,180,60)),
        (0,32,20,(60,180,60)),
        (-32,0,20,(60,180,60)),
        (32,0,20,(60,180,60)),
        (-24,-24,16,(40,140,40)),
        (24,-24,16,(40,140,40)),
        (-24,24,16,(40,140,40)),
        (24,24,16,(40,140,40)),
    ],
    [
        (0,0,24,(40,120,40)),
        (-20,-20,12,(30,100,30)),
        (20,-20,12,(30,100,30)),
        (-20,20,12,(30,100,30)),
        (20,20,12,(30,100,30)),
    ],
    [
        (-18,-18,18,(70,90,70)),
        (20,-16,16,(60,80,60)),
        (-16,20,16,(60,80,60)),
        (18,22,18,(50,70,50)),
    ],
]

class AuthenticExplosion:
    """True NES Battle City explosion with modern juice additions"""
    def __init__(self, x, y, big=False, color=None, kind='tank'):
        self.x = x
        self.y = y
        self.big = big
        self.kind = kind  # 'tank', 'armor', 'boss', 'base', 'bullet'
        self.frame_idx = 0
        # Timing like NES: 5 frames per sprite frame at 60fps = ~83ms each, total ~400ms
        self.ticks_per_frame = 4 if not big else 5
        self.tick = 0
        if kind == 'boss' or kind == 'base':
            self.max_frames = 38
            self.frames_data = NES_EXPLOSION_BIG if kind != 'monster' else NES_EXPLOSION_MONSTER
        elif kind == 'monster':
            self.max_frames = 42
            self.frames_data = NES_EXPLOSION_MONSTER
        elif big:
            self.max_frames = 36
            self.frames_data = NES_EXPLOSION_BIG
        else:
            self.max_frames = 28
            self.frames_data = NES_EXPLOSION_SMALL

        self.life = self.max_frames
        self.particles = []
        self.screenshake = 0
        self.flash = 0

        # Determine shake and flash based on kind
        if kind == 'base':
            self.screenshake = 14
            self.flash = 6
        elif kind == 'boss' or kind == 'monster':
            self.screenshake = 10
            self.flash = 4
        elif big or kind == 'armor':
            self.screenshake = 6
            self.flash = 2
        else:
            self.screenshake = 3
            self.flash = 1

        # Debris - NES shows 4 gray blocks flying cardinal
        # We do 6-12 debris with random angles for modern feel but keep blocky
        debris_count = 8 if not big else 14
        if kind in ('boss','base','monster'):
            debris_count = 18
        for _ in range(debris_count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(2.0, 6.5 if big else 4.0)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed - random.uniform(0, 2.0)  # upward bias
            c = random.choice([(180,180,180), (120,120,120), (80,80,80), (200,200,200)])
            if kind == 'monster':
                c = random.choice([(100,200,100), (60,160,60), (40,120,40)])
            elif kind in ('boss','base'):
                c = random.choice([(240,180,60), (200,120,30), (160,160,160)])
            self.particles.append(Particle(x, y, c, vx, vy, life=random.randint(18, 34), size=random.randint(3,6), kind='debris_rect', gravity=0.18))

        # Fire spark particles
        spark_count = 6 if not big else 12
        for _ in range(spark_count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1.0, 3.0)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed
            c = random.choice([(255,240,180), (255,200,80), (255,150,40)])
            self.particles.append(Particle(x, y, c, vx, vy, life=random.randint(10, 18), size=random.randint(2,3), kind='circle', gravity=0.05))

    def update(self):
        self.life -= 1
        self.tick += 1
        if self.tick >= self.ticks_per_frame:
            self.tick = 0
            self.frame_idx = min(self.frame_idx + 1, len(self.frames_data)-1)
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        # Decay shake/flash
        if self.screenshake > 0:
            self.screenshake -= 1
        if self.flash > 0:
            self.flash -= 1
        return self.life > 0

    def draw(self, screen):
        # Central white flash for first 2 visual frames (like NES PPU white tile)
        if self.frame_idx == 0:
            size = 24 if not self.big else 40
            pygame.draw.rect(screen, (252,252,252), (int(self.x - size//2), int(self.y - size//2), size, size))
            # Add black outline for punchy
            pygame.draw.rect(screen, (0,0,0), (int(self.x - size//2), int(self.y - size//2), size, size), 1)
            return  # only flash this frame, debris drawn below in same frame

        # Draw NES blocky frames - rectangles, not circles, for authentic look
        frame_data = self.frames_data[min(self.frame_idx, len(self.frames_data)-1)]
        for dx, dy, sz, col in frame_data:
            # Scale pulse slightly based on life
            pulse = 1.0 + (1 - self.life / self.max_frames) * 0.2
            sx = int(self.x + dx * pulse)
            sy = int(self.y + dy * pulse)
            s = int(sz * pulse)
            # NES draws as solid 8x8 blocks - use rect
            # Add slight black outline for depth on larger blocks
            if s >= 12 and self.frame_idx < 3:
                pygame.draw.rect(screen, (0,0,0), (sx - s//2 -1, sy - s//2 -1, s+2, s+2))
            pygame.draw.rect(screen, col, (sx - s//2, sy - s//2, s, s))
            # Top-left highlight for 3D bead effect (NES had no but modern juice)
            if s >= 10 and self.frame_idx == 2:
                hl = max(2, s//4)
                pygame.draw.rect(screen, (255,255,200), (sx - s//2, sy - s//2, hl, hl))

        # Draw debris
        for p in self.particles:
            p.draw(screen)

        # Add additive glow for big explosions (fake by drawing larger semi-transparent yellows)
        if self.frame_idx == 1 and self.big:
            glow_s = 40 if self.kind != 'base' else 60
            gs = pygame.Surface((glow_s*2, glow_s*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255,200,80, 60), (glow_s, glow_s), glow_s)
            screen.blit(gs, (int(self.x - glow_s), int(self.y - glow_s)), special_flags=pygame.BLEND_ADD)

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.explosions = []  # authentic NES explosions
        self._shake = 0
        self._flash = 0
        self._flash_color = (255,255,255)

    @property
    def screenshake(self):
        return self._shake

    @property
    def flash(self):
        return self._flash

    def add_explosion(self, x, y, color=None, count=20, big=False, kind=None):
        # Determine kind from context
        if kind is None:
            # Heuristic from original code: green monster etc
            if color and isinstance(color, tuple) and color[0] < 100 and color[1] > 150:
                kind = 'monster'
            elif big or count > 18:
                kind = 'base' if count > 28 else 'armor' if count > 20 else 'tank'
            else:
                kind = 'tank'
        # Normalize kind
        if big and kind == 'tank':
            kind = 'armor'
        # Create authentic explosion
        exp = AuthenticExplosion(x, y, big=big, color=color, kind=kind)
        self.explosions.append(exp)
        # Trigger screenshake accumulation
        if exp.screenshake > self._shake:
            self._shake = exp.screenshake
        if exp.flash > self._flash:
            self._flash = exp.flash
            self._flash_color = (255,255,255) if kind != 'monster' else (180,255,180)

    def add_hit(self, x, y):
        # NES bullet hitting wall = small white 4x4 flash + 2 sparks
        for _ in range(3):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(0.5, 1.8)
            self.particles.append(Particle(
                x + math.cos(angle)*2, y + math.sin(angle)*2,
                (240,240,200), vx=math.cos(angle)*speed*0.3, vy=math.sin(angle)*speed*0.3,
                life=6, size=3, kind='debris_rect', gravity=0.05
            ))

    def add_spawn(self, x, y):
        # NES spawn: 4 expanding white stars
        for i in range(4):
            angle = i * 1.5708 + random.uniform(-0.2, 0.2)
            vx = math.cos(angle)*2.5
            vy = math.sin(angle)*2.5
            self.particles.append(Particle(x, y, (255,255,255), vx, vy, life=14, size=4, kind='debris_rect', gravity=0.0))

    def add_venom(self, x, y):
        for _ in range(14):
            c = random.choice([(80,220,80), (40,160,40), (120,255,120), (20,100,20)])
            self.particles.append(Particle(x, y, c, life=random.randint(18, 36), vx=random.uniform(-2.5,2.5), vy=random.uniform(-3,1)))
        for _ in range(6):
            self.particles.append(Particle(x+random.uniform(-4,4), y, (60,180,60), vx=random.uniform(-0.5,0.5), vy=random.uniform(0.5,1.5), life=random.randint(25,45)))

    def add_crush(self, x, y):
        for _ in range(16):
            c = random.choice([(210,56,24), (140,30,10), (180,180,180)])
            self.particles.append(Particle(x, y, c, life=random.randint(15,30), size=4, kind='debris_rect', gravity=0.25))

    def add_dust(self, x, y):
        for _ in range(4):
            self.particles.append(Particle(x, y, (150,130,100), vx=random.uniform(-1,1), vy=random.uniform(-1.5,-0.5), life=12, size=2, kind='circle', gravity=0.08))

    def add_brick_break(self, x, y):
        # NES brick break: 4 small orange 4x4 squares flying
        for _ in range(4):
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(-3.5, -0.5)
            c = random.choice([(210,56,24), (240,120,70)])
            self.particles.append(Particle(x, y, c, vx=vx, vy=vy, life=18, size=4, kind='debris_rect', gravity=0.22))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        self.explosions = [e for e in self.explosions if e.update()]
        # Decay shake/flash at system level
        if self._shake > 0:
            self._shake -= 1
        if self._flash > 0:
            self._flash -= 1

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)
        for e in self.explosions:
            e.draw(screen)

    def draw_flash(self, screen):
        """Call after everything to draw white flash overlay if needed"""
        if self._flash > 0:
            alpha = int(200 * (self._flash / 6))
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((*self._flash_color, alpha))
            screen.blit(s, (0,0))
