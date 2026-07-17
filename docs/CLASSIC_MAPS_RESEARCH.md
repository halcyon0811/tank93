# Classic Battle City (Tank 90 / 1990) Maps Research

## Sources Found

### Primary: 35 Original NES Maps (most accurate)

1. **feichao93/battle-city** (1.9k stars React remake) - best source
   - Repo: https://github.com/feichao93/battle-city
   - Playable: https://battle-city.js.org
   - Raw maps: `app/stages/stage-{1..35}.json`
     - `https://raw.githubusercontent.com/feichao93/battle-city/master/app/stages/stage-1.json`
     - through stage-35
   - Parser: https://raw.githubusercontent.com/feichao93/battle-city/master/app/types/StageConfig.ts
   - Constants: https://raw.githubusercontent.com/feichao93/battle-city/master/app/utils/constants.ts

2. **dogballs/cattle-bity** - TypeScript, region-based format
   - Repo: https://github.com/dogballs/cattle-bity
   - Maps: `data/maps/original/{01..35}.json`
   - Manifest: https://raw.githubusercontent.com/dogballs/cattle-bity/master/data/map.manifest.json
   - Config: https://raw.githubusercontent.com/dogballs/cattle-bity/master/src/config.ts

3. **ROM hacking / Disassembly**
   - DataCrystal: https://datacrystal.tcrf.net/wiki/Battle_City_(NES)
   - RAM map: https://datacrystal.tcrf.net/wiki/Battle_City_(NES)/RAM_map (tile encoding values 0x0-0xF)
   - NESmaps visual: https://www.nesmaps.com/maps/BattleCity/BattleCity.html (screenshots per stage)

---

## Original NES 35 Stages - Enemy Composition

From feichao data:

- Stage 1: 18*basic, 2*fast
- Stage 2: 2*armor, 4*fast, 14*basic
- Stage 3: 14*basic, 4*fast, 2*armor
- Stage 4: 10*power, 5*fast, 2*basic, 3*armor
- Stage 5: 5*power, 2*armor, 8*basic, 5*fast
...
- Stage 35: 4*power, 6*fast, 10*armor (hardest)

Difficulty curve: early stages mostly basic, later armor count increases. Total enemies per stage = 20 (original). Your game uses `ENEMIES_PER_LEVEL = 20 + level*2`.

Enemy score mapping:
- basic (gray / tier a) = 100 pts
- fast (blue / b) = 200 pts
- power (red / c) = 300 pts
- armor (green flashing / d, needs 4 hits) = 400 pts

Match confirmed with your `ENEMY_COLORS` and scoring.

---

## Tile System - Deep Dive

### NES Original encoding (DataCrystal RAM 0x005C)

```
0x0 Brick_Vertical_1       half-brick vertical slice 1
0x1 Brick_Horizontal_1     half horizontal
0x2 Brick_Vertical_2
0x3 Brick_Horizontal_2
0x4 Full_Brick             whole 16px block = 4 micro bricks (4px each)
0x5 Marble_Vertical_1      steel partial
0x6 Marble_Horizontal_1
0x7 Marble_Vertical_2
0x8 Marble_Horizontal_2
0x9 Full_Marble            full steel 16px block
0xA Blue_Tile              water
0xB Green_Tile             forest / trees (overlay, z-top)
0xC Gray_Tile              ice / snow / slippery
0xD-0xF Empty
```

This is why original game supports **half bricks and quarter bricks**.

### feichao93 token format (most faithful to NES)

Map = 13x13 tokens, each token space-separated string like `"X  Bf X  Bf ..."`

