"""
Mega maps - 4x area (52x52) with base at very center surrounded by concrete/steel fort.
Tile types: 0 empty,1 brick,2 steel,3 water,4 grass,5 ice
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
    """Base at center with concrete (steel) surrounding it - thick fort"""
    # 2x2 base empty
    for dy in range(2):
        for dx in range(2):
            tilemap[base_y+dy][base_x+dx] = TILE_EMPTY
    # Thick steel fort - double layer concrete
    # Outer ring 6x6 steel, inner gap with brick
    for dy in range(-3, 5):
        for dx in range(-3, 5):
            gx = base_x + dx
            gy = base_y + dy
            if not (0 <= gx < MEGA_W and 0 <= gy < MEGA_H):
                continue
            # Skip base itself
            if (gx, gy) in [(base_x, base_y), (base_x+1, base_y), (base_x, base_y+1), (base_x+1, base_y+1)]:
                continue
            # Outer thick steel fort - 2 layers
            dist = max(abs(dx-0.5), abs(dy-0.5))
            if dist <= 1.5:
                # inner ring - steel (will be replaced with brick by default, keep steel for strong fort)
                continue  # will be brick or empty for passage
            if dist <= 3:
                tilemap[gy][gx] = TILE_STEEL
    # Create openings (north, south, east, west) for access
    openings = [
        (base_x, base_y-3), (base_x+1, base_y-3),  # north openings
        (base_x, base_y+4), (base_x+1, base_y+4),  # south
        (base_x-3, base_y), (base_x-3, base_y+1),  # west
        (base_x+4, base_y), (base_x+4, base_y+1),  # east
    ]
    for gx, gy in openings:
        if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
            tilemap[gy][gx] = TILE_EMPTY
    # Inner brick walls for extra layers (closer to base)
    inner_brick = [
        (base_x-1, base_y-1), (base_x, base_y-1), (base_x+1, base_y-1), (base_x+2, base_y-1),
        (base_x-1, base_y), (base_x+2, base_y),
        (base_x-1, base_y+1), (base_x+2, base_y+1),
        (base_x-1, base_y+2), (base_x, base_y+2), (base_x+1, base_y+2), (base_x+2, base_y+2),
    ]
    for gx, gy in inner_brick:
        if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
            if tilemap[gy][gx] == TILE_EMPTY:
                tilemap[gy][gx] = TILE_BRICK

def add_random_obstacles(tilemap, density=0.15, seed=None):
    if seed is not None:
        random.seed(seed)
    for y in range(MEGA_H):
        for x in range(MEGA_W):
            # Skip base area (center 10x10)
            if abs(x - BASE_CX) < 6 and abs(y - BASE_CY) < 6:
                continue
            # Skip player and enemy spawns
            if x < 4 and y < 4:
                continue
            if x > MEGA_W-5 and y < 4:
                continue
            if x < 4 and y > MEGA_H-5:
                continue
            if x > MEGA_W-5 and y > MEGA_H-5:
                continue
            if x in [8, 9, 42, 43] and y > 45:
                continue
            if random.random() < density:
                tilemap[y][x] = random.choice([TILE_BRICK, TILE_BRICK, TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_GRASS, TILE_ICE])

def add_symmetric_pattern(tilemap, pattern_type="maze", seed=0):
    random.seed(seed)
    if pattern_type == "labyrinth":
        # Create maze-like walls
        for y in range(0, MEGA_H, 4):
            for x in range(0, MEGA_W, 4):
                if abs(x - BASE_CX) < 8 and abs(y - BASE_CY) < 8:
                    continue
                if random.random() < 0.6:
                    # 2x2 block
                    t = random.choice([TILE_BRICK, TILE_STEEL])
                    for dy in range(2):
                        for dx in range(2):
                            gx = x+dx
                            gy = y+dy
                            if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                                if abs(gx-BASE_CX) > 5 or abs(gy-BASE_CY) > 5:
                                    tilemap[gy][gx] = t
    elif pattern_type == "city":
        # City grid with roads
        for gy in range(0, MEGA_H, 6):
            for gx in range(MEGA_W):
                if abs(gx-BASE_CX) < 6 and abs(gy-BASE_CY) < 6:
                    continue
                if gy % 6 == 0:
                    continue  # road horizontal
                if gx % 8 == 0:
                    continue  # road vertical
                if random.random() < 0.3:
                    tilemap[gy][gx] = TILE_BRICK
        # Add some water rivers
        river_y = MEGA_H // 3
        for x in range(MEGA_W):
            for dy in range(2):
                if 0 <= river_y+dy < MEGA_H:
                    if not (abs(x-BASE_CX) < 7 and abs(river_y+dy-BASE_CY) < 7):
                        if random.random() < 0.7:
                            tilemap[river_y+dy][x] = TILE_WATER
    elif pattern_type == "forest":
        for _ in range(8):
            cx = random.randint(5, MEGA_W-6)
            cy = random.randint(5, MEGA_H-6)
            if abs(cx-BASE_CX) < 8 and abs(cy-BASE_CY) < 8:
                continue
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    if dx*dx+dy*dy < 16 and random.random() < 0.7:
                        gx = cx+dx
                        gy = cy+dy
                        if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                            tilemap[gy][gx] = TILE_GRASS
    elif pattern_type == "fortress":
        # Multiple steel forts around
        forts = [(10,10), (40,10), (10,40), (40,40), (10,25), (40,25)]
        for fx, fy in forts:
            for dy in range(-2,3):
                for dx in range(-2,3):
                    gx = fx+dx
                    gy = fy+dy
                    if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                        if abs(gx-BASE_CX) < 6 and abs(gy-BASE_CY) < 6:
                            continue
                        if abs(dx)==2 or abs(dy)==2:
                            tilemap[gy][gx] = TILE_BRICK if random.random()<0.7 else TILE_STEEL
    elif pattern_type == "chaos":
        # Random but balanced
        add_random_obstacles(tilemap, density=0.22, seed=seed)

def generate_mega_level(index):
    """Generate a specific mega level by index"""
    m = create_empty_mega()
    
    # Always build center base fort
    build_center_base_steel_fort(m, BASE_CX, BASE_CY)
    
    # Add pattern based on index
    patterns = ["labyrinth", "city", "forest", "fortress", "chaos", "labyrinth", "city", "forest"]
    pattern = patterns[index % len(patterns)]
    
    # Expand original 26x26 level into 52x52 quadrants with variations
    try:
        from .battle_city import LEVELS_26
        if index < len(LEVELS_26):
            # Place original level in top-left quadrant scaled, and mirrored variants in other quadrants
            orig = LEVELS_26[index % len(LEVELS_26)]
            # Top-left: original 26x26 -> 0,0 to 25,25 but avoid base center overlap
            for y in range(26):
                for x in range(26):
                    if abs(x-12) < 8 and abs(y-12) < 8:
                        continue  # don't place over what will be center after shift
                    gx = x
                    gy = y
                    if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                        if m[gy][gx] == TILE_EMPTY:
                            t = orig[y][x]
                            # Skip if would overwrite base area in mega
                            if abs(gx-BASE_CX) < 6 and abs(gy-BASE_CY) < 6:
                                continue
                            m[gy][gx] = t
            # Bottom-right: mirrored original
            for y in range(26):
                for x in range(26):
                    gx = x+26
                    gy = y+26
                    if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                        if abs(gx-BASE_CX) < 6 and abs(gy-BASE_CY) < 6:
                            continue
                        if m[gy][gx] == TILE_EMPTY:
                            m[gy][gx] = orig[y][x] if random.random() < 0.8 else TILE_EMPTY
    except:
        pass
    
    add_symmetric_pattern(m, pattern, seed=index*100)
    
    # Add extra random for density
    add_random_obstacles(m, density=0.08, seed=index*50)
    
    # Ensure paths to base are not fully blocked - create corridors
    # North corridor
    for y in range(0, BASE_CY-2):
        m[y][BASE_CX] = TILE_EMPTY
        m[y][BASE_CX+1] = TILE_EMPTY
    # South corridor (below base)
    for y in range(BASE_CY+5, MEGA_H):
        m[y][BASE_CX] = TILE_EMPTY
        m[y][BASE_CX+1] = TILE_EMPTY
    # East-west
    for x in range(0, BASE_CX-2):
        m[BASE_CY][x] = TILE_EMPTY if x % 3 != 0 else m[BASE_CY][x]
        m[BASE_CY+1][x] = TILE_EMPTY if x % 3 != 0 else m[BASE_CY+1][x]
    for x in range(BASE_CX+5, MEGA_W):
        m[BASE_CY][x] = TILE_EMPTY if x % 3 != 0 else m[BASE_CY][x]
        m[BASE_CY+1][x] = TILE_EMPTY if x % 3 != 0 else m[BASE_CY+1][x]
    
    # Clear spawns
    spawns = [(0,0), (25,0), (50,0), (0,25)]
    for sx, sy in spawns:
        for dy in range(4):
            for dx in range(4):
                gx = sx+dx
                gy = sy+dy
                if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                    if abs(gx-BASE_CX) > 5 or abs(gy-BASE_CY) > 5:
                        if (gx, gy) not in [(BASE_CX, BASE_CY), (BASE_CX+1, BASE_CY), (BASE_CX, BASE_CY+1), (BASE_CX+1, BASE_CY+1)]:
                            # keep spawn area empty
                            if gx < 4 or gy < 4 or gx > MEGA_W-5 or gy > MEGA_H-5:
                                m[gy][gx] = TILE_EMPTY
    # Player spawns bottom
    for px, py in [(8,48), (42,48)]:
        for dy in range(-2, 4):
            for dx in range(-2, 4):
                gx = px+dx
                gy = py+dy
                if 0 <= gx < MEGA_W and 0 <= gy < MEGA_H:
                    m[gy][gx] = TILE_EMPTY
    
    return m

# Generate 35 mega maps
MEGA_LEVELS_52 = [generate_mega_level(i) for i in range(35)]

# Also create scaled versions of original 13x13 for compatibility
MEGA_LEVELS_13 = []  # We'll keep 13x13 for preview compatibility, but use 52x52 as main
for i in range(35):
    try:
        from .battle_city import LEVELS_13
        if i < len(LEVELS_13):
            MEGA_LEVELS_13.append(LEVELS_13[i])
        else:
            MEGA_LEVELS_13.append(LEVELS_13[0])
    except:
        # minimal
        MEGA_LEVELS_13.append([[0]*13 for _ in range(13)])

# Enemy queues for mega - more enemies because 4x map
MEGA_ENEMY_QUEUES = []
try:
    from .battle_city import ENEMY_QUEUES
    for q in ENEMY_QUEUES:
        # Double enemies for mega maps
        MEGA_ENEMY_QUEUES.append(q + q[:len(q)//2])
except:
    # fallback 40 enemies each
    MEGA_ENEMY_QUEUES = [['basic']*20 + ['fast']*10 + ['power']*5 + ['armor']*5 for _ in range(35)]

MEGA_STAGE_COUNT = 35
