# Tank93 Debug Logging System - Comprehensive Guide (Updated for Recent Changes)

## Overview

Tank93 now has a **production-grade debug logging system** with:

- **SQLite DB** (`debug.db`) in WAL mode for 0-latency concurrent read/write queries
- **Async writer thread** with queue to avoid game loop stalls
- **Text mirror** (`bug_trace.log`) for quick tail
- **Structured events**: sessions, state_changes, gameplay, perf, inputs, exceptions, network, edge, steel, weapons, maps, HUD, perf
- **Detailed breadcrumbs** for instant root cause analysis
- **Enhanced observability** for all recent features (network, steel, edge, startup perf, weapon stacking, map select, HUD)

## Architecture

```
Game Loop -> debug_logger.log_event/state/gameplay/input -> Queue (size 10000) -> Writer Thread -> SQLite WAL + text log
```

- **0 latency for queries**: SQLite WAL mode allows concurrent reads while writer appends
- **No frame drop**: Queue decouples game loop from disk I/O
- **Auto-pruning**: Keep last N sessions (default 20)

## Database Tables (same as before)

| Table | Purpose |
|-------|---------|
| `sessions` | Each run: git commit, platform, screen size, joystick info, start/end time |
| `events` | Generic structured logs: tag, level, message, extra JSON, stack trace (now includes NETWORK, MAP, PERF, HUD) |
| `state_changes` | Every `old_state -> new_state` with reason and stack |
| `gameplay` | Game-specific: now includes NETWORK_*, EDGE_*, STEEL_*, WEAPON_*, MAP_*, PERF_*, HUD_*, PWR_* etc |
| `perf_samples` | Every 30 frames: fps, dt, enemies/bullets count |
| `inputs` | Every KEYDOWN, JOYBUTTONDOWN, JOYHATMOTION |
| `exceptions_log` | Every caught exception |

## Logs Captured - Enhanced for Recent Changes

### 1. Network (Lida remote join - critical)
- **Before fix**: Discovery flood `192.168.0.131:58678` only, no `Lida CONNECTED`, No route 65
- **Now logs**:
  - `NETWORK_LIDA_CONNECTED` / `LIDA_CONNECTED_BROADCAST_FALLBACK` (AP isolation workaround)
  - `NETWORK_LIDA_DISCONNECT`, `LIDA_KICK`
  - `BROADCAST_FALLBACK_ACTIVE`: when unicast `No route` fails, input sent via `255.255.255.255:9999` broadcast
  - `Packet from Lida` preview to distinguish discovery vs `dir=UP` input
  - Old client detection: `⚠ Lida sending ONLY discovery for 10+ sec, no dir input`

Query:
```bash
python -m game.debug_logger query --last --network
python debug_report.py  # shows network section
```

### 2. Edge / Stuck / Outside Map (new fixes)
- `EDGE_BLOCK`, `EDGE_AUTO_CLAMP`, `PLAYER_STUCK`, `PLAYER_AUTO_UNSTUCK`
- `SLIDE_THROUGH_GAP`: tank nudged ±4/8/12px to pass 1-tile destroyed brick channel (new 20px collision)
- `CLAMP_OUTSIDE`, `SPAWN_CLAMP`: enemy outside map bug fixed, clamp to fully inside
- `EDGE_STUCK_SUMMARY` (via query)

Query:
```bash
python -m game.debug_logger query --last --stuck
```

### 3. Steel / Concrete Destructible (new: harder than brick)
- **Before**: steel required power>=2 instant, else indestructible
- **Now**: `STEEL_HITS_NEEDED` normal 5, power 3→2 after reduction, rapid 8, homing 6, etc
- Logs: `STEEL_DESTROY`, `STEEL_CHIP`, `BRICK_DESTROY` (now includes is_steel flag)

Query:
```bash
python -m game.debug_logger query --last --steel
```

### 4. Weapon Stacking (spread+homing both)
- **Before**: spread+homing = 8 homing (replacing)
- **Now**: spread+homing = 8 spread + 1-3 homing = 9+ bullets, both fire
- Logs: `WEAPON_COMBINED_SHOOT` with count, `SYNERGY_POWER_HOMING`, `PWR_UPDATE`

Query:
```bash
python -m game.debug_logger query --last --weapons
```

### 5. Performance / Startup (was 5s blocking)
- **Before**: `get_all_local_ips()` looped 6x ifconfig = 5.034s blocking Game.__init__
- **Now**: cached fast path 0.000s, async startup, menu instant 0.106s
- Logs: `PERF_STARTUP_INIT`, `PERF_NETWORK_STARTUP`, `PERF_PROJECTOR_STARTUP`, `PERF_STARTUP_SOLO`

Query:
```bash
python -m game.debug_logger query --last --perf
```

### 6. Map Select (redesign)
- **Before**: 104x38 cells overlapping preview at x=800, enemy text spam `18*basic 2*fast` cut off, LEFT/RIGHT +-5 broken for 7 cols, header "SELECT STAGE"
- **Now**: 84x52 cells, 7x5 grid width 608 centered, preview 160px at right with margin no overlap, short names (Outpost, Bunkers, Jungle...), grid-aware nav UP/DOWN=±7 cols, LEFT/RIGHT=±1 within row, BACK handling
- Logs: `MAP_GRID_NAV` with from/to rc, `MAP_SELECT`

Query:
```bash
python -m game.debug_logger query --last --maps
```