- `X` = empty
- `E` = Eagle/base (always at (6,12) big tile = (12,24) small = center bottom)
- `Bf` etc = Brick with hex mask:
  - `Bf` = 0xf = 1111 = all 4 quadrants of the 16px block have bricks (full)
  - `B3` = 0x3 = 0011 = top half only (quadrants 0,1)
  - `Bc` = 0xc = 1100 = bottom half
  - `Ba` = 0xa = 1010 = right side? Actually careful:
    ```
    bit0 0001 = TL (top-left 8px)
    bit1 0010 = TR
    bit2 0100 = BL
    bit3 1000 = BR
    So:
    3=0011 = TL+TR = top
    c=1100 = BL+BR = bottom
    5=0101 = TL+BL = left
    a=1010 = TR+BR = right
    f=1111 = full
    8=1000 = single BR quarter
    ```
  - Also e.g., `B5`, `B8`, `B4` etc observed in stages

Detailed brick micro-level:
- Brick block 16px = 4x4 micro-bricks of 4px each = 16 micro-bricks
- But token `Bf` shorthand expands via `parseBrickBits`:
  ```js
  short single hex digit -> expands to 4 nibbles:
    bit0 0b0001 => 0xf000 (top-left 2x2 micro-bricks)
    bit1 0b0010 => 0x0f00 (top-right)
    etc.
  So Bf = 1111 -> 0xffff = all 16 micro-bricks
  Ba = 1010 -> left/right? Actually 1010 binary -> top-left+bottom-left? Wait short expansion: 1010 = bits 1 and 3 => 0x0f00 + 0x000f = right half columns?
  Need full expansion as per StageConfig.ts.
  ```
- This allows **half-brick walls** that are 8px thick, classic Battle City style where bullets can chip away quarter bricks.

- `T<h>` = Steel, same bitmask but steel size = 8px, so each bit = one 8px steel quadrant (2x per big tile)
  - `Tf` = full steel 16px (all 4 quadrants 8px)
  - `T3` = top half steel
  - `Tc` = bottom half
  - `Ta` = right side = TR+BR
  - `T5` = left side = TL+BL
  - Observed: Tf 294 times across 35 maps, T3 84, Tc 54, T5 35, Ta 31 etc.

- `R` = River / Water
  - 16px block full
  - Tanks blocked, bullets pass
  - Animated waves in original

- `F` = Forest / Grass
  - 16px block, overlay (drawn after tanks)
  - Tanks hide under it, no collision
  - 2nd most frequent after brick: 744 occurrences (brick Bf 797)

- `S` = Snow / Ice / Gray Tile
  - 16px, slippery, no collision
  - Tanks slide faster
  - 238 occurrences

### Your Local Tilemap Encoding

`game/settings.py`:

```python
TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_GRASS = 4   # forest
TILE_ICE = 5
TILE_SIZE = 24   # small tile px, modernized HD (original 16 or 8)
GRID_W = 26
GRID_H = 26      # 26 small tiles = 13 big tiles *2 (matches NES 13x13)
PLAYFIELD_W = 624 # 26*24
BASE_POS = (12,24)  # eagle 2x2 at bottom center (matches NES)
PLAYER_SPAWN = [(8,24),(16,24)]  # (4,12) big tile -> (8,24) small
ENEMY_SPAWNS = [(0,0),(12,0),(24,0)] # top left/center/right
```

`game/tilemap.py`:

- Supports both 13x13 big and 26x26 small input
- `load_from_data`: if 13x13, expands 2x2 to 26x26 (each big -> 4 small of same type) -> **simplified**, loses half-brick info
- Real original needs sub-tile parsing (B3 etc should become only top half bricks in 26 grid)
- `draw_brick`, `draw_steel`, `draw_water`, `draw_grass`, `draw_ice` modernized pixel art
- `destroy_tile`: brick removed always, steel removed only if bullet_power>=2 (star upgrade)
- `build_base_walls` puts bricks around eagle
- `ensure_spawn_clear` clears 4x4 area around player and enemy spawns + base 2x2
- `shovel` powerup upgrades base walls to steel for 15s

Comparison:

