"""
Mega maps - 4x area (52x52) with base at very center surrounded by concrete/steel fort.
No fragmented small dots - uses solid big blocks like original NES maps from downloaded_maps/.
Tile types: 0 empty,1 brick,2 steel,3 water,4 grass,5 ice
Style reference: downloaded_maps/*.jpg - solid walls, big forest blocks, water rectangles, steel fortresses.
"""
import random

TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_GRASS = 4
TILE_ICE = 5

MEGA_W = 52
MEGA_H = 52
BASE_CX = 25
BASE_CY = 25

def create_empty_mega():
    return [[TILE_EMPTY for _ in range(MEGA_W)] for _ in range(MEGA_H)]

def build_center_base_steel_fort(tilemap, base_x=BASE_CX, base_y=BASE_CY):
    """Base at center with thick concrete/steel fort - solid walls like downloaded_maps"""
    # Clear base 2x2
    for dy in range(2):
        for dx in range(2):
            tilemap[base_y+dy][base_x+dx] = TILE_EMPTY
    # Thick steel fort: outer 8x8 steel border
    for dy in range(-4, 6):
        for dx in range(-4, 6):
            gx = base_x + dx
            gy = base_y + dy
            if not (0 <= gx < MEGA_W and 0 <= gy < MEGA_H):
                continue
            if (gx, gy) in [(base_x, base_y), (base_x+1, base_y), (base_x, base_y+1), (base_x+1, base_y+1)]:
                continue
            # Outer thick steel - 2 tiles thick
            if abs(dx) == 4 or abs(dy) == 4 or abs(dx) == 3 or abs(dy) == 3:
                tilemap[gy][gx] = TILE_STEEL
    # Inner brick ring with 4 openings (N,S,E,W) - like classic base protection
    # Openings keep base accessible
    openings = [
        (base_x, base_y-4), (base_x+1, base_y-4),  # north
        (base_x, base_y+5), (base_x+1, base_y+5),  # south
        (base_x-4, base_y), (base_x-4, base_y+1),  # west
        (base_x+5, base_y), (base_x+5, base_y+1),  # east
    ]
    for gx, gy in openings:
        if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
            tilemap[gy][gx] = TILE_EMPTY

def add_solid_rect(tilemap, x, y, w, h, tile_type, skip_base=True):
    """Draw solid rectangle block - like downloaded_maps solid walls"""
    for dy in range(h):
        for dx in range(w):
            gx = x+dx
            gy = y+dy
            if not (0 <= gx < MEGA_W and 0 <= gy < MEGA_H):
                continue
            if skip_base and abs(gx-BASE_CX) < 7 and abs(gy-BASE_CY) < 7:
                continue
            tilemap[gy][gx] = tile_type

def add_solid_blocks_from_original(tilemap, orig_map_13, offset_x, offset_y, scale=4):
    """
    Place a 13x13 original map as solid big blocks into mega map.
    Each 13x13 cell becomes scale x scale block (e.g., 4x4 for 52x52)
    This creates solid walls, not fragmented dots.
    """
    for by in range(13):
        for bx in range(13):
            t = orig_map_13[by][bx]
            if t == 0:
                continue
            gx0 = offset_x + bx*scale
            gy0 = offset_y + by*scale
            # Draw solid block of ttype size scale x scale
            for dy in range(scale):
                for dx in range(scale):
                    gx = gx0+dx
                    gy = gy0+dy
                    if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                        if abs(gx-BASE_CX) < 7 and abs(gy-BASE_CY) < 7:
                            continue
                        tilemap[gy][gx] = t

