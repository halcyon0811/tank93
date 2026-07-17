import pygame
import random
import math
from ..settings import *

class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=30):
        self.x = x
        self.y = y
        self.vx = vx if vx is not None else random.uniform(-3, 3)
        self.vy = vy if vy is not None else random.uniform(-3, 3)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15  # gravity
        self.vx *= 0.98
        self.life -= 1
        return self.life > 0

    def draw(self, screen):
        alpha = self.life / self.max_life
        size = int(self.size * alpha)
        if size > 0:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add_explosion(self, x, y, color=(255, 200, 0), count=20):
        for _ in range(count):
            c = random.choice([color, (255,100,0), (255,255,100), (80,80,80)])
            self.particles.append(Particle(x, y, c, life=random.randint(20, 40)))

    def add_hit(self, x, y):
        for _ in range(8):
            self.particles.append(Particle(x, y, (200,200,200), life=15))

    def add_spawn(self, x, y):
        for _ in range(12):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(1, 3)
            vx = math.cos(angle)*speed
            vy = math.sin(angle)*speed
            self.particles.append(Particle(x, y, (255,255,255), vx, vy, life=25))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, screen):
        for p in self.particles:
            p.draw(screen)
