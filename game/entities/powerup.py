import pygame
import random
from ..settings import *

class PowerUp:
    def __init__(self, x, y, type_name=None):
        self.x = x
        self.y = y
        self.type = type_name or random.choice(POWERUP_TYPES)
        self.alive = True
        self.rect = pygame.Rect(x - 16, y - 16, 32, 32)
        self.spawn_time = pygame.time.get_ticks()
        self.blink_timer = 0
        self.lifetime = 10000  # 10 sec

        self.colors = {
            'helmet': (80, 180, 255),
            'clock': (200, 200, 255),
            'shovel': (255, 220, 80),
            'star': (255, 255, 100),
            'grenade': (255, 60, 60),
            'tank': (80, 255, 80),
            'gun': (255, 80, 200),
            # new items
            'homing': (255, 140, 0),   # orange for tracking missile
            'spread': (160, 80, 255),  # purple for 8-way
            'rapid': (255, 50, 150),   # pink/red for rapid 3x attack
        }

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime:
            self.alive = False
        # blink when about to expire
        self.blink_timer += 1

    def draw(self, screen):
        if not self.alive:
            return
        # blinking
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime - 2000:
            if self.blink_timer % 20 < 10:
                return
        color = self.colors.get(self.type, COLOR_WHITE)
        # pulsing
        pulse = 2 * abs((self.blink_timer % 40) - 20) / 20
        size = int(28 + pulse*4)
        rect = pygame.Rect(0,0,size,size)
        rect.center = (self.x, self.y)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, COLOR_WHITE, rect, 2, border_radius=6)
        # icon letter
        font = pygame.font.Font(None, 22)
        icons = {
            'helmet': 'H',
            'clock': 'C',
            'shovel': 'S',
            'star': '*',
            'grenade': 'G',
            'tank': 'T',
            'gun': 'P',
            # new items
            'homing': 'M',  # missile
            'spread': '8',  # 8-way
            'rapid': 'R',   # rapid 3x attack
        }
        txt = font.render(icons.get(self.type, '?'), True, COLOR_BLACK)
        screen.blit(txt, txt.get_rect(center=(self.x, self.y)))

    def check_pickup(self, players):
        for p in players:
            if p.alive and p.rect.colliderect(self.rect):
                self.alive = False
                return p
        return None
