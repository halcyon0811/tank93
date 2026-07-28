# Log Event Schema - Shared Taxonomy for Python & Web-Pure

**Source of truth** for both `game/debug_logger.py` (Python) and `web-pure/src/logger.js` (JS).
All logs use same tag names, event types, levels, so agent can query cross-platform mentally.

## Levels

```
DEBUG < INFO < WARN < ERROR < FATAL
```

- DEBUG: verbose per-frame
- INFO: normal operations (spawn, shoot, nav)
- WARN: recoverable issues (bounce playing->menu, stuck, outside map warning)
- ERROR: exception caught but recovered
- FATAL: crash, unrecoverable, session ends

## Tables / Storage

| Concept | Python | Web JS |
|---------|--------|--------|
| sessions | SQLite sessions table | sessionId in memory + localStorage |
| events | events table | ring buffer 1000 + localStorage |
| state_changes | state_changes table | state_changes [] |
| gameplay | gameplay table | gameplay [] |
| perf_samples | perf_samples table | perf [] sampled every 30 frames |
| inputs | inputs table | inputs [] throttled |
| exceptions | exceptions_log table | exceptions [] + window.onerror |

## Tags (first-level)

Used in `log_event(tag, message)` or `logger.log_event(tag,...)`

| Tag | Purpose | Examples |
|-----|---------|----------|
| INIT | startup, asset load | Game init complete, maps loaded 35 |
| STATE | state machine | menu->playing, playing->gameover |
| INPUT | player input | KEYDOWN WASD, JOYBUTTON, GAMEPAD |
| NETWORK | Lida remote, LAN | LIDA_CONNECTED, BROADCAST_FALLBACK_ACTIVE, No route |
| STUCK | edge/stuck detection | EDGE_BLOCK, AUTO_CLAMP, PLAYER_STUCK, SLIDE_THROUGH_GAP |
| STEEL | brick/steel durability | STEEL_DESTROY, STEEL_CHIP, BRICK_DESTROY is_steel |
| WEAPON | weapon stacking/synergy | WEAPON_COMBINED_SHOOT, SYNERGY_POWER_HOMING, PWR_UPDATE |
| PERF | performance | STARTUP_INIT, FPS, NETWORK_STARTUP |
| MAP | map select grid | MAP_GRID_NAV, MAP_SELECT |
| HUD | hud clicks + updates | HUD_PAUSE_CLICK, HUD_COIN_CLICK, HUD_PWR_UPDATE |
| BOSS | boss lifecycle | BOSS_RELEASE_TRAPPED, BOSS_ESCAPED, BOSS_DEFEATED, BOSS_CRUSH |
| CRASH | unhandled exception | stack trace |
| MAP_LOAD | asset loading | maps.json loaded 35 stages |
| SOUND | sound system | distant_tank_shots loaded |
| EDGE | edge clamping | CLAMP_OUTSIDE, SPAWN_CLAMP |
| GAMEPLAY | generic gameplay | ENEMY_SPAWN, BASE_DAMAGE, LEVEL_INIT |

## Gameplay Event Types (second-level, in gameplay table / array)

| Event Type | Level context | Data fields |
|------------|---------------|-------------|
| SESSION_START | - | screen_w, screen_h, is_mega, joysticks |
| LEVEL_INIT | level_idx | num_players, enemies_total, max_on_field, spawn_interval |
| ENEMY_SPAWN | level_idx | type, grid_x, grid_y, spawned, total, on_field, carrier |
| ENEMY_KILLED | level_idx | type, player_id, score, position |
| PLAYER_HIT | level_idx | player_id, attacker, damage, armor_left |
| PLAYER_DIE | level_idx | player_id, lives_left |
| PLAYER_RESPAWN | level_idx | player_id, grid_x, grid_y |
| BOSS_RELEASE_TRAPPED | level_idx | base_x, base_y, wall_intact, boss_can_crush |
| BOSS_ESCAPED | level_idx | dist_from_base, pos |
| BOSS_DEFEATED | level_idx | score, monster_boss_defeated |
| BASE_DAMAGE | level_idx | attacker, hp_left, wall_damage |
| BASE_DESTROYED | level_idx | attacker |
| BRICK_DESTROY | level_idx | x,y, bullet_type, hits_needed, hits_done, is_steel |
| STEEL_DESTROY | level_idx | x,y, bullet_type, hits_needed |
| STEEL_CHIP | level_idx | x,y, bullet_type, progress |
| WEAPON_COMBINED_SHOOT | level_idx | player_id, spread:8, homing:1-3, total:9+, power |
| PWR_UPDATE | level_idx | player_id, pwr_index, damage_bonus, speed_bonus |
| POWERUP_SPAWN | level_idx | type, x,y |
| POWERUP_PICKUP | level_idx | player_id, type |
| VENOM_SPILLOVER | level_idx | source_id, target_id, radius, damage, factor |
| LIFE_SHARE | level_idx | from, to, chad_lives, lida_lives |
| PLAYER_JOIN_ATTEMPT | level_idx | player_id, state, players |
| STAGE_CLEAR | level_idx | next_level, score |
| GAME_OVER | level_idx | won, score, stage |
| COIN_INSERT | - | player_id, coins, lives |
| NETWORK_LIDA_CONNECTED | - | ip, via_broadcast_fallback |
| NETWORK_LIDA_DISCONNECT | - | reason |
| BROADCAST_FALLBACK_ACTIVE | - | ip, reason No route |
| EDGE_BLOCK | level_idx | player_id, pos, attempted_dir |
| EDGE_AUTO_CLAMP | level_idx | tank_id, from, to |
| SLIDE_THROUGH_GAP | level_idx | tank_id, offset |
| MAP_GRID_NAV | - | from_idx, to_idx, from_rc, to_rc, grid_cols |
| MAP_SELECT | - | level_idx, name |
| PERF_STARTUP_INIT | - | startup_ms, mode async_menu_instant |
| PERF_NETWORK_STARTUP | - | ip, startup_ms, async |
| PERF_PROJECTOR_STARTUP | - | ip, startup_ms |

