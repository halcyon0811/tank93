import pygame
import random
import math
from ..settings import *

class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=30, size=None, kind='circle'):
        self.x = x
        self.y = y
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-3, 3)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size if size is not None else random.randint(2, 6)
        self.kind = kind
        self.angle = random.uniform(0, 6.28)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.kind != 'debris':
            self.vy += 0.12
        self.vx *= 0.99
        self.life -= 1
        self.angle += 0.15
        return self.life > 0

    def draw(self, screen):
        alpha = self.life / self.max_life
        size = int(self.size * alpha)
        if size > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)

# Authentic Battle City NES explosion - frame by frame
# NES explosion animation: 4 frames, expanding cross/plus shape, colors: white -> yellow -> orange -> red -> black smoke
NES_EXPLOSION_FRAMES = [
    # Frame 0: small white core
    [ 
        (0,0, 2, (255,255,255)),
    ],
    # Frame 1: medium yellow plus
    [
        (0,0, 4, (255,255,220)),
        (0,-6, 2, (255,220,100)),
        (0,6, 2, (255,220,100)),
        (-6,0, 2, (255,220,100)),
        (6,0, 2, (255,220,100)),
    ],
    # Frame 2: large orange star
    [
        (0,0, 7, (255,200,50)),
        (0,-12, 3, (255,180,40)),
        (0,12, 3, (255,180,40)),
        (-12,0, 3, (255,180,40)),
        (12,0, 3, (255,180,40)),
        (-8,-8, 2, (255,160,30)),
        (8,-8, 2, (255,160,30)),
        (-8,8, 2, (255,160,30)),
        (8,8, 2, (255,160,30)),
    ],
    # Frame 3: huge red with smoke puffs
    [
        (0,0, 10, (255,100,20)),
        (0,-18, 4, (255,80,20)),
        (0,18, 4, (255,80,20)),
        (-18,0, 4, (255,80,20)),
        (18,0, 4, (255,80,20)),
        (-12,-12, 3, (200,60,10)),
        (12,-12, 3, (200,60,10)),
        (-12,12, 3, (200,60,10)),
        (12,12, 3, (200,60,10)),
        (0,0, 5, (255,255,200)),
    ],
    # Frame 4: fading smoke
    [
        (-8,-8, 6, (80,80,80)),
        (8,-8, 5, (100,100,100)),
        (-8,8, 5, (100,100,100)),
        (8,8, 6, (80,80,80)),
        (0,0, 3, (50,50,50)),
    ]
]

class AuthenticExplosion:
    def __init__(self, x, y, big=False, color=None):
        self.x = x
        self.y = y
        self.big = big
        self.frame = 0
        self.max_frames = 24 if not big else 32
        self.life = self.max_frames
        self.base_color = color
        self.particles = []
        # Add extra small debris
        count = 16 if not big else 28
        for _ in range(count):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1.5, 5.0 if big else 3.5)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed
            c = random.choice([(255,200,50), (255,150,20), (200,200,200), (80,80,80)])
            self.particles.append(Particle(x, y, c, vx, vy, life=random.randint(12, 20), size=random.randint(2,4), kind='debris'))
    
    def update(self):
        self.life -= 1
        self.frame = int((1 - self.life / self.max_frames) * len(NES_EXPLOSION_FRAMES))
        self.frame = min(self.frame, len(NES_EXPLOSION_FRAMES)-1)
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        return self.life > 0
    
    def draw(self, screen):
        # Draw NES style expanding blocks for authentic look
        scale = 1.0
        if self.big:
            scale = 1.6
        # Life factor for size pulse
        life_factor = 1.0 + (1 - self.life/self.max_frames)*0.3
        
        frame_data = NES_EXPLOSION_FRAMES[min(self.frame, len(NES_EXPLOSION_FRAMES)-1)]
        for dx, dy, size, color in frame_data:
            sx = int(self.x + dx*scale*life_factor)
            sy = int(self.y + dy*scale*life_factor)
            s = int(size*scale*life_factor)
            # Use rectangle for authentic NES blocky look, not smooth circle
            if self.frame < 3:
                # Blocky NES style
                pygame.draw.rect(screen, color, (sx-s//2, sy-s//2, s, s))
                # Highlight top-left white for 3D
                pygame.draw.rect(screen, (255,255,255), (sx-s//2, sy-s//2, s//3, s//3))
            else:
                # Smoke becomes circles
                pygame.draw.circle(screen, color, (sx, sy), s)
        
        # Also draw small debris particles
        for p in self.particles:
            p.draw(screen)
        
        # Central flash for first few frames
        if self.frame < 2:
            flash_size = int((14 - self.frame*3)*scale)
            pygame.draw.circle(screen, (255,255,255), (int(self.x), int(self.y)), flash_size)

class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.explosions = []  # authentic explosions

    def add_explosion(self, x, y, color=None, count=20, big=False):
        # Use authentic Battle City explosion for big events (tank death, boss, base)
        # For small hits we still use old particles, but for explosions use authentic style
        is_big = big or count > 18 or (color and color[0] > 200 and color[1] < 150)
        # Heuristic: tank explosions are big
        if big or (color and isinstance(color, tuple) and color[0] < 100 and color[1] > 150): # green monster
            is_big = True
        use_authentic = True  # Always use authentic now, it's more impactful
        
        if use_authentic:
            self.explosions.append(AuthenticExplosion(x, y, big=is_big, color=color))
        else:
            # Fallback old particles for tiny hits
            for _ in range(count):
                c = random.choice([color if color else (255,200,0), (255,100,0), (255,255,100), (80,80,80)])
                self.particles.append(Particle(x, y, c, life=random.randint(20, 40)))

    def add_hit(self, x, y):
        # Small spark hit - keep particles but make them more like NES: small white squares
        for _ in range(6):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1, 2.5)
            self.particles.append(Particle(
                x + math.cos(angle)*3, y + math.sin(angle)*3,
                (220,220,220), vx=math.cos(angle)*speed*0.5, vy=math.sin(angle)*speed*0.5,
                life=10, size=2
            ))

    def add_spawn(self, x, y):
        for _ in range(12):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1, 3)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed
            self.particles.append(Particle(x, y, (255,255,255), vx, vy, life=25))

    def add_venom(self, x, y):
        for _ in range(14):
            c = random.choice([(80,220,80), (40,160,40), (120,255,120), (20,100,20)])
            self.particles.append(Particle(x, y, c, life=random.randint(18, 36), vx=random.uniform(-2.5,2.5), vy=random.uniform(-3,1)))
        for _ in range(6):
            self.particles.append(Particle(x+random.uniform(-4,4), y, (60,180,60), vx=random.uniform(-0.5,0.5), vy=random.uniform(0.5,1.5), life=random.randint(25,45)))

    def add_crush(self, x, y):
        for _ in range(16):
            c = random.choice([(210,56,24), (140,30,10), (180,180,180)])
            self.particles.append(Particle(x, y, c, life=random.randint(15,30)))

    def add_dust(self, x, y):
        for _ in range(4):
            self.particles.append(Particle(x, y, (150,130,100), vx=random.uniform(-1,1), vy=random.uniform(-1.5,-0.5), life=12, size=2))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]
        self.explosions = [e for e in self.explosions if e.update()]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)
        for e in self.explosions:
            e.draw(screen)
