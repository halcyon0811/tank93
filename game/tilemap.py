"""Tilemap system - classic Battle City style 26x26 small tiles"""
import pygame
import json
import random
from .settings import *

class TileMap:
    def __init__(self, level_data=None):
        # 26x26 grid of tile types
        self.grid_w = GRID_W
        self.grid_h = GRID_H
        self.tiles = [[TILE_EMPTY for _ in range(self.grid_w)] for _ in range(self.grid_h)]
        self.shovel_timer = 0
        self.shovel_original = None

        if level_data:
            self.load_from_data(level_data)
        else:
            self.load_default()

    def load_from_data(self, data):
        """data can be 13x13 big tiles or 26x26 small tiles"""
        if len(data) == 13 and len(data[0]) == 13:
            # convert big to small
            for by in range(13):
                for bx in range(13):
                    t = data[by][bx]
                    # place 2x2
                    for dy in range(2):
                        for dx in range(2):
                            self.tiles[by*2+dy][bx*2+dx] = t
        elif len(data) == 26:
            for y in range(26):
                for x in range(26):
                    self.tiles[y][x] = data[y][x]

    def load_default(self):
        # simple default with border base protection
        # Base at 12,24 (2x2 eagle) surrounded by brick
        for y in range(GRID_H):
            for x in range(GRID_W):
                self.tiles[y][x] = TILE_EMPTY
        # add some walls
        # base walls
        bx, by = BASE_POS
        walls = [
            (bx-1, by-1, bx+2, by),   # top
            (bx-1, by, bx-1, by+2), # left
            (bx+2, by, bx+2, by+2), # right
        ]
        # will fill later in a proper method
        self.build_base_walls(TILE_BRICK)

    def clear_area(self, gx, gy, w=4, h=4):
        """Clear tiles around (gx,gy) to make spawn safe, centered"""
        # gx,gy is top-left small tile, clear w x h area
        for y in range(gy, gy+h):
            for x in range(gx, gx+w):
                if 0 <= x < GRID_W and 0 <= y < GRID_H:
                    # don't clear the base eagle itself (12,24) 2x2
                    if (x, y) in [(12,24),(13,24),(12,25),(13,25)]:
                        continue
                    self.tiles[y][x] = TILE_EMPTY

    def ensure_spawn_clear(self):
        # Clear player spawns (4x4 area)
        for px, py in PLAYER_SPAWN:
            self.clear_area(px-1, py-1, 4, 4)
        # Clear enemy spawns
        for sx, sy in ENEMY_SPAWNS:
            self.clear_area(sx, sy, 4, 3)
        # Clear base area slightly (base itself should remain empty for eagle, but we will place walls after)
        # Ensure base 2x2 is empty
        bx, by = BASE_POS
        for y in range(by, by+2):
            for x in range(bx, bx+2):
                if 0 <= x < GRID_W and 0 <= y < GRID_H:
                    self.tiles[y][x] = TILE_EMPTY

    def build_base_walls(self, tile_type):
        bx, by = BASE_POS
        # 2x2 base occupies (12,24),(13,24),(12,25),(13,25)
        # Wall around it: from (11,23) to (14,25)
        coords = [
            (bx-1, by-1), (bx, by-1), (bx+1, by-1), (bx+2, by-1),
            (bx-1, by), (bx-1, by+1),
            (bx+2, by), (bx+2, by+1),
        ]
        for (x, y) in coords:
            if 0 <= x < GRID_W and 0 <= y < GRID_H:
                self.tiles[y][x] = tile_type

    def get_tile_at_pixel(self, px, py):
        gx = int((px - PLAYFIELD_X) // TILE_SIZE)
        gy = int((py - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            return self.tiles[gy][gx], gx, gy
        return None, -1, -1

    def get_tiles_in_rect(self, rect):
        """rect in playfield pixel coords, return list of (tile_type, gx, gy, tile_rect)"""
        left = max(0, int((rect.left - PLAYFIELD_X) // TILE_SIZE))
        right = min(GRID_W-1, int((rect.right - 1 - PLAYFIELD_X) // TILE_SIZE))
        top = max(0, int((rect.top - PLAYFIELD_Y) // TILE_SIZE))
        bottom = min(GRID_H-1, int((rect.bottom - 1 - PLAYFIELD_Y) // TILE_SIZE))
        result = []
        for gy in range(top, bottom+1):
            for gx in range(left, right+1):
                t = self.tiles[gy][gx]
                if t != TILE_EMPTY and t != TILE_GRASS and t != TILE_ICE:
                    tile_rect = pygame.Rect(
                        PLAYFIELD_X + gx * TILE_SIZE,
                        PLAYFIELD_Y + gy * TILE_SIZE,
                        TILE_SIZE, TILE_SIZE
                    )
                    result.append((t, gx, gy, tile_rect))
        return result

    def is_blocking(self, gx, gy, for_bullet=False, bullet_power=1):
        if not (0 <= gx < GRID_W and 0 <= gy < GRID_H):
            return True
        t = self.tiles[gy][gx]
        if t == TILE_EMPTY or t == TILE_GRASS or t == TILE_ICE:
            return False
        if for_bullet:
            # bullets can pass grass, ice
            if t == TILE_BRICK:
                return True
            if t == TILE_STEEL:
                return bullet_power >= 2 or True # steel blocks unless high power, but still counts as hit
            if t == TILE_WATER:
                return False
        else:
            # tank movement
            if t == TILE_BRICK or t == TILE_STEEL or t == TILE_WATER:
                return True
        return False

    def destroy_tile(self, gx, gy, bullet_power=1):
        if not (0 <= gx < GRID_W and 0 <= gy < GRID_H):
            return False
        t = self.tiles[gy][gx]
        if t == TILE_BRICK:
            self.tiles[gy][gx] = TILE_EMPTY
            return True
        if t == TILE_STEEL and bullet_power >= 2:
            self.tiles[gy][gx] = TILE_EMPTY
            return True
        return False

    def update(self, dt):
        if self.shovel_timer > 0:
            self.shovel_timer -= 1
            if self.shovel_timer <= 0:
                # revert to brick
                self.build_base_walls(TILE_BRICK)

    def activate_shovel(self):
        # save original around base then build steel
        self.build_base_walls(TILE_STEEL)
        self.shovel_timer = POWERUP_DURATION['shovel']

    def draw(self, screen):
        # draw playfield background
        pf_rect = pygame.Rect(PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_W, PLAYFIELD_H)
        pygame.draw.rect(screen, COLOR_PLAYFIELD_BG, pf_rect)
        # draw tiles
        for y in range(GRID_H):
            for x in range(GRID_W):
                t = self.tiles[y][x]
                if t == TILE_EMPTY:
                    continue
                rx = PLAYFIELD_X + x * TILE_SIZE
                ry = PLAYFIELD_Y + y * TILE_SIZE
                if t == TILE_BRICK:
                    self.draw_brick(screen, rx, ry)
                elif t == TILE_STEEL:
                    self.draw_steel(screen, rx, ry)
                elif t == TILE_WATER:
                    self.draw_water(screen, rx, ry)
                # grass and ice drawn later overlay (after tanks)

    def draw_overlay(self, screen):
        for y in range(GRID_H):
            for x in range(GRID_W):
                t = self.tiles[y][x]
                rx = PLAYFIELD_X + x * TILE_SIZE
                ry = PLAYFIELD_Y + y * TILE_SIZE
                if t == TILE_GRASS:
                    self.draw_grass(screen, rx, ry)
                elif t == TILE_ICE:
                    self.draw_ice(screen, rx, ry)

    # Modernized pixel art tile renderers
    def draw_brick(self, screen, x, y):
        pygame.draw.rect(screen, COLOR_BRICK, (x, y, TILE_SIZE, TILE_SIZE))
        # brick pattern
        pygame.draw.rect(screen, COLOR_BRICK_DARK, (x, y, TILE_SIZE, TILE_SIZE), 2)
        pygame.draw.line(screen, COLOR_BRICK_LIGHT, (x, y+TILE_SIZE//2), (x+TILE_SIZE, y+TILE_SIZE//2), 2)
        pygame.draw.line(screen, COLOR_BRICK_DARK, (x+TILE_SIZE//2, y), (x+TILE_SIZE//2, y+TILE_SIZE//2), 1)
        pygame.draw.line(screen, COLOR_BRICK_DARK, (x+TILE_SIZE//4, y+TILE_SIZE//2), (x+TILE_SIZE//4, y+TILE_SIZE), 1)
        pygame.draw.line(screen, COLOR_BRICK_DARK, (x+3*TILE_SIZE//4, y+TILE_SIZE//2), (x+3*TILE_SIZE//4, y+TILE_SIZE), 1)

    def draw_steel(self, screen, x, y):
        pygame.draw.rect(screen, COLOR_STEEL, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(screen, COLOR_STEEL_DARK, (x, y, TILE_SIZE, TILE_SIZE), 2)
        # diagonal highlight
        pygame.draw.line(screen, COLOR_STEEL_LIGHT, (x+2, y+2), (x+TILE_SIZE-2, y+2), 2)
        pygame.draw.line(screen, COLOR_STEEL_LIGHT, (x+2, y+2), (x+2, y+TILE_SIZE-2), 2)
        # rivets
        pygame.draw.circle(screen, COLOR_STEEL_DARK, (x+5, y+5), 2)
        pygame.draw.circle(screen, COLOR_STEEL_DARK, (x+TILE_SIZE-5, y+5), 2)
        pygame.draw.circle(screen, COLOR_STEEL_DARK, (x+5, y+TILE_SIZE-5), 2)
        pygame.draw.circle(screen, COLOR_STEEL_DARK, (x+TILE_SIZE-5, y+TILE_SIZE-5), 2)

    def draw_water(self, screen, x, y):
        # animated water using time
        t = pygame.time.get_ticks()
        offset = (t // 200) % 4
        pygame.draw.rect(screen, COLOR_WATER, (x, y, TILE_SIZE, TILE_SIZE))
        # wave lines
        c = (70, 140, 255)
        for i in range(0, TILE_SIZE, 6):
            pygame.draw.line(screen, c, (x, y+i+offset), (x+TILE_SIZE, y+i+offset), 1)

    def draw_grass(self, screen, x, y):
        pygame.draw.rect(screen, COLOR_GRASS, (x, y, TILE_SIZE, TILE_SIZE))
        # leaves
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (x+2, y+4, 4, 8))
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (x+10, y+2, 3, 10))
        pygame.draw.rect(screen, COLOR_GRASS_DARK, (x+18, y+6, 4, 8))
        pygame.draw.circle(screen, (50, 180, 50), (x+12, y+12), 5)

    def draw_ice(self, screen, x, y):
        pygame.draw.rect(screen, COLOR_ICE, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(screen, (200, 230, 255), (x, y, TILE_SIZE, TILE_SIZE), 1)
        # shine
        pygame.draw.line(screen, COLOR_WHITE, (x+4, y+4), (x+10, y+8), 2)

# Predefined levels - 13x13 big tiles converted
LEVELS = [
    # Level 1 - classic
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
    # Level 2 - more water
    [
        [0,0,1,0,0,0,0,0,0,0,1,0,0],
        [0,0,1,0,2,2,0,2,2,0,1,0,0],
        [0,0,1,0,2,2,3,2,2,0,1,0,0],
        [0,0,0,0,0,0,3,0,0,0,0,0,0],
        [0,0,0,0,0,0,3,0,0,0,0,0,0],
        [1,1,1,0,0,0,0,0,0,0,1,1,1],
        [0,0,0,0,0,2,2,2,0,0,0,0,0],
        [3,3,3,0,0,2,0,2,0,0,3,3,3],
        [3,3,3,0,0,0,0,0,0,0,3,3,3],
        [0,0,0,0,1,1,0,1,1,0,0,0,0],
        [0,1,1,1,1,0,0,0,1,1,1,1,0],
        [0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,1,1,0,1,1,1,0,1,1,0,0],
    ],
    # Level 3 - forest maze
    [
        [0,0,0,1,1,0,0,0,1,1,0,0,0],
        [0,4,4,1,1,0,2,0,1,1,4,4,0],
        [0,4,4,0,0,0,2,0,0,0,4,4,0],
        [1,1,0,0,4,4,0,4,4,0,0,1,1],
        [1,1,0,0,4,4,0,4,4,0,0,1,1],
        [0,0,0,0,0,0,0,0,0,0,0,0,0],
        [0,0,2,2,0,1,1,1,0,2,2,0,0],
        [0,0,2,2,0,1,3,1,0,2,2,0,0],
        [0,0,0,0,0,1,3,1,0,0,0,0,0],
        [4,4,0,0,0,0,3,0,0,0,0,4,4],
        [4,4,0,1,1,0,0,0,1,1,0,4,4],
        [0,0,0,1,1,0,0,0,1,1,0,0,0],
        [0,0,0,0,0,0,1,0,0,0,0,0,0],
    ],
    # Level 4 - steel fortress
    [
        [0,1,0,2,0,0,0,0,0,2,0,1,0],
        [0,1,0,2,0,1,1,1,0,2,0,1,0],
        [0,0,0,0,0,1,0,1,0,0,0,0,0],
        [2,2,0,0,0,1,0,1,0,0,0,2,2],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,0,0,1,0,2,0,2,0,1,0,0,0],
        [0,0,0,1,0,0,0,0,0,1,0,0,0],
        [0,1,0,1,0,0,3,0,0,1,0,1,0],
        [0,1,0,0,0,3,3,3,0,0,0,1,0],
        [0,0,0,0,3,3,0,3,3,0,0,0,0],
        [1,1,0,0,0,0,0,0,0,0,0,1,1],
        [0,0,0,1,1,0,5,0,1,1,0,0,0],
        [0,0,0,0,0,1,1,1,0,0,0,0,0],
    ],
    # Level 5 - final chaos (ice + water)
    [
        [0,0,2,0,3,3,0,3,3,0,2,0,0],
        [1,0,2,0,3,3,0,3,3,0,2,0,1],
        [1,0,0,0,0,0,0,0,0,0,0,0,1],
        [0,0,0,5,5,0,0,0,5,5,0,0,0],
        [0,2,0,5,5,0,1,0,5,5,0,2,0],
        [0,2,0,0,0,0,1,0,0,0,0,2,0],
        [3,3,0,0,1,1,1,1,1,0,0,3,3],
        [3,3,0,0,1,0,0,0,1,0,0,3,3],
        [0,0,0,0,1,0,4,0,1,0,0,0,0],
        [0,1,1,0,0,4,4,4,0,0,1,1,0],
        [0,0,0,0,5,5,0,5,5,0,0,0,0],
        [0,1,0,5,5,0,0,0,5,5,0,1,0],
        [0,1,0,0,0,1,1,1,0,0,0,1,0],
    ],
]
