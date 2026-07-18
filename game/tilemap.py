"""Tilemap system - classic Battle City style with armor + brick durability + forest hiding + NES explosion"""
import pygame
import json
import random
from .settings import *

# Debug logging
try:
    from .logger_integration import safe_log_gameplay
    HAS_DEBUG = True
except:
    HAS_DEBUG = False
    def safe_log_gameplay(*a, **kw): pass

class TileMap:
    def __init__(self, level_data=None, is_mega=None):
        if is_mega is None:
            is_mega = MEGA_ENABLED
        self.is_mega = is_mega
        if is_mega:
            self.grid_w = MEGA_GRID_W
            self.grid_h = MEGA_GRID_H
            self.tile_size = MEGA_TILE_SIZE
            self.base_pos = MEGA_BASE_POS
            self.player_spawns = MEGA_PLAYER_SPAWN
            self.enemy_spawns = MEGA_ENEMY_SPAWNS
        else:
            self.grid_w = GRID_W
            self.grid_h = GRID_H
            self.tile_size = TILE_SIZE
            self.base_pos = BASE_POS
            self.player_spawns = PLAYER_SPAWN
            self.enemy_spawns = ENEMY_SPAWNS
        self.tiles = [[TILE_EMPTY for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        self.shovel_timer = 0
        self.brick_health = {}  # (gx,gy) -> hits taken

        if level_data:
            self.load_from_data(level_data)
        else:
            self.load_default()

    def load_from_data(self, data):
        if not data:
            return
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        if h == 13 and w == 13:
            gw, gh = self.grid_w, self.grid_h
            scale_x = gw // 13
            scale_y = gh // 13
            for by in range(13):
                for bx in range(13):
                    t = data[by][bx]
                    for dy in range(scale_y):
                        for dx in range(scale_x):
                            gx = bx*scale_x+dx
                            gy = by*scale_y+dy
                            if 0 <= gx < gw and 0 <= gy < gh:
                                self.tiles[gy][gx] = t
        elif h == 26 and w == 26:
            if self.grid_w == 26:
                for y in range(26):
                    for x in range(26):
                        self.tiles[y][x] = data[y][x]
            else:
                for y in range(26):
                    for x in range(26):
                        t = data[y][x]
                        for dy in range(2):
                            for dx in range(2):
                                gx = x*2+dx
                                gy = y*2+dy
                                if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                                    self.tiles[gy][gx] = t
        elif h == 52 and w == 52:
            for y in range(52):
                for x in range(52):
                    if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                        self.tiles[y][x] = data[y][x]
        else:
            for y in range(min(h, self.grid_h)):
                for x in range(min(w, self.grid_w)):
                    self.tiles[y][x] = data[y][x]

    def load_default(self):
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                self.tiles[y][x] = TILE_EMPTY
        self.build_base_walls(TILE_BRICK)

    def clear_area(self, gx, gy, w=4, h=4):
        bx, by = self.base_pos
        base_cells = [(bx, by), (bx+1, by), (bx, by+1), (bx+1, by+1)]
        for y in range(gy, gy+h):
            for x in range(gx, gx+w):
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    if (x, y) in base_cells:
                        continue
                    self.tiles[y][x] = TILE_EMPTY
                    self.brick_health.pop((x,y), None)

    def ensure_spawn_clear(self):
        for px, py in self.player_spawns:
            self.clear_area(px-1, py-1, 4, 4)
        for sx, sy in self.enemy_spawns:
            self.clear_area(sx, sy, 4, 3)
        bx, by = self.base_pos
        for y in range(by, by+2):
            for x in range(bx, bx+2):
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    self.tiles[y][x] = TILE_EMPTY

    def build_base_walls(self, tile_type, concrete_steel=False):
        bx, by = self.base_pos
        if self.is_mega:
            outer = [
                (bx-2, by-2), (bx-1, by-2), (bx, by-2), (bx+1, by-2), (bx+2, by-2), (bx+3, by-2),
                (bx-2, by-1), (bx+3, by-1),
                (bx-2, by), (bx+3, by),
                (bx-2, by+1), (bx+3, by+1),
                (bx-2, by+2), (bx-1, by+2), (bx, by+2), (bx+1, by+2), (bx+2, by+2), (bx+3, by+2),
            ]
            inner = [
                (bx-1, by-1), (bx, by-1), (bx+1, by-1), (bx+2, by-1),
                (bx-1, by), (bx+2, by),
                (bx-1, by+1), (bx+2, by+1),
            ]
            use_steel = concrete_steel or tile_type == TILE_STEEL
            wall_tile = TILE_STEEL if use_steel else TILE_BRICK
            for (x, y) in outer + inner:
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    self.tiles[y][x] = wall_tile
            openings = [
                (bx, by-2), (bx+1, by-2),
                (bx, by+3), (bx+1, by+3),
                (bx-2, by), (bx-2, by+1),
                (bx+3, by), (bx+3, by+1),
            ]
            for gx, gy in openings:
                if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                    self.tiles[gy][gx] = TILE_EMPTY
                    self.brick_health.pop((gx,gy), None)
        else:
            coords = [
                (bx-1, by-1), (bx, by-1), (bx+1, by-1), (bx+2, by-1),
                (bx-1, by), (bx-1, by+1),
                (bx+2, by), (bx+2, by+1),
            ]
            for (x, y) in coords:
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    self.tiles[y][x] = tile_type

    def get_tile_at_pixel(self, px, py):
        gx = int((px - PLAYFIELD_X) // self.tile_size)
        gy = int((py - PLAYFIELD_Y) // self.tile_size)
        if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
            return self.tiles[gy][gx], gx, gy
        return None, -1, -1

    def get_tiles_in_rect(self, rect):
        left = max(0, int((rect.left - PLAYFIELD_X) // self.tile_size))
        right = min(self.grid_w-1, int((rect.right - 1 - PLAYFIELD_X) // self.tile_size))
        top = max(0, int((rect.top - PLAYFIELD_Y) // self.tile_size))
        bottom = min(self.grid_h-1, int((rect.bottom - 1 - PLAYFIELD_Y) // self.tile_size))
        result = []
        for gy in range(top, bottom+1):
            for gx in range(left, right+1):
                t = self.tiles[gy][gx]
                if t != TILE_EMPTY and t != TILE_GRASS and t != TILE_ICE:
                    tile_rect = pygame.Rect(
                        PLAYFIELD_X + gx * self.tile_size,
                        PLAYFIELD_Y + gy * self.tile_size,
                        self.tile_size, self.tile_size
                    )
                    result.append((t, gx, gy, tile_rect))
        return result

    def is_blocking(self, gx, gy, for_bullet=False, bullet_power=1):
        if not (0 <= gx < self.grid_w and 0 <= gy < self.grid_h):
            return True
        t = self.tiles[gy][gx]
        if t == TILE_EMPTY or t == TILE_GRASS or t == TILE_ICE:
            return False
        if for_bullet:
            if t == TILE_BRICK:
                return True
            if t == TILE_STEEL:
                return bullet_power >= 2 or True
            if t == TILE_WATER:
                return False
        else:
            if t == TILE_BRICK or t == TILE_STEEL or t == TILE_WATER:
                return True
        return False

    def is_in_forest(self, px, py):
        """Check if world pixel position is inside forest - for hiding tanks"""
        gx = int((px - PLAYFIELD_X) // self.tile_size)
        gy = int((py - PLAYFIELD_Y) // self.tile_size)
        if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
            return self.tiles[gy][gx] == TILE_GRASS
        return False

    def destroy_tile(self, gx, gy, bullet_power=1, bullet_dir=None, bullet_type='normal'):
        """All weapons destroy bricks with different hit counts"""
        if not (0 <= gx < self.grid_w and 0 <= gy < self.grid_h):
            return False
        
        t = self.tiles[gy][gx]
        if t == TILE_STEEL:
            if bullet_power >= 2:
                self.tiles[gy][gx] = TILE_EMPTY
                self.brick_health.pop((gx,gy), None)
                return True
            return False
        
        if t != TILE_BRICK:
            return False
        
        hits_needed = BRICK_HITS_NEEDED.get(bullet_type, 2)
        if bullet_power >= 2:
            hits_needed = max(1, hits_needed - 1)
        
        key = (gx, gy)
        current_hits = self.brick_health.get(key, 0) + 1
        max_needed = hits_needed
        
        if bullet_type == 'homing':
            import random as _rnd2
            max_needed = _rnd2.choice([3, 4])
        
        if current_hits >= max_needed:
            self.tiles[gy][gx] = TILE_EMPTY
            self.brick_health.pop(key, None)
            if HAS_DEBUG:
                try:
                    safe_log_gameplay("BRICK_DESTROY", data={"x": gx, "y": gy, "hits": current_hits, "needed": max_needed, "type": bullet_type, "power": bullet_power})
                except:
                    pass
            return True
        else:
            self.brick_health[key] = current_hits
            return False

    def update(self, dt):
        if self.shovel_timer > 0:
            self.shovel_timer -= 1
            if self.shovel_timer <= 0:
                self.build_base_walls(TILE_BRICK)

    def activate_shovel(self):
        self.build_base_walls(TILE_STEEL)
        self.shovel_timer = POWERUP_DURATION['shovel']

    def draw(self, screen):
        pf_rect = pygame.Rect(PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_W, PLAYFIELD_H)
        pygame.draw.rect(screen, COLOR_PLAYFIELD_BG, pf_rect)
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                t = self.tiles[y][x]
                if t == TILE_EMPTY:
                    continue
                rx = PLAYFIELD_X + x * self.tile_size
                ry = PLAYFIELD_Y + y * self.tile_size
                if t == TILE_BRICK:
                    self.draw_brick(screen, rx, ry, gx=x, gy=y)
                elif t == TILE_STEEL:
                    self.draw_steel(screen, rx, ry)
                elif t == TILE_WATER:
                    self.draw_water(screen, rx, ry)

    def draw_overlay(self, screen):
        # Forest overlay - now FULLY OPAQUE to completely hide tanks
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                t = self.tiles[y][x]
                rx = PLAYFIELD_X + x * self.tile_size
                ry = PLAYFIELD_Y + y * self.tile_size
                if t == TILE_GRASS:
                    self.draw_grass(screen, rx, ry, dense=True)
                elif t == TILE_ICE:
                    self.draw_ice(screen, rx, ry)

    def draw_brick(self, screen, x, y, gx=None, gy=None):
        ts = self.tile_size
        if gx is None or gy is None:
            gx = int((x - PLAYFIELD_X) // ts)
            gy = int((y - PLAYFIELD_Y) // ts)
        s = pygame.Surface((16,16))
        BR = (210, 56, 24)
        BD = (100, 22, 10)
        BL = (240, 90, 50)
        BM = (140, 30, 12)
        s.fill(BD)
        brick_w = 7
        brick_h = 6
        positions = [(1, 1), (9, 1), (2, 9), (10, 9)]
        for bx, by in positions:
            pygame.draw.rect(s, BR, (bx, by, brick_w, brick_h))
            pygame.draw.line(s, BL, (bx, by), (bx+brick_w-1, by), 1)
        pygame.draw.line(s, BM, (8, 1), (8, 7), 1)
        pygame.draw.line(s, BM, (1, 8), (15, 8), 1)
        
        hits = self.brick_health.get((gx, gy), 0) if hasattr(self, 'brick_health') else 0
        if hits > 0:
            for _ in range(hits):
                x1 = random.randint(2, 12)
                y1 = random.randint(2, 12)
                x2 = x1 + random.randint(-4, 4)
                y2 = y1 + random.randint(-4, 4)
                pygame.draw.line(s, (50, 20, 10), (x1, y1), (x2, y2), 1)
            dark = pygame.Surface((16,16), pygame.SRCALPHA)
            dark.fill((0, 0, 0, hits * 40))
            s.blit(dark, (0,0))

        scaled = pygame.transform.scale(s, (ts-2, ts-2))
        screen.blit(scaled, (x+1, y+1))

    def draw_steel(self, screen, x, y):
        s = pygame.Surface((8,8))
        S_BG = (210, 210, 210)
        S_DARK = (130, 130, 130)
        S_LIGHT = (255, 255, 255)
        S_RIVET_D = (90, 90, 90)
        S_RIVET_L = (230, 230, 230)
        s.fill(S_DARK)
        pygame.draw.rect(s, S_BG, (1,1,6,6))
        pygame.draw.rect(s, S_LIGHT, (2,2,4,4))
        s.set_at((6,6), S_DARK)
        s.set_at((1,6), S_DARK)
        s.set_at((6,1), S_DARK)
        s.set_at((2,2), S_RIVET_D)
        s.set_at((1,1), S_RIVET_L)
        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

    def draw_water(self, screen, x, y):
        s = pygame.Surface((8,8))
        BLUE = (28, 90, 240)
        WHITE = (235, 245, 255)
        s.fill(BLUE)
        t = pygame.time.get_ticks()
        phase = (t // 200) % 2
        if phase == 0:
            dots = [(1,1),(3,2),(6,1),(2,4),(5,5),(1,6)]
        else:
            dots = [(2,1),(5,2),(1,3),(4,4),(6,6),(2,7)]
        for dx, dy in dots:
            if (dx+dy) % 2 == 0:
                s.set_at((dx, dy), WHITE)
                if dx+1 < 8:
                    s.set_at((dx+1, dy), WHITE)
            else:
                s.set_at((dx, dy), WHITE)
        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

    def draw_grass(self, screen, x, y, dense=False):
        ts = self.tile_size
        # Dense forest for hiding - fully opaque
        s = pygame.Surface((16,16), pygame.SRCALPHA)
        BASE = (45, 120, 15)
        DARK = (20, 70, 8)
        DARK2 = (30, 90, 12)
        LIGHT = (110, 190, 60)
        MID = (70, 150, 25)
        LIGHT2 = (140, 210, 80)
        s.fill(BASE)
        # Use position-seeded random for consistent but dense forest
        rnd = random.Random(x*1000 + y)
        for _ in range(16 if dense else 12):
            rx = rnd.randint(0,15)
            ry = rnd.randint(0,15)
            r = rnd.randint(2,4)
            pygame.draw.circle(s, rnd.choice([DARK, DARK2]), (rx, ry), r)
        for _ in range(18 if dense else 14):
            rx = rnd.randint(0,15)
            ry = rnd.randint(0,15)
            r = rnd.randint(2,3)
            pygame.draw.circle(s, rnd.choice([BASE, MID]), (rx, ry), r)
        for _ in range(10 if dense else 8):
            rx = rnd.randint(2,13)
            ry = rnd.randint(2,13)
            r = rnd.randint(1,2)
            pygame.draw.circle(s, rnd.choice([LIGHT, LIGHT2]), (rx, ry), r)
        pygame.draw.circle(s, BASE, (8,8), 6)
        scaled = pygame.transform.scale(s, (ts, ts))
        screen.blit(scaled, (x, y))

    def draw_ice(self, screen, x, y):
        s = pygame.Surface((8,8))
        BASE = (190, 190, 190)
        DARK = (130, 130, 135)
        LIGHT = (230, 230, 235)
        VERY_LIGHT = (220, 220, 220)
        s.fill(BASE)
        for px in range(8):
            for py in range(8):
                v = (px + py) % 4
                if v == 0:
                    s.set_at((px, py), DARK)
                elif v == 2:
                    s.set_at((px, py), LIGHT)
        s.set_at((1,1), VERY_LIGHT)
        s.set_at((5,2), VERY_LIGHT)
        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

# ---- Classic 35 NES Maps ----
try:
    from .levels.battle_city import LEVELS_13 as _ORIG_13, LEVELS_26 as _ORIG_26, ENEMY_QUEUES, BOTS_RAW, STAGE_COUNT
    LEVELS_13_ORIGINAL = _ORIG_13
    LEVELS_26_ORIGINAL = _ORIG_26
    LEVELS = _ORIG_26
    ENEMY_QUEUES_ORIGINAL = ENEMY_QUEUES
    BOTS_RAW_ORIGINAL = BOTS_RAW
    ORIGINAL_STAGE_COUNT = STAGE_COUNT
except ImportError as e:
    print(f"Warning: Could not load original 35 maps, using 5 handcrafted fallback: {e}")
    ORIGINAL_STAGE_COUNT = 5
    ENEMY_QUEUES_ORIGINAL = []
    BOTS_RAW_ORIGINAL = []
    LEVELS_13_ORIGINAL = []
    LEVELS_26_ORIGINAL = []
    LEVELS = [
        [
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,1,0,1,1,0,1,1,0,1,1,0],
            [0,1,1,0,1,1,0,1,1,0,1,1,0],
            [0,1,1,0,1,1,0,1,1,0,1,1,0],
            [0,1,1,0,1,1,2,2,1,0,1,1,0],
            [0,1,1,0,1,1,0,0,0,0,1,1,0],
            [0,1,1,0,1,1,0,1,1,0,1,1,0],
            [0,0,0,0,0,0,0,1,1,0,0,0,0],
            [1,1,0,0,0,3,3,3,0,0,0,1,1],
            [2,2,0,0,0,3,3,3,0,0,0,2,2],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,1,0,1,1,0,1,1,0,1,1,0],
            [0,0,0,0,1,1,0,1,1,0,0,0,0],
        ],
    ]
