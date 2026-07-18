import pygame
import random
import math
import os
import pathlib
from ..settings import *

# Item icon loader using your downloaded assets - size similar to tank
ITEMS_DIR = pathlib.Path(__file__).parent.parent / "assets" / "items"

# Map your 7 classic icons to types (based on common Battle City icon order)
# Battle City classic icons (from NES): helmet, clock, shovel, star, grenade, tank, gun
# Your files battle_city_icon_1..7.png correspond to these - we'll auto-detect best guess by file existence
# User provided 7 classic + we create 5 new: homing, spread, rapid, shrink, giant

# Try to guess mapping: icon_1 helmet, 2 clock, 3 shovel, 4 star, 5 grenade, 6 tank, 7 gun
CLASSIC_ICON_MAP = {
    'helmet': 'battle_city_icon_1.png',
    'clock': 'battle_city_icon_2.png',
    'shovel': 'battle_city_icon_3.png',
    'star': 'battle_city_icon_4.png',
    'grenade': 'battle_city_icon_5.png',
    'tank': 'battle_city_icon_6.png',
    'gun': 'battle_city_icon_7.png',
}

NEW_ICON_MAP = {
    'homing': 'battle_city_icon_homing.png',
    'spread': 'battle_city_icon_spread.png',
    'rapid': 'battle_city_icon_rapid.png',
    'shrink': 'battle_city_icon_shrink.png',
    'giant': 'battle_city_icon_giant.png',
}

ALL_ICON_MAP = {**CLASSIC_ICON_MAP, **NEW_ICON_MAP}

# Cache for loaded images
_ICON_CACHE = {}

def load_item_icon(type_name, target_size=None):
    """Load icon for powerup type, scaled to tank size (32)"""
    if target_size is None:
        target_size = TANK_SIZE  # similar as tank size per user request
    
    cache_key = (type_name, target_size)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]
    
    # Try to load from file
    icon_filename = ALL_ICON_MAP.get(type_name)
    if icon_filename:
        icon_path = ITEMS_DIR / icon_filename
        if icon_path.exists():
            try:
                surf = pygame.image.load(str(icon_path))
                # For headless load, don't use convert_alpha before display exists
                if pygame.display.get_surface():
                    try:
                        surf = surf.convert_alpha()
                    except:
                        pass
                orig_w, orig_h = surf.get_size()
                scale = target_size / max(orig_w, orig_h) * 0.95
                new_w = int(orig_w * scale)
                new_h = int(orig_h * scale)
                try:
                    scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
                except:
                    scaled = pygame.transform.scale(surf, (new_w, new_h))
                final = pygame.Surface((target_size, target_size), pygame.SRCALPHA)
                final.fill((0,0,0,0))
                fx = (target_size - new_w)//2
                fy = (target_size - new_h)//2
                final.blit(scaled, (fx, fy))
                _ICON_CACHE[cache_key] = final
                return final
            except Exception as e:
                print(f"Failed to load icon {icon_path}: {e}")
    
    # Fallback: generate pixel art style icon matching Battle City style
    return generate_fallback_icon(type_name, target_size)

