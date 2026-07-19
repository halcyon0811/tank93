"""
Tank 93 Enhanced - Settings
Designed for PC prototype with Switch portability in mind.
"""
import pygame

# Window
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
FPS = 60

MEGA_SCREEN_WIDTH = 1600
MEGA_SCREEN_HEIGHT = 1400  # tall enough for 1248 playfield + margins

# Playfield - classic Battle City is 13x13 big tiles = 26x26 small tiles
TILE_SIZE = 24
MEGA_ENABLED = False  # Restore original 35 maps with original size (user: big map too empty)
MEGA_GRID_W = 52
MEGA_GRID_H = 52
MEGA_TILE_SIZE = 24
MEGA_PLAYFIELD_W = 52 * 24
MEGA_PLAYFIELD_H = 52 * 24
MEGA_PLAYFIELD_X = 48
MEGA_PLAYFIELD_Y = 48
MEGA_BASE_POS = (25, 25)
MEGA_PLAYER_SPAWN = [(8, 48), (42, 48)]
MEGA_ENEMY_SPAWNS = [(0, 0), (25, 0), (50, 0), (0, 25)]

# When mega enabled, override to big map; otherwise use original 26x26
if MEGA_ENABLED:
    GRID_W = MEGA_GRID_W
    GRID_H = MEGA_GRID_H
    PLAYFIELD_W = MEGA_PLAYFIELD_W
    PLAYFIELD_H = MEGA_PLAYFIELD_H
    BASE_POS = MEGA_BASE_POS
    PLAYER_SPAWN = MEGA_PLAYER_SPAWN
    ENEMY_SPAWNS = MEGA_ENEMY_SPAWNS
    SCREEN_WIDTH = MEGA_SCREEN_WIDTH
    SCREEN_HEIGHT = MEGA_SCREEN_HEIGHT
else:
    GRID_W = 26
    GRID_H = 26
    PLAYFIELD_W = 26 * 24
    PLAYFIELD_H = 26 * 24
    BASE_POS = (12, 24)  # original bottom center
    PLAYER_SPAWN = [(8, 24), (16, 24)]
    ENEMY_SPAWNS = [(0, 0), (12, 0), (24, 0)]
    SCREEN_WIDTH = 960
    SCREEN_HEIGHT = 720

PLAYFIELD_X = 48
PLAYFIELD_Y = 48

# Compatibility helpers (still needed for old code)
def get_playfield_size(is_mega=False):
    return (MEGA_PLAYFIELD_W, MEGA_PLAYFIELD_H) if is_mega else (MEGA_PLAYFIELD_W if MEGA_ENABLED else 26*24, MEGA_PLAYFIELD_H if MEGA_ENABLED else 26*24)

def get_tile_size(is_mega=False):
    return 24  # always 24 to keep tank size same

def get_grid_size(is_mega=False):
    return (MEGA_GRID_W, MEGA_GRID_H) if (is_mega or MEGA_ENABLED) else (26, 26)

def get_base_pos(is_mega=False):
    return MEGA_BASE_POS if (is_mega or MEGA_ENABLED) else (12, 24)

def get_player_spawns(is_mega=False):
    return MEGA_PLAYER_SPAWN if (is_mega or MEGA_ENABLED) else [(8,24),(16,24)]

def get_enemy_spawns(is_mega=False):
    return MEGA_ENEMY_SPAWNS if (is_mega or MEGA_ENABLED) else [(0,0),(12,0),(24,0)]

def get_screen_size(is_mega=False):
    return (MEGA_SCREEN_WIDTH, MEGA_SCREEN_HEIGHT) if (is_mega or MEGA_ENABLED) else (960,720)

