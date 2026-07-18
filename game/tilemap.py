"""Tilemap system - classic Battle City style 26x26 small tiles"""
import pygame
import json
import random
from .settings import *

class TileMap:
    def __init__(self, level_data=None, is_mega=None):
        # Support both normal (26x26) and mega (52x52) maps
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
        self.shovel_original = None

        if level_data:
            self.load_from_data(level_data)
        else:
            self.load_default()

    def load_from_data(self, data):
        """data can be 13x13 big tiles or 26x26 small tiles or 52x52 mega"""
        if not data:
            return
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        if h == 13 and w == 13:
            # convert big to small - works for mega too (scale up)
            gw, gh = self.grid_w, self.grid_h
            # For mega, we need to scale 13x13 to 52x52 (4x), for normal 26x26 (2x)
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
            # 26x26 to current grid (scale if mega)
            if self.grid_w == 26:
                for y in range(26):
                    for x in range(26):
                        self.tiles[y][x] = data[y][x]
            else:  # scale to 52x52 (4x)
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
            # direct mega
            for y in range(52):
                for x in range(52):
                    if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                        self.tiles[y][x] = data[y][x]
        else:
            # arbitrary size - copy as much as fits
            for y in range(min(h, self.grid_h)):
                for x in range(min(w, self.grid_w)):
                    self.tiles[y][x] = data[y][x]

    def load_default(self):
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                self.tiles[y][x] = TILE_EMPTY
        self.build_base_walls(TILE_BRICK)

    def clear_area(self, gx, gy, w=4, h=4):
        """Clear tiles around (gx,gy) to make spawn safe, centered"""
        bx, by = self.base_pos
        base_cells = [(bx, by), (bx+1, by), (bx, by+1), (bx+1, by+1)]
        for y in range(gy, gy+h):
            for x in range(gx, gx+w):
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    if (x, y) in base_cells:
                        continue
                    self.tiles[y][x] = TILE_EMPTY

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
        """Build walls around base. For mega, 2 layers default as bricks (not thick steel fort)"""
        bx, by = self.base_pos
        if self.is_mega:
            # NEW: 2 layers only, default bricks (user request: center base has too much walls, make it 2 layers default bricks)
            # Outer ring at distance 2, inner at distance 1, both bricks by default
            # Openings N/S/E/W kept for access
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
            # Default as bricks for mega center base (2 layers)
            fort_tile = TILE_BRICK  # default bricks per user request
            # If concrete_steel flag or tile_type is steel (shovel powerup), use steel
            use_steel = concrete_steel or tile_type == TILE_STEEL
            wall_tile = TILE_STEEL if use_steel else TILE_BRICK
            
            # Build 2 layers: inner and outer both as brick (or steel if shovel)
            for (x, y) in outer + inner:
                if 0 <= x < self.grid_w and 0 <= y < self.grid_h:
                    self.tiles[y][x] = wall_tile
            
            # Create openings N/S/E/W (2 tiles each for access)
            openings = [
                (bx, by-2), (bx+1, by-2),  # north
                (bx, by+3), (bx+1, by+3),  # south
                (bx-2, by), (bx-2, by+1),  # west
                (bx+3, by), (bx+3, by+1),  # east
            ]
            for gx, gy in openings:
                if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                    self.tiles[gy][gx] = TILE_EMPTY
        else:
            # Normal mode: classic 1-layer walls around base
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
        """rect in playfield pixel coords, return list of (tile_type, gx, gy, tile_rect)"""
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

    def destroy_tile(self, gx, gy, bullet_power=1, bullet_dir=None):
        if not (0 <= gx < self.grid_w and 0 <= gy < self.grid_h):
            return False
        # NEW: Only destroy 1 brick per hit (tank-sized), not 2 like old authentic logic
        tiles_to_destroy = [(gx, gy)]

        destroyed = False
        for tx, ty in tiles_to_destroy:
            if not (0 <= tx < self.grid_w and 0 <= ty < self.grid_h):
                continue
            t = self.tiles[ty][tx]
            if t == TILE_BRICK:
                self.tiles[ty][tx] = TILE_EMPTY
                destroyed = True
            elif t == TILE_STEEL and bullet_power >= 2:
                self.tiles[ty][tx] = TILE_EMPTY
                destroyed = True
        return destroyed

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
                    self.draw_brick(screen, rx, ry)
                elif t == TILE_STEEL:
                    self.draw_steel(screen, rx, ry)
                elif t == TILE_WATER:
                    self.draw_water(screen, rx, ry)
                # grass and ice drawn later overlay (after tanks)

    def draw_overlay(self, screen):
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                t = self.tiles[y][x]
                rx = PLAYFIELD_X + x * self.tile_size
                ry = PLAYFIELD_Y + y * self.tile_size
                if t == TILE_GRASS:
                    self.draw_grass(screen, rx, ry)
                elif t == TILE_ICE:
                    self.draw_ice(screen, rx, ry)

    # ===== Pixel-perfect NES Battle City tiles extracted from downloaded_maps =====
    # Screenshots are 5x upscaled: 40px = 8px native. We recreate exact 8x8 and 16x16 patterns.
    # Tile layout per NES:
    # - Brick 8x8: red-orange bricks with 1px dark mortar, 3 rows, staggered. 2 mortar shades.
    # - Steel 8x8: white tile with light gray shade, dark border, inner bevel, rivets.
    # - Water 8x8: bright blue #2870FF with white 1-2px speckle dots animated 2-phase.
    # - Forest 8x8: dappled green - base #60A014 + dark #185A00 + light #B0E040 dither 50% density.
    # - Ice 8x8: light gray #C0C0C0 with diagonal \\\\ hatching dark #808080 / light #E0E0E0.

    def _brick_pixels_8(self):
        # Return 8x8 pixel array for brick small tile, based on extraction from tile_brick_red_big.png
        # Pattern from crop: red #D8 3A 14, mortar #8B 20 10 dark and #5A 1A 08 darker
        # 8x8 breakdown: 2 brick rows of 3px + 1px mortar between + 1px top/bottom
        # Row0: top mortar 1px blackish, then bricks
        # Using extracted data: 8x8 brick_small had ~24 unique colors due to jpg, but core is:
        # Let's define exact pattern to match 0YU1FH.jpg which is cleanest
        # Approximate true NES brick 8x8: looks like:
        # Row0: |########|  full brick
        # Row1: |###||###|  vertical mortar center
        # Row2: |########| mortar horizontal separator
        # Row3: |#||###||#| staggered
        # etc. We'll use palette:
        return None  # we draw procedurally below matching extraction

    def draw_brick(self, screen, x, y):
        # Fine-grained brick - similar size as tank (tank 32px, brick tile 24px but with 4 micro-bricks)
        # Make brick look smaller/more detailed like NES original has 4 mini bricks per tile
        # Draw at native 16x16 then scale to tile_size, with visible mortar gaps
        ts = self.tile_size
        # Create surface with mortar gap around edges (2px gap makes brick appear smaller, similar to tank)
        # Use fine-grained 16x16 pattern with 4 bricks
        s = pygame.Surface((16,16))
        BR = (210, 56, 24)   # brick red
        BD = (100, 22, 10)   # dark mortar
        BL = (240, 90, 50)   # light highlight
        BM = (140, 30, 12)   # mid mortar
        
        s.fill(BD)  # mortar background
        
        # Draw 4 small bricks in 16x16: 2 rows of 2 bricks each, with mortar gaps
        # Each small brick ~7x6 with 2px mortar gaps - makes bricks look fine-grained, similar to tank details
        brick_w = 7
        brick_h = 6
        gap = 2
        # Positions for 4 bricks
        positions = [(1, 1), (9, 1), (1, 9), (9, 9)]
        # Stagger second row
        positions = [(1, 1), (9, 1), (2, 9), (10, 9)]  # staggered like NES
        
        for bx, by in positions:
            # Brick body with highlight top
            pygame.draw.rect(s, BR, (bx, by, brick_w, brick_h))
            # Top highlight line (1px)
            pygame.draw.line(s, BL, (bx, by), (bx+brick_w-1, by), 1)
            # Left highlight
            # pygame.draw.line(s, BL, (bx, by), (bx, by+brick_h-1), 1)
        
        # Add vertical mortar lines to emphasize separation
        pygame.draw.line(s, BM, (8, 1), (8, 7), 1)
        pygame.draw.line(s, BM, (1, 8), (15, 8), 1)
        
        # Scale to tile_size with slight shrink for mortar gap around tile (makes brick appear smaller than tank)
        # If BRICK_FINE_GRAINED enabled, shrink visual with gap
        if getattr(self, '_brick_shrink', True):
            # Draw with 1px gap around tile for fine-grained look
            scaled = pygame.transform.scale(s, (ts-2, ts-2))
            screen.blit(scaled, (x+1, y+1))
        else:
            scaled = pygame.transform.scale(s, (ts, ts))
            screen.blit(scaled, (x, y))

    def draw_steel(self, screen, x, y):
        # Pixel-perfect NES steel from tile_steel.png extraction:
        # 8x8 steel pattern observed:
        # White tile with gray border: outer 1px dark gray (130,130,130), inner fill white (210,210,210) with central 4x4 lighter white (255,255,255) and rivets dark at corners
        s = pygame.Surface((8,8))
        # palette
        S_BG = (210, 210, 210)  # base
        S_DARK = (130, 130, 130)  # outer border / shadow
        S_LIGHT = (255, 255, 255)  # inner hilight
        S_RIVET_D = (90, 90, 90)
        S_RIVET_L = (230, 230, 230)

        s.fill(S_DARK)
        # inner white area 6x6
        pygame.draw.rect(s, S_BG, (1,1,6,6))
        pygame.draw.rect(s, S_LIGHT, (2,2,4,4))
        # rivet at center? Actually NES steel small tile has rivets at corners of inner? In screenshots steel tiles show no rivets for small 8x8, but for 16x16 there are 4 inner squares.
        # Since we are rendering small 8px tile (our TILE_SIZE=24 is 3x native), the native 8x8 steel is just white with gray border. Extraction shows unique colors 34 for 16x16 but for 8x8 it was all black (error crop on black). Let's approximate:
        # Draw small shadow at bottom/right
        s.set_at((6,6), S_DARK)
        s.set_at((1,6), S_DARK)
        s.set_at((6,1), S_DARK)

        # Add rivet like dot at center of each edge? Actually keep simple: 1px dark dots at 2,2 and 5,2 etc?
        # For authenticity, add tiny rivets at (2,2) and (5,5) as in big steel pattern where each 8x8 has a rivet
        # We'll add dark pixel + light highlight offset
        # Top-left rivet
        s.set_at((2,2), S_RIVET_D)
        s.set_at((1,1), S_RIVET_L)

        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

    def draw_water(self, screen, x, y):
        # NES water from tile_water_blue 8x8 extraction had blue base (27,92,255) with white sparkle (156,230,255) 2x2 dots
        # Pattern observed in +2Fof9.jpg: water tile 16x16 has many white dots ~2px, spacing ~4px, arranged in staggered rows
        # Original NES water animation is 2 frames toggling dot positions. We will implement 2-phase animation using pygame.time.get_ticks()
        # Base blue
        s = pygame.Surface((8,8))
        BLUE = (28, 90, 240)
        WHITE = (235, 245, 255)
        s.fill(BLUE)

        t = pygame.time.get_ticks()
        phase = (t // 200) % 2  # 2 phases like NES

        # Native 8x8 water pattern: based on extraction water_small unique colors 33, had white dots at approx positions
        # We'll define two phases to animate sparkling
        if phase == 0:
            dots = [(1,1),(3,2),(6,1),(2,4),(5,5),(1,6)]
        else:
            dots = [(2,1),(5,2),(1,3),(4,4),(6,6),(2,7)]

        for dx, dy in dots:
            # some dots 2x1
            if (dx+dy) % 2 == 0:
                s.set_at((dx, dy), WHITE)
                if dx+1 < 8:
                    s.set_at((dx+1, dy), WHITE)
            else:
                s.set_at((dx, dy), WHITE)

        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

    def draw_grass(self, screen, x, y):
        # Forest/grass mottled – extracted from forest_big 16x16 had many greens: base (60,160,20), dark (20,100,10), light (140,230,80) etc.
        # Pattern: dense dither 8x8 with 50% coverage dark/light alternation
        # Native 8x8 forest pattern from tile_forest_green.png:
        # It appears as checker-like noise
        s = pygame.Surface((8,8))
        BASE = (60, 160, 20)
        DARK = (20, 80, 10)
        LIGHT = (160, 220, 90)
        MID = (90, 190, 40)
        DARK2 = (30, 110, 20)

        s.fill(BASE)

        # Dark speckles pattern – use fixed pattern matching extract (visually mottled)
        dark_spots = [(0,1),(2,0),(4,1),(6,0),(1,3),(3,2),(5,3),(7,2),(0,5),(2,4),(4,5),(6,4),(1,7),(3,6),(5,7),(7,6)]
        for dx, dy in dark_spots[::2]:
            s.set_at((dx, dy), DARK)
        for dx, dy in dark_spots[1::2]:
            s.set_at((dx, dy), DARK2)

        light_spots = [(1,0),(3,1),(5,0),(7,1),(0,2),(2,3),(4,2),(6,3),(1,4),(3,5),(5,4),(7,5),(0,6),(2,7),(4,6),(6,7)]
        for i, (dx, dy) in enumerate(light_spots):
            if i % 3 == 0:
                s.set_at((dx, dy), LIGHT)
            elif i % 3 == 1:
                s.set_at((dx, dy), MID)

        # Add a couple extra highlights
        s.set_at((2,2), LIGHT)
        s.set_at((5,5), LIGHT)

        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

    def draw_ice(self, screen, x, y):
        # Ice hatched – from tile_ice_gray 16x16 extraction: light gray base (198,198,198) with diagonal stripes dark (130) / light (236)
        # Pattern: 45° stripes repeating every 4px?
        # Native 8x8 pattern: diagonal lines
        s = pygame.Surface((8,8))
        BASE = (190, 190, 190)
        DARK = (130, 130, 135)
        LIGHT = (230, 230, 235)
        VERY_LIGHT = (220, 220, 220)

        s.fill(BASE)

        # Diagonal hatching \ direction (from top-left to bottom-right) like screenshot OP9X_b.jpg bottom right gray area
        # For 8x8, pattern: stripes every 3px: e.g., positions where (x+y)%4==0 -> DARK, %2==0 -> LIGHT
        for px in range(8):
            for py in range(8):
                v = (px + py) % 4
                if v == 0:
                    s.set_at((px, py), DARK)
                elif v == 2:
                    s.set_at((px, py), LIGHT)
                # else base

        # Second set of stripes with offset? Add a few light highlights for sheen
        s.set_at((1,1), VERY_LIGHT)
        s.set_at((5,2), VERY_LIGHT)

        scaled = pygame.transform.scale(s, (self.tile_size, self.tile_size))
        screen.blit(scaled, (x, y))

# ---- Classic 35 NES Maps ----
# Import authentic 35 original Battle City maps converted from feichao93/battle-city
# Each stage: 13x13 big tiles (0 empty,1 brick,2 steel,3 water,4 forest,5 ice)
# plus 26x26 precise with half-brick support (B3 top half, Bc bottom, T3 top steel etc.)
# Source: https://github.com/feichao93/battle-city stage-{1..35}.json
# Tile decoding: X empty, B<h> brick hex, T<h> steel bitmask, R water, F forest, S ice, E eagle
# See docs/CLASSIC_MAPS_RESEARCH.md for full analysis
try:
    from .levels.battle_city import LEVELS_13 as _ORIG_13, LEVELS_26 as _ORIG_26, ENEMY_QUEUES, BOTS_RAW, STAGE_COUNT
    # Primary: use 26x26 precise (half-bricks) for accurate collision/rendering.
    # 13x13 simplified also available for editor export.
    LEVELS_13_ORIGINAL = _ORIG_13  # 35 x 13x13 simplified
    LEVELS_26_ORIGINAL = _ORIG_26  # 35 x 26x26 precise
    LEVELS = _ORIG_26  # default: 26x26 precise authentic maps
    ENEMY_QUEUES_ORIGINAL = ENEMY_QUEUES
    BOTS_RAW_ORIGINAL = BOTS_RAW
    ORIGINAL_STAGE_COUNT = STAGE_COUNT
except ImportError as e:
    # Fallback if battle_city module missing (e.g., running from stripped build)
    print(f"Warning: Could not load original 35 maps, using 5 handcrafted fallback: {e}")
    ORIGINAL_STAGE_COUNT = 5
    ENEMY_QUEUES_ORIGINAL = []
    BOTS_RAW_ORIGINAL = []
    LEVELS_13_ORIGINAL = []
    LEVELS_26_ORIGINAL = []
    LEVELS = [
        # Level 1 - classic (fallback)
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

# Backwards compat alias used elsewhere; now 35 maps
# If you want simplified 13x13 for debug, use LEVELS_13_ORIGINAL
