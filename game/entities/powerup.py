import pygame
import random
import math
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
            'homing': (255, 140, 0),
            'spread': (160, 80, 255),
            'rapid': (255, 50, 150),
            'shrink': (80, 220, 255),
            'giant': (255, 80, 80),
        }

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime:
            self.alive = False
        self.blink_timer += 1

    # ---------- Icon draw helpers ----------
    def _draw_icon_helmet(self, surf, cx, cy, col):
        # Shield bubble + helmet dome
        pygame.draw.circle(surf, (200, 230, 255), (cx, cy-2), 8, 2)
        pygame.draw.arc(surf, col, (cx-7, cy-6, 14, 10), 0, math.pi, 2)
        pygame.draw.rect(surf, col, (cx-8, cy-1, 16, 3), border_radius=2)

    def _draw_icon_clock(self, surf, cx, cy, col):
        # Clock face
        pygame.draw.circle(surf, COLOR_WHITE, (cx, cy), 8, 2)
        pygame.draw.circle(surf, col, (cx, cy), 2)
        # hands at 10:10 frozen
        pygame.draw.line(surf, COLOR_WHITE, (cx, cy), (cx-3, cy-5), 2)
        pygame.draw.line(surf, COLOR_WHITE, (cx, cy), (cx+4, cy-2), 2)
        # freeze ticks
        for a in range(0, 360, 90):
            rx = cx + 10*math.cos(math.radians(a))
            ry = cy + 10*math.sin(math.radians(a))
            pygame.draw.circle(surf, (150, 200, 255), (int(rx), int(ry)), 1)

    def _draw_icon_shovel(self, surf, cx, cy, col):
        # Shovel
        pygame.draw.rect(surf, (150, 100, 30), (cx-2, cy-8, 4, 12), border_radius=1)
        pygame.draw.polygon(surf, col, [(cx-7, cy+4), (cx+7, cy+4), (cx+5, cy+10), (cx-5, cy+10)])
        pygame.draw.rect(surf, (80, 60, 30), (cx-8, cy-6, 16, 3))

    def _draw_icon_star(self, surf, cx, cy, col):
        # 5-point star
        pts = []
        for i in range(10):
            r = 10 if i % 2 == 0 else 5
            ang = math.radians(i * 36 - 90)
            pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.polygon(surf, COLOR_WHITE, pts, 2)
        # sparkle
        pygame.draw.circle(surf, COLOR_WHITE, (cx+3, cy-3), 2)

    def _draw_icon_grenade(self, surf, cx, cy, col):
        # Grenade body
        pygame.draw.circle(surf, col, (cx, cy+3), 7)
        pygame.draw.rect(surf, (100, 100, 100), (cx-4, cy-6, 8, 6))
        pygame.draw.circle(surf, (80, 80, 80), (cx+3, cy-7), 2)
        # fuse spark
        for _ in range(3):
            sx = cx+3 + random.randint(-1,1)
            sy = cy-9 + random.randint(-1,1)
            pygame.draw.circle(surf, (255, 220, 0), (sx, sy), 1)

    def _draw_icon_tank(self, surf, cx, cy, col):
        # Mini tank with + sign (extra life)
        pygame.draw.rect(surf, col, (cx-8, cy-2, 16, 8), border_radius=2)
        pygame.draw.rect(surf, (40,40,40), (cx-2, cy-8, 4, 8))
        pygame.draw.circle(surf, COLOR_WHITE, (cx+6, cy-6), 5)
        pygame.draw.line(surf, (0,180,0), (cx+3, cy-6), (cx+9, cy-6), 2)
        pygame.draw.line(surf, (0,180,0), (cx+6, cy-9), (cx+6, cy-3), 2)

    def _draw_icon_gun(self, surf, cx, cy, col):
        # Double-barrel / power gun
        pygame.draw.rect(surf, (60,60,60), (cx-2, cy-10, 4, 14))
        pygame.draw.rect(surf, col, (cx-6, cy-12, 3, 16))
        pygame.draw.rect(surf, col, (cx+3, cy-12, 3, 16))
        pygame.draw.circle(surf, COLOR_YELLOW, (cx-5, cy-13), 2)
        pygame.draw.circle(surf, COLOR_YELLOW, (cx+5, cy-13), 2)
        # power rings
        pygame.draw.circle(surf, COLOR_WHITE, (cx, cy+2), 6, 1)

    def _draw_icon_homing(self, surf, cx, cy, col):
        # Homing missile with trail + target lock
        pygame.draw.circle(surf, col, (cx-4, cy), 4)
        pygame.draw.circle(surf, (255, 220, 0), (cx-4, cy), 2)
        pygame.draw.line(surf, (255, 100, 0), (cx-4, cy), (cx-10, cy+2), 2)
        # target reticle
        pygame.draw.circle(surf, COLOR_WHITE, (cx+6, cy-2), 5, 1)
        pygame.draw.line(surf, COLOR_WHITE, (cx+6-2, cy-2), (cx+6+2, cy-2), 1)
        pygame.draw.line(surf, COLOR_WHITE, (cx+6, cy-2-2), (cx+6, cy-2+2), 1)
        # dotted line
        for i in range(2):
            pygame.draw.circle(surf, (255,140,0), (cx-1+i*4, cy), 1)

    def _draw_icon_spread(self, surf, cx, cy, col):
        # Center + 8 arrows outward
        pygame.draw.circle(surf, COLOR_WHITE, (cx, cy), 3)
        pygame.draw.circle(surf, col, (cx, cy), 2)
        for ang in range(0, 360, 45):
            rx = math.cos(math.radians(ang)) * 9
            ry = math.sin(math.radians(ang)) * 9
            pygame.draw.line(surf, col, (cx, cy), (cx+rx, cy+ry), 2)
            pygame.draw.circle(surf, col, (cx+rx, cy+ry), 2)

    def _draw_icon_rapid(self, surf, cx, cy, col):
        # Three bullets stacked with speed lines
        for i in range(3):
            bx = cx - 6 + i*6
            pygame.draw.circle(surf, col, (bx, cy), 3)
            pygame.draw.circle(surf, COLOR_WHITE, (bx, cy), 1)
        # speed motion lines
        pygame.draw.line(surf, COLOR_WHITE, (cx-10, cy-6), (cx-4, cy-6), 1)
        pygame.draw.line(surf, COLOR_WHITE, (cx-8, cy+6), (cx-2, cy+6), 1)

    def _draw_icon_shrink(self, surf, cx, cy, col):
        # Small tank inside big dashed outline + down arrow
        # Big dashed outer
        pygame.draw.rect(surf, (100, 180, 220), (cx-10, cy-8, 20, 12), 1, border_radius=2)
        # Small inner solid
        pygame.draw.rect(surf, col, (cx-4, cy-3, 8, 5), border_radius=2)
        pygame.draw.rect(surf, (30,30,30), (cx-1, cy-7, 2, 5))
        # down / shrink arrows
        pygame.draw.polygon(surf, COLOR_WHITE, [(cx+8, cy-6), (cx+11, cy-6), (cx+9.5, cy-2)])
        pygame.draw.polygon(surf, COLOR_WHITE, [(cx-8, cy+6), (cx-11, cy+6), (cx-9.5, cy+2)])
        # speed streaks
        pygame.draw.line(surf, (150, 220, 255), (cx-8, cy-9), (cx-2, cy-9), 1)

    def _draw_icon_giant(self, surf, cx, cy, col):
        # Giant tank stepping on brick
        # Brick below
        pygame.draw.rect(surf, (160, 60, 30), (cx-8, cy+6, 16, 6))
        pygame.draw.line(surf, (100,30,10), (cx, cy+6), (cx, cy+12), 1)
        # Giant tank above
        pygame.draw.rect(surf, col, (cx-9, cy-8, 18, 10), border_radius=3)
        pygame.draw.rect(surf, (40,40,40), (cx-2, cy-14, 4, 8))
        pygame.draw.rect(surf, (20,20,20), (cx-11, cy+1, 5, 5), border_radius=1)
        pygame.draw.rect(surf, (20,20,20), (cx+6, cy+1, 5, 5), border_radius=1)
        # Crack on brick
        pygame.draw.line(surf, COLOR_WHITE, (cx-4, cy+8), (cx+2, cy+10), 1)

    def draw(self, screen):
        if not self.alive:
            return
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime - 2000:
            if self.blink_timer % 20 < 10:
                return
        color = self.colors.get(self.type, COLOR_WHITE)
        pulse = 2 * abs((self.blink_timer % 40) - 20) / 20
        size = int(32 + pulse*6)
        rect = pygame.Rect(0,0,size,size)
        rect.center = (self.x, self.y)
        # shadow
        shadow = rect.inflate(4,4)
        pygame.draw.rect(screen, (0,0,0,120), shadow, border_radius=8)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, COLOR_WHITE, rect, 2, border_radius=8)
        # glow pulse
        if pulse > 0.8:
            glow = rect.inflate(8,8)
            pygame.draw.rect(screen, (*color, 60), glow, 1, border_radius=10)

        # draw icon centered
        try:
            draw_func = getattr(self, f"_draw_icon_{self.type}", None)
            if draw_func:
                draw_func(screen, self.x, self.y, color)
            else:
                font = pygame.font.Font(None, 20)
                txt = font.render("?", True, COLOR_BLACK)
                screen.blit(txt, txt.get_rect(center=(self.x, self.y)))
        except Exception as e:
            # fallback: just color block
            pass

    def check_pickup(self, players):
        for p in players:
            if p.alive and p.rect.colliderect(self.rect):
                self.alive = False
                return p
        return None