### 7. HUD (redesign + explicit P/C buttons + HP rename)
- **Before**: Joy count, LAN Host long URL cut off, Cal, TOTAL (BASE...), SPAWN..., 20 icons overflow, no explicit Pause/Coin
- **Now**: concise: ENEMY LEFT, LIFE x3, Score, HP (renamed from ARMOR), PWR index (weapon damage), ITEMS ON MAP with descriptions, COINS, minimal LAN, explicit clickable buttons `P = PAUSE` blue and `C = COIN` yellow
- Logs: `HUD_PAUSE_BUTTON_CLICK`, `HUD_COIN_BUTTON_CLICK`, `HUD_PWR_UPDATE`

### 8. State Transitions, Gameplay, Input, Perf, Exceptions (existing)
- Same as before, plus new tags MAP, PERF, HUD, NETWORK, etc.

## Query CLI - Enhanced

```bash
# Existing
python -m game.debug_logger stats
python debug_query.py --last --state
python debug_query.py --last --errors
python debug_query.py --last --bounce
python debug_query.py --last --gameplay ENEMY_SPAWN

# New observability queries
python -m game.debug_logger query --last --network   # broadcast fallback, No route, old client
python -m game.debug_logger query --last --stuck     # edge stuck, outside map, slide, clamp
python -m game.debug_logger query --last --steel     # steel destructible harder than brick
python -m game.debug_logger query --last --weapons   # spread+homing both, PWR index
python -m game.debug_logger query --last --perf      # startup 5s -> 0.1s async
python -m game.debug_logger query --last --maps      # grid nav, short names

# Auto-diagnosis now includes all new sections
python debug_report.py
# Shows:
# - Network Issues (broadcast fallback, No route, old client)
# - Stuck / Edge / Outside Map
# - Steel / Concrete Destruction
# - Weapon Stacking (spread+homing both)
# - Performance (startup)
# - Map Select (grid nav)
# - Auto-diagnosis summary for recent changes (stuck count, outside clamps, broadcast fallback usage, steel destroyed, weapon synergy)

python debug_report.py --last-bounce  # only bounce
python -m game.debug_logger tail --lines 100
```

## Example: Finding Recent Bugs

### Lida No route + discovery flood
```bash
python debug_report.py
# Shows:
# --- Network Issues ---
# F123 [NETWORK] Packet from Lida len=69 preview={"type":"discovery"...}
# F124 NETWORK_LIDA_CONNECTED_BROADCAST_FALLBACK
# --- Auto-diagnosis ---
# Broadcast fallback active (Lida AP isolation) - 3 times
```

### Edge stuck
```bash
python -m game.debug_logger query --last --stuck
# Should show SLIDE_THROUGH_GAP, AUTO_UNSTUCK, CLAMP_OUTSIDE if bug recurs
```

### Steel destructible
```bash
python -m game.debug_logger query --last --steel
# STEEL_DESTROY after 5 normal hits, 2 power hits
```

### Weapon stacking both
```bash
python -m game.debug_logger query --last --weapons
# WEAPON_COMBINED_SHOOT {spread:8, homing:1, total:9, power:True}
```

## Integration Points - Updated

- `game/game.py`: async network/projector startup with PERF logs, MAP_GRID_NAV, HUD button clicks
- `game/entities/tank.py`: EDGE auto-clamp, SLIDE_THROUGH_GAP, CLAMP_OUTSIDE, SPAWN_CLAMP
- `game/entities/bullet.py`: STEEL handling via destroy_tile
- `game/tilemap.py`: STEEL_DESTROY/CHIP logs, BRICK_DESTROY with is_steel
- `game/entities/player.py`: WEAPON_COMBINED_SHOOT, PWR_UPDATE, spread+homing both
- `game/network.py`: BROADCAST_FALLBACK_ACTIVE, LIDA_CONNECTED_BROADCAST_FALLBACK, packet preview, old client detection
- `game/ui/hud.py`: HP renamed from ARMOR, PWR index, explicit P/C buttons with HUD logs
- `game/projector.py`: cached IP, non-blocking start with PERF log
- `game/logger_integration.py`: new helpers safe_log_network, safe_log_steel, safe_log_edge, safe_log_weapon, safe_log_map, safe_log_perf, safe_log_hud

## Performance Impact - Still <0.1ms

- Cache for get_all_local_ips 30s TTL: first call 0.000s (was 5s)
- Async network/projector: Game() init 0.106s (was 5s+)
- Queue size 10000, WAL 64MB cache, async thread unchanged
- New logs are throttled (e.g., PWR_UPDATE every 5 sec, STUCK every 60 frames)

## Maintenance

```bash
python -m game.debug_logger stats
python -m game.debug_logger prune --keep 20
python debug_report.py  # now includes observability for all recent changes
```

## Files Updated for Observability

- `game/debug_logger.py`: +6 query helpers, +6 CLI flags (--network, --stuck, --steel, --weapons, --perf, --maps)
- `game/logger_integration.py`: +7 safe wrappers + docs
- `game/game.py`: + PERF logs for startup, MAP_GRID_NAV, HUD button logs
- `game/entities/player.py`: + WEAPON_COMBINED_SHOOT, PWR_UPDATE
- `game/entities/tank.py`: + EDGE/ CLAMP logs (already existed, kept)
- `game/tilemap.py`: + STEEL logs (already)
- `game/network.py`: + BROADCAST_FALLBACK_ACTIVE, CONNECTED_BROADCAST_FALLBACK, packet preview
- `game/ui/hud.py`: + HP rename, PWR index, explicit buttons
- `debug_report.py`: +5 new sections + auto-diagnosis for recent changes
- `docs/DEBUG_LOGGING.md`: this file
- `docs/DEBUG_PROTOCOL.md` (if exists) should also be updated