def generate_fallback_icon(type_name, size):
    """Generate fallback icon in same style: white border, dark bg, pixel art center"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0,0,0,0))
    # Draw Battle City style border (like original icons)
    # outer black, inner white 2px, dark bg
    inner = int(size*0.9)
    off = (size-inner)//2
    pygame.draw.rect(surf, (0,0,0,255), (off, off, inner, inner))
    pygame.draw.rect(surf, (255,255,255,255), (off+2, off+2, inner-4, inner-4), 2)
    pygame.draw.rect(surf, (5,25,35,255), (off+4, off+4, inner-8, inner-8))
    
    # Draw simple symbol based on type
    cx, cy = size//2, size//2
    if type_name == 'helmet':
        pygame.draw.circle(surf, (200,200,200), (cx, cy-2), 6, 1)
        pygame.draw.arc(surf, (220,220,220), (cx-5, cy-4, 10, 8), 0, 3.14, 1)
    elif type_name == 'clock':
        pygame.draw.circle(surf, (220,220,220), (cx, cy), 7, 1)
        pygame.draw.line(surf, (255,255,255), (cx, cy), (cx, cy-5), 1)
        pygame.draw.line(surf, (255,255,255), (cx, cy), (cx+4, cy), 1)
    elif type_name == 'shovel':
        pygame.draw.rect(surf, (180,180,180), (cx-1, cy-6, 2, 8))
        pygame.draw.polygon(surf, (200,200,200), [(cx-5, cy+2), (cx+5, cy+2), (cx+3, cy+6), (cx-3, cy+6)])
    elif type_name == 'star':
        pts = [(cx, cy-7), (cx-2, cy-2), (cx-7, cy-2), (cx-3, cy+1), (cx-4, cy+7), (cx, cy+3), (cx+4, cy+7), (cx+3, cy+1), (cx+7, cy-2), (cx+2, cy-2)]
        pygame.draw.polygon(surf, (255,255,180), pts)
    elif type_name == 'grenade':
        pygame.draw.circle(surf, (200,200,200), (cx, cy+2), 5)
    elif type_name == 'tank':
        pygame.draw.rect(surf, (200,200,200), (cx-6, cy-2, 12, 6))
    elif type_name == 'gun':
        pygame.draw.rect(surf, (200,200,200), (cx-1, cy-8, 2, 12))
    else:
        font = pygame.font.Font(None, size//2)
        txt = font.render(type_name[0].upper(), True, (255,255,255))
        surf.blit(txt, txt.get_rect(center=(cx, cy)))
    
    _ICON_CACHE[(type_name, size)] = surf
    return surf

class PowerUp:
    def __init__(self, x, y, type_name=None):
        self.x = x
        self.y = y
        self.type = type_name or random.choice(POWERUP_TYPES)
        self.alive = True
        # Size similar to tank size per user request (32)
        self.base_size = TANK_SIZE
        self.rect = pygame.Rect(x - self.base_size//2, y - self.base_size//2, self.base_size, self.base_size)
        self.spawn_time = pygame.time.get_ticks()
        self.blink_timer = 0
        self.lifetime = 10000
        self.rotation = 0
        self.bob_offset = random.uniform(0, 6.28)

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
        # Preload icon
        try:
            self.icon = load_item_icon(self.type, TANK_SIZE)
        except:
            self.icon = None

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.spawn_time > self.lifetime:
            self.alive = False
        self.blink_timer += 1
        self.rotation = (self.rotation + 1) % 360

    def draw(self, screen):
        if not self.alive:
            return
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime - 2000:
            if self.blink_timer % 20 < 10:
                return

        # Bobbing animation
        bob = math.sin(pygame.time.get_ticks() * 0.005 + self.bob_offset) * 3
        draw_x = self.x
        draw_y = self.y + bob
        
        # Pulsing glow
        pulse = 1.0 + 0.15 * abs(math.sin(self.blink_timer * 0.1))
        size = int(self.base_size * pulse)
        
        # Shadow
        shadow_rect = pygame.Rect(0,0,size+4,size+4)
        shadow_rect.center = (draw_x+2, draw_y+2)
        shadow_surf = pygame.Surface((size+4, size+4), pygame.SRCALPHA)
        shadow_surf.fill((0,0,0,60))
        screen.blit(shadow_surf, shadow_rect.topleft)
        
        # Glow behind icon (colored)
        col = self.colors.get(self.type, COLOR_WHITE)
        glow_size = size + 8
        glow_rect = pygame.Rect(0,0,glow_size, glow_size)
        glow_rect.center = (draw_x, draw_y)
        glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*col, 30), (0,0,glow_size,glow_size), border_radius=6)
        screen.blit(glow_surf, glow_rect.topleft)
        
        # Draw icon image (Battle City style) sized to tank
        if self.icon:
            try:
                # Scale with pulse
                icon_scaled = pygame.transform.smoothscale(self.icon, (size, size)) if pulse != 1.0 else self.icon
                icon_rect = icon_scaled.get_rect(center=(draw_x, draw_y))
                screen.blit(icon_scaled, icon_rect)
                
                # Shine effect on top
                shine = pygame.Surface((size, size//3), pygame.SRCALPHA)
                shine.fill((255,255,255,20))
                screen.blit(shine, (draw_x - size//2, draw_y - size//2))
            except:
                # Fallback rect
                rect = pygame.Rect(0,0,size,size)
                rect.center = (draw_x, draw_y)
                pygame.draw.rect(screen, col, rect, border_radius=4)
                pygame.draw.rect(screen, COLOR_WHITE, rect, 2, border_radius=4)
        else:
            rect = pygame.Rect(0,0,size,size)
            rect.center = (draw_x, draw_y)
            pygame.draw.rect(screen, col, rect, border_radius=4)
            pygame.draw.rect(screen, COLOR_WHITE, rect, 2, border_radius=4)

    def check_pickup(self, players):
        for p in players:
            if p.alive and p.rect.colliderect(self.rect):
                self.alive = False
                return p
        return None
