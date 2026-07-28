# Web Sync Contract - Python ↔ Web-Pure

**Status:** Living doc. Enforced by `scripts/generate_web_assets.py` + CI checks.
**Last audit:** 2026-07-19 - 15 divergences found

## Philosophy

- **Python (desktop) = Source of Truth** for gameplay logic, maps, settings, balance
- **Web-pure (JS) = Derived** - must sync via codegen, not manual copy
- **Shared taxonomy, separate implementation** for logging & tests
- **Maps already synced**, but need automated generation to prevent drift

---

## 1. Asset Sync Pipeline

| Asset | Source (Python) | Generated (Web) | Generator | Auto? |
|-------|----------------|-----------------|-----------|-------|
| Maps 26x26 | `game/levels/battle_city.py` LEVELS_26 | `web-pure/assets/maps.json` levels_26 | `generate_web_assets.py` | `npm run sync-assets` + CI |
| Maps 13x13 | LEVELS_13 | levels_13 | same | same |
| Enemy queues | ENEMY_QUEUES from battle_city.py (BOTS_RAW) | maps.json.queues | same | same |
| Settings | `game/settings.py` all constants | `web-pure/assets/settings.json` | same | same |
| Sprites | `game/assets/General-Sprites.png` | `web-pure/assets/images/General-Sprites.png` | copy | same |
| Sounds | `game/assets/sounds/*.ogg` + real/*.wav | web-pure assets (optional) | manual | future |

### Running sync

```bash
python scripts/generate_web_assets.py      # regenerates maps.json + settings.json
# or from web-pure:
cd web-pure && npm run sync-assets
```

CI will FAIL if generated files differ from committed (prevents drift).

### Settings included in settings.json

Should include ALL gameplay constants, not just 8:
- SCREEN, TILE_SIZE, GRID, PLAYFIELD, BASE_POS, SPAWNS
- TANK_SIZE, TANK_SPEED, BULLET_SPEED, BULLET_SIZE
- ARMOR_INITIAL, ARMOR_MAX, BRICK_HITS_NEEDED, STEEL_HITS_NEEDED
- HOMING_* (speed, max_dist, turn, detection, astar interval, avoidance, margins)
- VENOM_* (dissolve, speed, spillover radius/interval/damage/factors)
- BOMB_*, SHRINK_*, GIANT_*, MONSTER_*
- POWERUP_TYPES, POWERUP_DURATION, STAR_LEVELS
- PLAYER_NAMES, COLORS, etc...
- See `generate_web_assets.py` for full list

---

## 2. Logic Parity Checklist (must pass E2E)

### Tier 1: Critical (crash / stuck)
- [ ] **TileMap.destroyTile**: direction-aware? Python now single tile + health; JS had old 2-tile heuristic → OUTDATED
- [ ] **Enemy spawn separation**: distance > 1.8*TANK_SIZE + push apart
- [ ] **Tank tryMove**: clamp inside playfield, slide through 1-tile gap offsets 4/8/12
- [ ] **Base**: release boss clears only 2x2 NOT 4x4, boss trapped then crushes steel+brick to escape
- [ ] **Boss escape detection**: distance >3 tiles from base → log BOSS_ESCAPED + homing prioritizes boss

### Tier 2: Gameplay balance
- [ ] **Armor system**: player 100-300, enemy 40-400, absorbs damage, flash when hit, HUD bar
- [ ] **Brick durability**: normal 2 hits, power 1, rapid 3, homing 4, power_homing 1 etc
- [ ] **Steel durability**: normal 5, power 3→2 after -1 reduction, rapid 8, homing 6, etc.
- [ ] **Homing missile**: speed 3.56 not 6.5, turn 0.068 not 0.18, fuel limit 574px, LOS check, A* 26x26 waypoints, avoidance, boss priority 0.5*dist
- [ ] **Spread+homing**: BOTH fire = 8 spread non-homing + 1-3 homing (level based), not merged 8 homing
- [ ] **Venom**: speed 0.45*bullet, dissolve 18s 1080 frames, spillover radius 72 every 20 frames, factor enemy 1.0 player 0.5 boss 0.7, infect other player 20% half duration
- [ ] **Shrink/Giant**: 0.5 scale 2x speed, 2.0 scale crush bricks+enemies, 15s duration, synergy both => 1.0 fast crush
- [ ] **Bullet counter**: player bullets counters enemy bullets if dist<BULLET_SIZE+3 power>=2
- [ ] **Forest hiding**: enemy 100% hidden in forest, player 18% faint silhouette after overlay + rustle particles
- [ ] **Boss free-for-all**: owner='boss' hits both players and enemies
- [ ] **Bomb (grenade)**: armor damage 100 each enemy, explode only if armor gone, power damage 2

### Tier 3: Polish / parity
- [ ] **Sprites**: DIR_OFFSETS RIGHT=6 LEFT=2 fixed, 8-dir rotation via canvas rotate, anim frame move_timer//6%2
- [ ] **Stacking**: total_items_collected, homing/spread/rapid level, star_extra_count beyond max, bullet_damage_bonus + speed_bonus
- [ ] **Input**: 8-dir WASD combos, ice sliding inertia, per Joy-Con calibration SWAP+INV_Y, cross-control fix
- [ ] **Particles**: explosion, hit, spawn, crush, venom drips
- [ ] **HUD**: Stage 35, enemy 20/20 max 4 spawn 2.5s, PWR index, Chad/Lida names, HP rename, Armor bar, boss HP 18 not 12
- [ ] **Fullscreen**: canvas scaled to screen, not small corner (Python uses SCALED flag)
- [ ] **Sound**: 53 sounds via Web Audio, intro music on stage 0 only, no BGM in battle (authentic NES)

---

## 3. Logging - Shared Taxonomy, Separate Implementation

### Why separate?
- Python can afford SQLite WAL 64MB cache + async thread (0-latency, <2ms query on 100k rows, no frame drop)
- JS cannot: SQLite in browser impossible efficiently, need ring buffer + IndexedDB/localStorage + ?debug overlay
- But same tags/event_types so agent can query both mentally

### Shared Tags (canonical)

Defined in `docs/LOG_EVENT_SCHEMA.md` (source of truth for both):

**Sections:**
- `STATE`: playing->menu bounce, old/new/reason/stack
- `INPUT`: key/joy/gamepad
- `NETWORK`: Lida remote, broadcast fallback, No route
- `STUCK`: EDGE_BLOCK, AUTO_CLAMP, PLAYER_STUCK
- `STEEL`: STEEL_DESTROY, STEEL_CHIP, BRICK_DESTROY with is_steel
- `WEAPON`: WEAPON_COMBINED_SHOOT, SYNERGY_POWER_HOMING, PWR_UPDATE
- `PERF`: STARTUP_INIT, NETWORK_STARTUP, PROJECTOR_STARTUP, FPS sampled every 30 frames
- `MAP`: MAP_GRID_NAV, MAP_SELECT, grid-aware nav 7 cols
- `HUD`: HUD_PAUSE_BUTTON_CLICK, HUD_COIN_BUTTON_CLICK
- `GAMEPLAY`: ENEMY_SPAWN, BOSS_RELEASE_TRAPPED, BOSS_ESCAPED, BOSS_DEFATED, BASE_DAMAGE, VENOM_SPILLOVER, FOREST_HIDE, etc.
- `CRASH`: full traceback
- `BOSS`: BOSS_RELEASE, BOSS_ESCAPED, BOSS_CRUSH

### Implementation per platform

| Feature | Python (desktop) | Web Pygbag (wasm) | Web-Pure JS |
|---------|------------------|------------------|-------------|
| Storage | debug.db SQLite WAL + bug_trace.log | MEMFS ephemeral (no-op mode recommended) | Ring buffer 500 + localStorage + ?debug overlay |
| Writer | Async thread queue 10k | no-op or console.log bridge via pyodide_js | sync push + IndexedDB optional |
| Query CLI | debug_query.py + debug_report.py | N/A | window.logger.query() in console + export button |
| Lifespan | prune keep 20 sessions | single session per load | per load, exportable |
| Overhead | <0.1ms | ~0 | <0.1ms |
| Capture | inputs, state, gameplay, perf, exceptions, network, edge, steel, weapon, map, hud | same if enabled | same but JS categories |

### Dashboard Idea (future)

- ?debug=1 in URL shows overlay: last 50 events, FPS, enemy count, boss HP, markers for stuck/brick/boss
- Export button: downloads debug_logs.json for upload to issue tracker
- Console helper: `logger.tail(50)`, `logger.query({tag:'BOSS'})`, `logger.report()`

---

## 4. E2E Tests - Separate Runners, Mirrored Scenarios

### Python (existing, excellent - keep)

- **Runner**: pytest + SDL_VIDEODRIVER=dummy (headless)
- **Fixtures**: conftest.py clean_db, game fixture waits 2s for async network host
- **Tests (26)**: 
  - test_full_game_400_frames_no_crash (assert no bounce, no exception)
  - test_boss_escape_and_homing_track
  - test_2p_life_share
  - test_venom_spillover
  - test_stage_clear_flow
  - test_fuzz_monkey_no_crash (500 random keys)
  - test_no_stuck (5): inside playfield, not inside brick/steel, edge slide, 1-tile gap passable, steel destructible
  - test_collision (5): brick destroy pass-through, edge slide, overlap unstick, stuck-shoots-and-recovers, giant crush
  - test_bullets (5): bomb armor, homing chip, boss both, weapon stacking
  - test_menu_navigation (5): LEFT/RIGHT, JOYHAT, 1P restart with Lida, pause robust, kick Lida via N

**CI**: .github/workflows/test.yml matrix 3.10/3.11 ubuntu, fails → debug_report.py + stats + bounce + errors, upload debug.db artifact

### Web-Pure (new, to build)

- **Runner**: Playwright + Vitest
- **Package**: web-pure/package.json with scripts: test (vitest unit), e2e (playwright), sync-assets (python ../scripts/generate_web_assets.py)
- **Structure**:
  ```
  web-pure/
    src/                # ESM modules split from game.js monolith (to enable unit tests)
      tilemap.js
      tank.js
      player.js
      enemy.js
      bullet.js
      powerup.js
      logger.js         # ring buffer logger
      constants.js      # generated from settings.json? or import
    tests/
      unit.test.js      # TileMap, Tank logic without canvas
      e2e.spec.js       # Playwright: load index.html, press Enter, 400 frames no crash, check HUD
      no-stuck.spec.js  # mirror test_no_stuck
      collision.spec.js # mirror test_collision
      bullets.spec.js   # mirror test_bullets
    assets/
      maps.json         # generated
      settings.json     # generated
  ```

- **Mirrored scenarios** (same as Python, but JS API):

| Python Test | Web Equivalent | How |
|-------------|----------------|-----|
| test_full_game_400_frames_no_crash | e2e: 400 ticks no console.error, state != error | Playwright evaluate: window.game.state |
| test_boss_escape_and_homing_track | e2e boss release, homing tracks boss | Simulate brick destroy around base, shoot homing, assert dist decreases |
| test_2p_life_share | N/A (needs 2 players) or simulate both WASD+arrows | Press L / emulate share |
| test_venom_spillover | venom infects nearby enemy | Venom bullet hits, check other tank venom_timer >0 |
| test_stage_clear_flow | stage clear → next stage | Kill all enemies, assert level_idx increment |
| test_fuzz_monkey | fuzz random keys 500 frames no crash | random WASD + SPACE |
| test_no_stuck (inside playfield) | tank bounds inside PLAYFIELD | assert x in [PLAYFIELD_X, PLAYFIELD_X+W] for all frames |
| test_no_stuck (not inside brick) | not overlapping solid tiles | same collision check |
| test_no_stuck (edge slide) | edge UP must move | place tank near edge, move UP, assert y changes |
| test_no_stuck (1-tile gap) | destroyed brick gap passable | destroy one brick, slide with offsets |
| test_no_stuck (steel destructible) | steel 5 hits normal 2 power | shoot 5 times |
| test_collision brick destroy | same | JS unit |
| test_collision edge slide | same | JS unit |
| test_collision overlap unstick | dist>30 after 30 updates | JS unit |
| test_collision stuck-shoots-recovers | stuck >25 shoot forward | JS unit |
| test_collision giant crush | giant crushes brick | JS unit |
| test_bullets bomb armor | bomb 100 armor | JS unit |
| test_bullets homing chip | homing chip/destroy | JS unit |
| test_bullets boss both | boss bullet hits both sides | JS unit |
| test_bullets weapon stacking | stacking | JS unit |
| test_menu nav | LEFT/RIGHT | JS e2e key press |

**CI for web**: New job in same workflow or separate web.yml:
```yaml
web-tests:
  runs-on: ubuntu-latest
  steps:
    - checkout
    - setup-node 20
    - run: cd web-pure && npm ci && npm run test && npx playwright install && npx playwright test
    - if failure: upload playwright-report + web-debug-logs
    - sync check: python scripts/generate_web_assets.py --check (fail if dirty)
```

---

## 5. Publishing

- **Itch.io**: pygbag build (Python WASM) for authentic, web-pure as fallback
- **GitHub Pages**: serve web-pure/ as https://halcyon0811.github.io/tank93/web-pure/
- **Workflow**: on push main, deploy web-pure to gh-pages (upload-pages-artifact)

---

## 6. Migration Path

1. **Phase 1 (now)**: Asset pipeline + logger.js + LOG_EVENT_SCHEMA.md + sync doc (this file)
2. **Phase 2**: Split game.js monolith into ESM src/ + add package.json + unit tests (mirror no_stuck, collision, bullets)
3. **Phase 3**: Playwright e2e mirroring 400_frames, boss, venom, stage clear + CI job
4. **Phase 4**: Fix Tier 1 divergences (boss trapped, spawn sep, homing speed)
5. **Phase 5**: Tier 2 balance (armor, brick health, homing A*, venom spillover, shrink/giant)
6. **Phase 6**: Tier 3 polish + visual parity + sound

Each fix must have corresponding unit/e2e test + log event.

---

## 7. What NOT to share

- **Do NOT** try to share SQLite implementation in JS (keep separate)
- **Do NOT** share Python Game loop directly in JS (different rendering, input)
- **Do NOT** manually copy constants (use generator)
- **Do NOT** copy-paste game.js logic to Python or vice versa without adding test + log

---

## 8. Quick Reference

```bash
# Sync assets from Python truth to web
python scripts/generate_web_assets.py
# Check drift (CI)
python scripts/generate_web_assets.py --check

# Python tests
pytest tests/ -v

# Web tests (once implemented)
cd web-pure
npm i
npm run sync-assets
npm test                # vitest unit
npm run e2e             # playwright e2e
npm run e2e -- --headed # with browser

# Logs
python debug_report.py
python -m game.debug_logger stats
python debug_query.py --last --bounce

# Web logs (future)
# Open web-pure/index.html?debug=1
# Console: logger.report(), logger.query({tag:'BOSS'}), logger.export()
```