def generate_mega_level(index):
    """Generate mega level using solid blocks like downloaded_maps structure"""
    m = create_empty_mega()
    build_center_base_steel_fort(m, BASE_CX, BASE_CY)
    
    try:
        from .battle_city import LEVELS_13, LEVELS_26
        # Use LEVELS_13 as source for solid blocks (more authentic big blocks)
        orig13 = LEVELS_13[index % len(LEVELS_13)]
        
        # Strategy: place original map scaled to 4 quadrants with solid blocks
        # Top-left quadrant: first half of original scaled
        # We want big solid walls, not single tiles
        
        # Place original 13x13 map scaled 2x in center area around base, creating Maze
        # Use 26x26 precise map but scaled as 2x2 solid blocks for mega
        orig26 = LEVELS_26[index % len(LEVELS_26)]
        
        # Copy original 26x26 into top-left and bottom-right quadrants as solid
        # Top-left quadrant (0,0)
        for y in range(26):
            for x in range(26):
                t = orig26[y][x]
                if t == 0:
                    continue
                if abs(x-12) < 4 and abs(y-12) < 4:
                    continue  # skip center of original that would overlap mega center if placed at 0,0
                if m[y][x] == TILE_EMPTY:
                    # Keep solid, no random fragmentation
                    if abs(x-BASE_CX) > 6 or abs(y-BASE_CY) > 6:
                        m[y][x] = t
        
        # Bottom-right quadrant mirrored - create second maze area
        for y in range(26):
            for x in range(26):
                gx = x + 26
                gy = y + 26
                if gx >= MEGA_W or gy >= MEGA_H:
                    continue
                if abs(gx-BASE_CX) < 7 and abs(gy-BASE_CY) < 7:
                    continue
                t = orig26[y][x]
                if t != 0 and random.random() < 0.85:  # 85% keep solid
                    if m[gy][gx] == TILE_EMPTY:
                        m[gy][gx] = t
        
        # Top-right and bottom-left: add solid walls based on pattern type
        pattern_type = ["brick_fort", "water", "forest", "steel_fort", "mixed"][index % 5]
        
        if pattern_type == "brick_fort":
            # Big solid brick fortresses like OP9X_b.jpg
            forts = [(30, 5, 12, 8, TILE_BRICK), (5, 30, 10, 12, TILE_BRICK), (35, 35, 10, 8, TILE_STEEL)]
            for x, y, w, h, tt in forts:
                if abs(x-BASE_CX) > 7 or abs(y-BASE_CY) > 7:
                    add_solid_rect(m, x, y, w, h, tt)
        elif pattern_type == "water":
            # Big water rectangles like +2Fof9.jpg has large water area
            waters = [(8, 8, 16, 6, TILE_WATER), (28, 15, 12, 8, TILE_WATER), (10, 35, 20, 4, TILE_WATER)]
            for x, y, w, h, tt in waters:
                add_solid_rect(m, x, y, w, h, tt)
            # Add some brick islands in water
            add_solid_rect(m, 12, 10, 4, 2, TILE_BRICK)
            add_solid_rect(m, 32, 18, 4, 2, TILE_BRICK)
        elif pattern_type == "forest":
            # Big forest blocks like 0YU1FH.jpg has large green areas
            forests = [(5, 5, 14, 10, TILE_GRASS), (32, 8, 12, 10, TILE_GRASS), (8, 32, 10, 12, TILE_GRASS)]
            for x, y, w, h, tt in forests:
                add_solid_rect(m, x, y, w, h, tt)
        elif pattern_type == "steel_fort":
            # Steel fortresses like lU_lvY.jpg has gray steel walls
            steels = [(10, 8, 8, 2, TILE_STEEL), (30, 10, 2, 10, TILE_STEEL), (12, 28, 12, 2, TILE_STEEL), (38, 32, 8, 8, TILE_STEEL)]
            for x, y, w, h, tt in steels:
                add_solid_rect(m, x, y, w, h, tt)
            # Brick behind
            add_solid_rect(m, 5, 15, 6, 10, TILE_BRICK)
        else:  # mixed
            # Mix of big solid blocks - like all downloaded_maps have big areas not dots
            add_solid_rect(m, 6, 6, 10, 3, TILE_BRICK)
            add_solid_rect(m, 30, 6, 12, 4, TILE_STEEL)
            add_solid_rect(m, 8, 20, 8, 8, TILE_BRICK)
            add_solid_rect(m, 36, 22, 10, 6, TILE_BRICK)
            add_solid_rect(m, 10, 36, 8, 8, TILE_WATER)
            add_solid_rect(m, 28, 38, 12, 6, TILE_GRASS)
    
    except Exception as e:
        # Fallback solid maps if battle_city import fails
        print(f"Mega gen fallback: {e}")
        # Simple solid maze
        for i in range(0, MEGA_W, 8):
            if i % 16 == 0:
                add_solid_rect(m, i, 4, 2, 18, TILE_BRICK)
        for i in range(0, MEGA_H, 8):
            if i % 16 == 0:
                add_solid_rect(m, 4, i, 18, 2, TILE_BRICK)
    
    # Ensure clear corridors to center base (wide roads, not single tile)
    # North-South highway 4 tiles wide
    for y in range(0, BASE_CY-4):
        for dx in range(2):
            m[y][BASE_CX+dx] = TILE_EMPTY
    for y in range(BASE_CY+6, MEGA_H):
        for dx in range(2):
            m[y][BASE_CX+dx] = TILE_EMPTY
    # East-West highway
    for x in range(0, BASE_CX-4):
        for dy in range(2):
            m[BASE_CY+dy][x] = TILE_EMPTY
    for x in range(BASE_CX+6, MEGA_W):
        for dy in range(2):
            m[BASE_CY+dy][x] = TILE_EMPTY
    
    # Clear player spawns (big clear area)
    for px, py in [(8,48), (42,48), (0,0), (25,0), (50,0), (0,25)]:
        for dy in range(-2, 4):
            for dx in range(-2, 4):
                gx = px+dx
                gy = py+dy
                if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                    if not (abs(gx-BASE_CX) < 8 and abs(gy-BASE_CY) < 8):
                        m[gy][gx] = TILE_EMPTY
    
    # Remove isolated single tiles (fragmented dots) - if tile has no same-type neighbor, remove it
    # This ensures no small fragmented dots
    to_clear = []
    for y in range(MEGA_H):
        for x in range(MEGA_W):
            if m[y][x] == TILE_EMPTY:
                continue
            if abs(x-BASE_CX) < 8 and abs(y-BASE_CY) < 8:
                continue
            # Count same-type neighbors in 4-dir
            same_neighbors = 0
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < MEGA_W and 0 <= ny < MEGA_H:
                    if m[ny][nx] == m[y][x]:
                        same_neighbors += 1
            # If isolated (0 same neighbors) and not part of steel fort (which might be border), remove
            if same_neighbors == 0:
                # But keep if it's intentional single? In downloaded_maps, no isolated single tiles - all are blocks
                # So clear isolated
                to_clear.append((x,y))
    for x,y in to_clear:
        m[y][x] = TILE_EMPTY
    
    return m

# Generate 35 mega maps
MEGA_LEVELS_52 = [generate_mega_level(i) for i in range(35)]

MEGA_LEVELS_13 = []
for i in range(35):
    try:
        from .battle_city import LEVELS_13
        if i < len(LEVELS_13):
            MEGA_LEVELS_13.append(LEVELS_13[i])
        else:
            MEGA_LEVELS_13.append(LEVELS_13[0])
    except:
        MEGA_LEVELS_13.append([[0]*13 for _ in range(13)])

MEGA_ENEMY_QUEUES = []
try:
    from .battle_city import ENEMY_QUEUES
    for q in ENEMY_QUEUES:
        MEGA_ENEMY_QUEUES.append(q + q[:len(q)//2])
except:
    MEGA_ENEMY_QUEUES = [['basic']*20 + ['fast']*10 + ['power']*5 + ['armor']*5 for _ in range(35)]

MEGA_STAGE_COUNT = 35