# Armor system
ARMOR_INITIAL_PLAYER = 100
ARMOR_INITIAL_ENEMY = {
    'basic': 50,
    'fast': 40,
    'power': 80,
    'armor': 150,
    'boss': 300,
    'monster_boss': 400,
    'monster': 300,
}
ARMOR_MAX_PLAYER = 300
ARMOR_UPGRADE_STAR = 25  # per star level
ARMOR_UPGRADE_TANK = 50  # extra life also gives armor
ARMOR_UPGRADE_GUN = 30   # gun powerup
ARMOR_SHIELD_REDUCTION = 0.3  # armor absorbs 70% damage, 30% passes to health when armor exists
ARMOR_REGEN_RATE = 0  # no auto regen

# Brick durability - hits needed to destroy
# Synergy bullets (power+homing etc) also defined here
BRICK_HITS_NEEDED = {
    'normal': 2,      # normal bullet 2 hits
    'power': 1,       # power/gun 1 hit
    'rapid': 3,       # rapid 3 hits (weaker per bullet)
    'homing': 4,      # tracking missile 4 hits (balanced because it avoids walls)
    'spread': 2,      # spread 2 hits
    'venom': 2,       # venom 2 hits
    'power_homing': 1,          # powerful tracking missile - 1 hit (synergy weapon enforcement + homing)
    'power_homing_spread': 1,   # 8 powerful homing missiles - 1 hit each
    'power_spread': 1,          # spread power bullets
    'power_rapid': 1,           # rapid power
    'power_spread_rapid': 1,    # ultimate spread rapid power
}

# Steel / concrete durability - harder than bricks, but now destructible by all weapons
# User request: weapon should be able to destroy concrete/steel, just harder than bricks
STEEL_HITS_NEEDED = {
    'normal': 5,      # normal bullet 5 hits (vs 2 for brick)
    'power': 2,       # power/gun 2 hits (vs 1)
    'rapid': 8,       # rapid 8 hits (weaker)
    'homing': 6,      # tracking missile 6 hits
    'spread': 5,      # spread 5 hits
    'venom': 4,       # venom 4 hits
    'power_homing': 2,          # powerful homing 2 hits
    'power_homing_spread': 2,   # 8 powerful homing 2 hits
    'power_spread': 2,
    'power_rapid': 2,
    'power_spread_rapid': 1,    # ultimate still 1 hit even for steel (reward)
}

# Sidebar HUD
HUD_X = PLAYFIELD_X + PLAYFIELD_W + 20
HUD_W = SCREEN_WIDTH - HUD_X - 20

# Colors - authentic NES Battle City palette matched from downloaded_maps (retro screenshots)
# Your downloaded_maps show: red-orange bricks, white/light-gray steel with rivets,
# bright blue water with white sparkles, mottled green forest, diagonal-hatched light gray ice
# Keeping classic NES look: black playfield background

COLOR_BG = (18, 18, 24)
COLOR_PLAYFIELD_BG = (0, 0, 0)

# --- Retro NES tile colors sampled from Battle City screenshots ---
# Brick: bright red-orange 0xE0 0x38 0x18 approx, mortar dark brown
COLOR_BRICK = (210, 56, 24)          # main red brick - from screenshots #D23818
COLOR_BRICK_DARK = (140, 30, 10)      # mortar dark
COLOR_BRICK_LIGHT = (240, 120, 70)    # highlight / top edge
COLOR_BRICK_MORTAR = (180, 180, 180)  # light gray mortar line (NES style thin)

COLOR_STEEL = (210, 210, 210)         # white/light gray steel
COLOR_STEEL_DARK = (130, 130, 130)    # shadow
COLOR_STEEL_LIGHT = (255, 255, 255)   # highlight / inner white square
COLOR_STEEL_RIVET = (160, 160, 160)

COLOR_WATER = (28,  90, 240)          # bright NES blue #1C5AF0
COLOR_WATER_DARK = (12, 60, 180)
COLOR_WATER_SPARKLE = (200, 220, 255) # white dots

COLOR_GRASS = (60, 160,  20)          # base green
COLOR_GRASS_DARK = (20, 100, 10)      # dark dapple
COLOR_GRASS_LIGHT = (140, 230, 80)    # light speckles
COLOR_GRASS_MID = (90, 190, 30)