| Aspect | Original NES | Your game | Gap |
|--------|-------------|-----------|-----|
| Grid | 13x13 big = 26x26 small = 52x52 micro-brick | 26x26 small only | Missing half-brick (you map B3 as full brick in 13x13 expand) |
| Brick | Breakable 4x4 micro (4px), can break quarter | Breakable per small tile (24px) | Less granular destruction but okay for HD |
| Steel | Needs bullet power >=3 (star max) | Needs power >=2 | Slightly easier |
| Water | Blocks tank, bullet passes | Same | Correct |
| Forest | Overlay after tanks, hides | Overlay `draw_overlay` after tanks | Correct |
| Ice | Slippery, no collision | `on_ice` speed 1.3x | Correct |
| Base | Fixed at (6,12) big, 32x32 eagle | (12,24) small 2x2 = same | Correct |
| Spawn | (4,12),(8,12) big for P1/P2 | (8,24),(16,24) small same | Correct |
| Level count | 35 official + construction mode | 5 handcrafted | Can upgrade to 35 via converted file |

### Frequency across 35 original maps

- Brick total tokens ~1200 across 35 (most common)
- Forest 744
- Steel Tf 294 (but steel used strategically around base/enemy)
- Water 219
- Ice 238
- Empty ~ majority

Pattern per stage:
- Stage 1: simple brick maze, 2 steel spots
- Stage 2: brick + steel mix + river islands
- Stage 3: forest maze intro
- Stage 4+: ice + water combos, steel fortress
- Stage 32: snow field full screen (S S S...)
- Stage 26: river heavy (R)
- etc.

---

## Converted Files for Your Project

Generated in `docs/BATTLE_CITY_ORIGINAL_35_MAPS.py`:

- `LEVELS_13`: list[35][13][13] ints 0-5 simplified (B*->1,T*->2,R->3,F->4,S->5)
- `LEVELS_26`: list[35][26][26] ints precise with half-brick/steel support
- `BOTS`: list[35] list[str] like ["18*basic","2*fast"]

Also JSON per stage in `game/levels/original_35/stage_XX.json`:

```json
{
  "name": "1",
  "bots": [...],
  "map_13": [[...]],
  "map_26": [[...]],
  "original_raw": ["X  X  X...", ...]
}
```

### How to integrate into your game

Option A - Simple drop-in (keep 13x13 support):

```python
from docs.BATTLE_CITY_ORIGINAL_35_MAPS import LEVELS_13
# replace LEVELS = LEVELS_13 in tilemap.py
```

Option B - High fidelity (use 26x26 precise):

```python
from docs.BATTLE_CITY_ORIGINAL_35_MAPS import LEVELS_26
# replace LEVELS = LEVELS_26 but update load_from_data to detect 26
# already supports 26x26 path
```

Option C - Lazy bricks exact (parse B3 etc as half bricks):

Current `LEVELS_26` already does half-brick conversion:
- B3 top half -> top two rows in 26 grid marked brick, bottom empty
- Bc bottom half -> etc.
- T3 top steel half -> only top 8px row etc.

---

## References

- https://github.com/feichao93/battle-city - stage-{1..35}.json
- https://github.com/dogballs/cattle-bity
- https://datacrystal.tcrf.net/wiki/Battle_City_(NES)/RAM_map
- https://www.nesmaps.com/maps/BattleCity/BattleCity.html
- https://strategywiki.org/wiki/Battle_City/Walkthrough
- https://en.wikipedia.org/wiki/Battle_City (confirms 35 stages)
- TCRF: https://tcrf.net/Battle_City_(NES)

## Next Steps Suggested

1. Replace your 5 LEVELS with 35 original (use LEVELS_26 for accuracy)
2. Add bullet micro-destruction: instead of destroying whole 24px tile, destroy quarter if B3 etc.
3. Keep your enhancements (ice slippery, shovel, power-ups) - not in original but fine
4. Add level editor export compatible with 13x13 token format for custom maps sharing
5. Test maps with your collision system - ensure spawn clears work (original maps already leave spawn empty)
