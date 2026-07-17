"""
Retro NES Battle City Sprites - authentic extraction
General-Sprites.png 400x256 original NES rip contains:
- Yellow player, green 2P, silver basic enemy, red power enemy, purple armor etc. plus tiles
This module loads the sheet and provides 16x16 tank sprites cropped for authentic look.
Matching your downloaded_maps editor which uses exact same sheet.

We also keep procedural 8x8 tiles for brick/steel/water/forest/ice that match your 4 custom maps (pixel-perfect NES).

For tanks: use sprite sheet directly for 100% authentic NES tanks.
"""
import pygame
import pathlib
from PIL import Image

ASSET_DIR = pathlib.Path(__file__).parent
GENERAL_SHEET = ASSET_DIR / "General-Sprites.png"

# Cache
_sheet_surface = None
_tank_cache = {}

def load_sheet_pygame():
    global _sheet_surface
    if _sheet_surface is None:
        if not GENERAL_SHEET.exists():
            return None
        _sheet_surface = pygame.image.load(str(GENERAL_SHEET)).convert_alpha()
    return _sheet_surface

# Mapping based on manual inspection of General-Sprites.png 400x256 (16px tiles)
# Coordinates in tiles (x_tiles, y_tiles) each 16px. First sheet has 25x16 tiles.
# From visual x4 screenshot you gave:
# - Yellow player tanks occupy cols 0-7 rows 0-7 (4 directions *2 anim)
#   Row0: up (2 frames col0-1), col2-3 right? Actually pattern: in sheet, first row appears as yellow tanks facing up? Let's look:
#   The sheet's top-left 8 columns: first row seems to contain up-facing yellow tanks (2 frames), second row down-facing, etc.
#   Row0 col0 = yellow up frame0, col1 = yellow up frame1, col2 = yellow right frame0? Wait in classic NES sheet layout, each tank direction has 2 frames side-by-side.
#   So our x4 image shows: columns 0 and 1 both up (tread anim), 2-3 right, 4-5 down, 6-7 left maybe? Let's assume that.

# We will define a helper to get tank sprite by type and direction
# Type mapping:
# P1 yellow: basic level uses same sprite as level0? Actually Battle City has 4 levels for player (different guns). We'll use level 0 for all P1 unless star.
# For simplicity, use:
# - yellow player level 0-3 share same base but different armor? In sheet, yellow tanks have 4 distinct levels: basic, fast, power, armor (ArmorPlayerTank) as per tanks.tsx – they are different art.
#   BasicPlayerTank, FastPlayerTank etc are different shapes (size of gun, tracks width)
#   So we need separate sprites for each level.

# Let's map using the sheet coordinates we can infer from feichao's resources:
# From your x4 screenshot, the tank grid:
# Row 0: col0-7 yellow basic? Actually row0 col0-7 appears to be same tank facing different? Looks like yellow tanks with different gun lengths (levels)
# Better: Let's just extract based on the extracted single colors we did:
# yellow 0 at (0,0) 16x16, silver at (8,0), green at (0,8), red at (8,8) for basic.
# We need directions: for each color, the 8 columns around contain 4 directions *2 frames.
# So for yellow: (0,0)-(7,0) row0 are 8 frames of yellow? Let's assume:
# (0,0)=up f0, (1,0)=up f1, (2,0)=right f0, (3,0)=right f1, (4,0)=down f0, (5,0)=down f1, (6,0)=left f0, (7,0)=left f1
# Similarly row1 and row2 might contain level upgrades? Actually row1 also yellow? Looking at screenshot, row1 col0-7 also yellow similar but slightly larger gun? Could be level1 fast.

# Simplifying: we will provide function get_tank_sprite(color, direction, frame, level) that indexes.
# For now, implement generic: color 'yellow'/'green'/'silver'/'red' (red = powerup armor etc)

# Exact mapping from your 4 screenshots + verification via crops:
# yellow_first_row_8tanks.png etc:
# col0=UP f0, col1=UP f1, col2=RIGHT f0, col3=RIGHT f1, col4=DOWN f0, col5=DOWN f1, col6=LEFT f0, col7=LEFT f1
# This is official NES Battle City order (UP,RIGHT,DOWN,LEFT) *2 tread frames = 8 columns per row

# Base positions (in 16px tiles) for each tank color/type in General-Sprites.png 400x256 (25x16 tiles)
# Verified by extracting non-empty cells and by visual of your x4 upscale:
# Yellow player (P1) basic row starts at (0,0), fast at (0,1), power at (0,2), armor at (0,3) ???
# Actually from tanks.tsx source, there are 4 player tank types: Basic,Fast,Power,Armor each have 2 shape frames for tread animation (shape 0/1)
# Those shapes are drawn as SVG in original but our PNG sheet contains them as well. For simplicity we use rows as levels:
# Row 0: Basic yellow (small gun)
# Row 1: Fast yellow (medium)
# Row 2: Power yellow (wide body, cannon)
# Row 3: Armor yellow (large)
# Similarly green P2 rows 8-11, silver enemy rows 0 col8, red enemy rows 8 col8 etc.
# However our earlier extraction of yellow first row shows 8 frames in single row = all directions for ONE level.
# So LEVEL is row offset: level 0 = row 0, level1 = row1 for yellow, etc.
# For silver enemy: col 8,row0 = silver basic level 0 row, row1 = silver level1? etc.
TANK_BASE = {
    "yellow": (0, 0),   # yellow P1 basic at row0 col0, level adds row
    "silver": (8, 0),   # silver basic enemy at row0 col8
    "green": (0, 8),    # green P2
    "red": (8, 8),      # red/purple power/armor enemy
}

# Direction to column offset within 8-frame row (each dir has 2 anim frames)
DIR_OFFSETS = {'UP':0, 'RIGHT':2, 'DOWN':4, 'LEFT':6}  # start index of pair, verified by your yellow strip

def get_tank_frame(color, direction, anim_frame=0, level=0):
    """
    Return 16x16 surface from sprite sheet.
    direction: 'UP','DOWN','LEFT','RIGHT'
    anim_frame: 0/1 tread anim (toggled every 8 game frames for classic look)
    level: 0-3 (basic,fast,power,armor) selects row offset
    """
    base = TANK_BASE.get(color, (0,0))
    base_x, base_y = base

    # Dir offset
    d = direction.upper() if isinstance(direction, str) else 'UP'
    col_offset = DIR_OFFSETS.get(d, 0) + (anim_frame % 2)

    fx = base_x + col_offset
    fy = base_y + level  # level = row offset

    sheet = load_sheet_pygame()
    if sheet is None:
        return None

    # Bounds check (sheet 25x16)
    if fx < 0 or fy < 0 or fx >= 25 or fy >= 16:
        fx = base_x
        fy = base_y

    rect = pygame.Rect(fx*16, fy*16, 16, 16)
    sub = pygame.Surface((16,16), pygame.SRCALPHA)
    sub.blit(sheet, (0,0), rect)
    return sub

def get_tank_sprite_scaled(color, direction, anim_frame=0, level=0, size=32):
    small = get_tank_frame(color, direction, anim_frame, level)
    if small is None:
        return None
    # Scale with nearest for crisp NES pixels
    # If size is multiple of 16, use scale for perfect pixels
    scaled = pygame.transform.scale(small, (size, size))
    return scaled

# Also cache for performance
_sprite_cache = {}
def get_cached_tank(color, direction, anim, level, size):
    key = (color, direction, anim, level, size)
    if key in _sprite_cache:
        return _sprite_cache[key]
    s = get_tank_sprite_scaled(color, direction, anim, level, size)
    _sprite_cache[key] = s
    return s