COLOR_ICE = (190, 190, 190)           # light gray ice
COLOR_ICE_DARK = (130, 130, 135)
COLOR_ICE_STRIPE = (220, 220, 220)    # diagonal hatching light
COLOR_ICE_SHADOW = (100, 100, 105)

COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_YELLOW = (255, 224, 64)
COLOR_RED = (235, 50, 50)

# Retro brick pattern as used in NES: 2 rows of bricks per 16px tile, offset
# We'll draw exact pattern in tilemap.py draw_brick retro

# Player colors and names - P1=Chad, P2=Lida (user request)
PLAYER_COLORS = [
    (255, 220, 0),   # Chad (was P1) Yellow - modern
    (0, 200, 100),   # Lida (was P2) Green
]
PLAYER_NAMES = ["Chad", "Lida"]
# Keep backward compat for places that still say P1/P2
PLAYER_DISPLAY_NAMES = PLAYER_NAMES
# Mapping for old references

def get_player_display_name(player_id):
    """Get display name Chad/Lida for player id 1/2"""
    if 1 <= player_id <= len(PLAYER_NAMES):
        return PLAYER_NAMES[player_id-1]
    return f"P{player_id}"

ENEMY_COLORS = {
    'basic': (180, 180, 180),
    'fast': (80, 180, 255),
    'power': (255, 80, 80),
    'armor': (140, 140, 200),
    'boss': (100, 200, 80),  # monster boss green
    'monster_boss': (100, 200, 80),
    'monster': (120, 220, 100),
}

# Gameplay
TANK_SIZE = 32  # visual tank size similar to tile
TANK_SPEED = {"player": 3.3, "enemy": 1.8, "fast": 3.0}  # 1.5x faster
BULLET_SPEED = 8.25  # 1.5x faster: was 5.5 -> 8.25
BULLET_SIZE = 6
MAX_BULLETS = {"player": 2, "enemy": 1}

# Brick fine-grained: make brick tiles smaller visual detail similar to tank size
# Previously brick was full tile (24px). Now we want fine-grained like sub-tiles, but keep collision same
# We'll achieve via drawing: brick pattern more detailed, but collision grid stays same
# For finer feel, reduce TILE effective? Keep TILE_SIZE 24 but TANK 32 similar, so brick looks similar size
# Actually make brick slightly smaller visually: still 24px tile but with mortar gaps so brick appears ~20px ~ tank
BRICK_FINE_GRAINED = True
BRICK_VISUAL_SHRINK = 2  # shrink brick visual by 2px for mortar gap, making it feel similar to tank size

# Smart M (homing) missile - new behavior: tank speed, limited range, avoids walls
HOMING_SPEED = TANK_SPEED["player"] * 1.08  # ~3.56 now with 1.5x tank speed, keeps ratio
HOMING_MAX_DISTANCE = GRID_W * TILE_SIZE * 0.92  # ~574 px = 24 tiles travel limit (limited but allows going around walls)
HOMING_TURN_SPEED = 0.068  # slightly higher than before for wall avoidance agility, still smooth (was 0.18 before, now smarter slower)
HOMING_DETECTION_RANGE = PLAYFIELD_W * 0.92  # only track enemies within range
HOMING_LOS_CHECK = True  # prefer direct if line of sight, else A* waypoints
HOMING_ASTAR_REPLAN_INTERVAL = 36  # frames between path replan (faster replan for moving enemies)
HOMING_AVOIDANCE_LOOKAHEAD = 2.6  # tiles lookahead for obstacle avoidance (longer = earlier dodge)
HOMING_WALL_SAFE_MARGIN = 0.28  # safe margin from walls in tile units
HOMING_STUCK_DESTROY_THRESHOLD = 16  # frames stuck before destroying brick fallback