## JS Logger API (mirrors Python)

```js
// Python: debug_logger.log_event(tag, msg, level, extra, with_stack)
logger.log_event(tag, message, level="INFO", extra=null, withStack=false)
logger.log_state(oldState, newState, reason, extra=null)
logger.log_gameplay(eventType, levelIdx, playerId, data)
logger.log_crash(where, error)
logger.log_input(type, device, code, value, mappedAction)
logger.log_perf(fps, dt, enemyCount, bulletCount)

// Helpers (mirror logger_integration.py safe wrappers)
logger.log_network(type, data)
logger.log_steel(type, data)
logger.log_edge(type, data)
logger.log_weapon(type, data)
logger.log_map(type, data)
logger.log_boss(type, data)
logger.log_perf_event(type, data)

// Query (mirrors debug_query.py)
logger.query({tag:"STATE"})  // filter
logger.query({eventType:"BOSS_ESCAPED"})
logger.tail(50)
logger.stats()
logger.report()  // auto-diagnosis like debug_report.py
logger.export()  // downloads JSON
logger.clear()
```

## Query Examples Cross-Platform

Python:
```bash
python debug_query.py --last --bounce
python debug_query.py --last --state
python debug_query.py --last --errors
python -m game.debug_logger stats
python debug_report.py
```

JS (browser console):
```js
logger.query({tag:"STATE"})
logger.query({tag:"BOSS"})
logger.query({eventType:"BOSS_ESCAPED"})
logger.tail(100)
logger.stats()
logger.report()   // shows auto-diagnosis like Python debug_report.py
logger.export()   // downloads tank93-debug-2024-...json
```

## Auto-Diagnosis (both)

Both `debug_report.py` and `logger.report()` in JS should detect:
- playing->menu bounce with breadcrumbs last 50 events before bounce
- Exception present with file:line
- Inputs near bounce (ghost ESC, joystick Plus)
- Stuck events: EDGE_BLOCK, SLIDE_THROUGH_GAP count
- Steel: destroyed/chipped count
- Network: broadcast fallback active, No route, old client only discovery
- Weapons: synergy count
- Perf: startup time
- Boss: release trapped, escaped, defeated, crush count
- Map: grid nav broken

## Persistence

- Python: debug.db WAL (gitignored), bug_trace.log text mirror
- Web JS: 
  - In-memory ring buffers (1000 events, 500 gameplay, 200 state_changes, 200 inputs, 100 exceptions)
  - localStorage.debugLogs JSON (max 50KB circular) for next load triage
  - IndexedDB optional for larger logs
  - ?debug=1 URL param enables visible overlay
  - Export via button or console `logger.export()`

## Versioning

Schema version: 1.0.0
- Add new tags/eventTypes without breaking existing queries (append only)
- If breaking, bump major and update both implementations same PR

## Related Files

- Python: game/debug_logger.py (863 LOC), game/logger_integration.py, debug_query.py, debug_report.py
- JS: web-pure/src/logger.js (to be created, mirror)
- Docs: docs/DEBUG_LOGGING.md (Python detailed), docs/DEBUG_PROTOCOL.md, docs/WEB_SYNC_CONTRACT.md

## Do NOT

- Do NOT log PII / real IP beyond LAN? LAN IP ok for debug, but don't upload.
- Do NOT log every frame (perf) - sample every 30 frames
- Do NOT let logger crash game - wrap all in try/catch with silent fail (seen in logger_integration.py safe wrappers)
- Do NOT block game loop (async in Python, sync ring buffer in JS is <0.1ms)
```
