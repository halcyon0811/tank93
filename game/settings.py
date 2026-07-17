"""
Tank 90 Enhanced - Settings
Designed for PC prototype with Switch portability in mind.
"""
import pygame

# Window
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
FPS = 60

# Playfield - classic Battle City is 13x13 big tiles = 26x26 small tiles
TILE_SIZE = 24  # small tile pixel size (modernized HD)
GRID_W = 26
GRID_H = 26
PLAYFIELD_W = GRID_W * TILE_SIZE  # 624
PLAYFIELD_H = GRID_H * TILE_SIZE  # 624
PLAYFIELD_X = 48
PLAYFIELD_Y = 48

# Sidebar HUD
HUD_X = PLAYFIELD_X + PLAYFIELD_W + 20
HUD_W = SCREEN_WIDTH - HUD_X - 20

# Colors - modernized palette
COLOR_BG = (18, 18, 24)
COLOR_PLAYFIELD_BG = (0, 0, 0)
COLOR_BRICK = (168, 80, 32)
COLOR_BRICK_DARK = (120, 56, 24)
COLOR_BRICK_LIGHT = (200, 112, 48)
COLOR_STEEL = (160, 160, 170)
COLOR_STEEL_DARK = (110, 110, 120)
COLOR_STEEL_LIGHT = (200, 200, 210)
COLOR_WATER = (32, 99, 199)
COLOR_WATER_DARK = (16, 60, 150)
COLOR_GRASS = (34, 139, 34)
COLOR_GRASS_DARK = (20, 100, 20)
COLOR_ICE = (173, 216, 230)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_YELLOW = (255, 224, 64)
COLOR_RED = (235, 50, 50)

# Player colors
PLAYER_COLORS = [
    (255, 220, 0),   # P1 Yellow - modern
    (0, 200, 100),   # P2 Green
]

ENEMY_COLORS = {
    'basic': (180, 180, 180),
    'fast': (80, 180, 255),
    'power': (255, 80, 80),
    'armor': (140, 140, 200),
}

# Gameplay
TANK_SIZE = 32  # visual tank size slightly bigger than tile
TANK_SPEED = {"player": 2.2, "enemy": 1.2, "fast": 2.0}
BULLET_SPEED = 5.5
BULLET_SIZE = 6
MAX_BULLETS = {"player": 2, "enemy": 1}  # classic limiting

PLAYER_SPAWN = [
    (8, 24),   # P1 grid position
    (16, 24),  # P2
]
ENEMY_SPAWNS = [(0, 0), (12, 0), (24, 0)]
BASE_POS = (12, 24)  # eagle position (top-left of 2x2)

# Powerups
POWERUP_TYPES = ['helmet', 'clock', 'shovel', 'star', 'grenade', 'tank', 'gun']
POWERUP_DURATION = {
    'helmet': 10 * FPS,
    'clock': 5 * FPS,
    'shovel': 15 * FPS,
}
STAR_LEVELS = 4

# Enemy count per level
ENEMIES_PER_LEVEL = 20
MAX_ENEMIES_ON_FIELD = 4
ENEMY_SPAWN_INTERVAL = 2.5 * FPS

# Arcade Coin System - Each coin = 10 lives
INITIAL_LIVES = 3
COIN_LIVES = 10
MAX_LIVES = 99
CONTINUE_TIME = 15 * FPS  # 15 sec to continue
COIN_KEYS = [pygame.K_c, pygame.K_5]  # MAME style: 5=coin, C=coin
P1_START_KEYS = [pygame.K_1]
P2_START_KEYS = [pygame.K_2]

# Joy-Con Calibration - Both sides have 90° rotation bug per latest user report:
# Right: Up->Right, Down->Left, Right->Down = 90° rotation = SWAP+INV_Y fix
# Left: previously fixed with same SWAP+INV_Y
JOYCON_INVERT_X = False
JOYCON_INVERT_Y = True
JOYCON_SWAP_AXES = True
# Per Joy-Con - both use SWAP+INV_Y for 90° rotation
JOYCON_L_INVERT_X = False
JOYCON_L_INVERT_Y = True
JOYCON_L_SWAP = True
JOYCON_R_INVERT_X = False
JOYCON_R_INVERT_Y = True
JOYCON_R_SWAP = True
# Rumble disabled per user request
ENABLE_RUMBLE = False
# D-pad mapping
JOYCON_L_DPAD_MAP = {0: 'DOWN', 1: 'RIGHT', 2: 'UP', 3: 'LEFT'}
JOYCON_R_FACE_MAP = {0: 'LEFT', 1: 'UP', 2: 'DOWN', 3: 'RIGHT'}

# Directions
DIRS = {
    'UP': (0, -1),
    'DOWN': (0, 1),
    'LEFT': (-1, 0),
    'RIGHT': (1, 0),
}
DIR_ANGLE = {
    'UP': 0,
    'RIGHT': 90,
    'DOWN': 180,
    'LEFT': 270,
}

# Tile types (using classic Battle City)
# 0 empty, 1 brick, 2 steel, 3 water, 4 grass/trees, 5 ice, 6 base border
TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_GRASS = 4
TILE_ICE = 5

# For easier map design, we support big tile (2x2 small tiles)
# Will convert big tile map 13x13 to 26x26