# These are overridden per MEGA_ENABLED above, kept for fallback if mega disabled
if not MEGA_ENABLED:
    PLAYER_SPAWN = [
        (8, 24),
        (16, 24),
    ]
    ENEMY_SPAWNS = [(0, 0), (12, 0), (24, 0)]
    BASE_POS = (12, 24)

# Powerups - classic + new items (homing missile, 8-way spread, rapid fire 3x, shrink, giant)
# grenade renamed to bomb per user request - now does armor damage, explodes only if no armor left
POWERUP_TYPES = ['helmet', 'clock', 'shovel', 'star', 'grenade', 'tank', 'gun', 'homing', 'spread', 'rapid', 'shrink', 'giant']

# Bomb (grenade) armor damage - new behavior: causes armor hurt, explodes only if no armor left
BOMB_ARMOR_DAMAGE = 100  # how much armor damage bomb does to each enemy on screen
BOMB_POWER_DAMAGE = 2    # health damage after armor gone (basic enemies health=1, armor enemies health=4, boss 18)
POWERUP_DURATION = {
    'helmet': 10 * FPS,
    'clock': 5 * FPS,
    'shovel': 15 * FPS,
    'homing': 15 * FPS,   # tracking missile active for 15 sec (now PERM until death)
    'spread': 12 * FPS,   # 8-direction firing for 12 sec (now PERM until death)
    'rapid': 10 * FPS,    # rapid fire 3x attack speed - now PERM until death
    'shrink': 15 * FPS,   # half size double speed for 15s
    'giant': 15 * FPS,    # double size crush bricks + enemies for 15s
}
STAR_LEVELS = 4

# New item specifics
SHRINK_SCALE = 0.5
SHRINK_SPEED_MULT = 2.0
GIANT_SCALE = 2.0
GIANT_DURATION = 15 * FPS
MONSTER_SPEED_MULT = 1.0  # slowed to normal enemy speed per user request (was 1.5x player)
VENOM_DISSOLVE_TIME = 18 * FPS  # slowed down venom: was 10s, now 18s for more time to counter (user request)
VENOM_SPEED = BULLET_SPEED * 0.45  # slowed down venom: was 0.7x bullet speed, now 0.45x (slower)
BULLET_COUNTER_ENABLED = True

# Venom spillover: infected player damages nearby tanks (proximity)
VENOM_SPILLOVER_ENABLED = True
VENOM_SPILLOVER_RADIUS = 72  # 3 tiles = 72px, proximity damage radius
VENOM_SPILLOVER_INTERVAL = 20  # every 20 frames (~0.33s) check and damage
VENOM_SPILLOVER_DAMAGE = 1  # power for nearby damage (armor damage 25 base)
VENOM_SPILLOVER_ENEMY_DAMAGE_FACTOR = 1.0  # full damage to enemies
VENOM_SPILLOVER_PLAYER_DAMAGE_FACTOR = 0.5  # half damage to other player (Chad/Lida friendly fire spillover)
VENOM_SPILLOVER_BOSS_DAMAGE_FACTOR = 0.7  # boss takes less from spillover

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

# Directions - 4 cardinal + 4 diagonal for 8-way firing item
DIRS = {
    'UP': (0, -1),
    'DOWN': (0, 1),
    'LEFT': (-1, 0),
    'RIGHT': (1, 0),
    'UP_LEFT': (-1, -1),
    'UP_RIGHT': (1, -1),
    'DOWN_LEFT': (-1, 1),
    'DOWN_RIGHT': (1, 1),
}
DIR_ANGLE = {
    'UP': 0,
    'UP_RIGHT': 45,
    'RIGHT': 90,
    'DOWN_RIGHT': 135,
    'DOWN': 180,
    'DOWN_LEFT': 225,
    'LEFT': 270,
    'UP_LEFT': 315,
}
# For 8-direction firing
EIGHT_DIRS = ['UP', 'UP_RIGHT', 'RIGHT', 'DOWN_RIGHT', 'DOWN', 'DOWN_LEFT', 'LEFT', 'UP_LEFT']

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
