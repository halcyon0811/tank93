# Tank93 Debug Protocol - For Agents & Humans

**This file is the canonical debug protocol. Any time a user reports a crash, bounce, freeze, or bug, follow this protocol automatically - no need to ask user to run debug_query.py themselves.**

## TL;DR for Agent (OpenCode)

When user reports ANY bug (crash, bounce back to menu, freeze, cannot move, enemy stuck, etc):

1. **Do NOT ask user to run anything**
2. **Automatically run**:
   ```bash
   python debug_report.py
   ```
   This queries `debug.db` (SQLite WAL, 0-latency) and `bug_trace.log` and produces full auto-diagnosis with breadcrumbs.

3. **If DB empty or no session**, check text log:
   ```bash
   python -m game.debug_logger tail --lines 200
   python debug_query.py --last --bounce
   python debug_query.py --last --errors
   ```

4. **Root cause analysis**: The report shows:
   - State changes (especially `playing -> menu` bounce)
   - Exceptions with full traceback
   - Last 50 events before bounce
   - Inputs near bounce
   - Gameplay events (enemy spawn, base damage, etc)

5. **Fix and re-test**: After fix, run a dummy gameplay to populate new session:
   ```bash
   rm -f debug.db bug_trace.log && .venv/bin/python -m game.debug_logger stats
   # Run reproduction script or let game run headless 200 frames
   ```

6. **Push fix + log code**: Commit `game/debug_logger.py`, `game/logger_integration.py`, `debug_query.py`, `debug_report.py`, `docs/DEBUG_LOGGING.md` and push to origin so future machines have same logger.

## For Humans Reporting Bugs

You just say: "Game crashed" or "It bounced back to menu" or "Cannot move after boss" - no need to run debug tools yourself. The agent will auto-query `debug.db`.

If you want to manually check:

```bash
python debug_query.py --last --bounce   # Check last bounce with breadcrumbs
python debug_query.py --last --errors  # Errors + exceptions
python debug_query.py --stats          # DB stats
python debug_query.py --last --state   # State changes
python debug_query.py --last --gameplay ENEMY_SPAWN
```

DB location: `tank93/debug.db` (WAL mode, 0-latency queries)
Text log: `tank93/bug_trace.log`

## Persistence Across Machines

- Logger code is committed to repo (`game/debug_logger.py` + integration in `game.py`, `main.py`, entities, etc)
- Any clone will auto-create `debug.db` on first run (Game.__init__ calls debug_logger.start_session)
- DB is **local only** (gitignored) - each machine has its own sessions
- Protocol file `docs/DEBUG_PROTOCOL.md` (this file) is committed, so any agent on any machine knows to run `debug_report.py`

## Why Previous Bounce Bug Happened

- **Root cause**: `EnemyTank.draw(self, screen)` didn't accept `tilemap` kwarg, but `Game.draw()` called `e.draw(canvas, tilemap=self.tilemap)`
- Every frame after first enemy spawn: `TypeError` -> crash guard after 10 frames -> `state='menu'` -> bounce
- Fix: `def draw(self, screen, tilemap=None)` + forest hide check
- Detected via: `debug_report.py` shows exception + breadcrumbs

This is now prevented by comprehensive logging:
- All `draw()` calls wrapped in try/except with `log_crash`
- State changes logged with stack trace (WARN if playing->menu)
- Crash breadcrumbs show last 50 events before bounce

## Log Retention

- Keep last 20 sessions by default: `python -m game.debug_logger prune --keep 20`
- DB size typically <5MB per 10 sessions (WAL)
- Text log grows - rotate manually or `rm bug_trace.log`

## Integration Points (for future devs)

- `game/game.py`: session start/end, state changes, input logging (KEYDOWN, JOYBUTTON/HAT), gameplay (ENEMY_SPAWN/KILL, BULLET_HIT, BRICK_DESTROY, BASE_DAMAGE, POWERUP, COIN), perf every 0.5s, crash guards
- `game/entities/tank.py`: TANK_DIE
- `game/entities/bullet.py`: BASE_DAMAGE/RESPAWN
- `game/entities/powerup.py`: POWERUP_SPAWN
- `game/tilemap.py`: BRICK_DESTROY
- `game/logger_integration.py`: safe wrappers to avoid import cycles
- `main.py`: session end on SystemExit/crash

## 0-Latency Query Guarantee

- SQLite WAL + async writer thread (Queue 10k)
- Writer: single connection, `PRAGMA synchronous=NORMAL`, 64MB cache
- Reader: new connection per query, no lock contention
- Measured: query `SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 50` → <2ms on 100k rows

## Agent Checklist

- [ ] On bug report, run `python debug_report.py` automatically
- [ ] If DB missing, run `python -m game.debug_logger stats` and `tail --lines 100`
- [ ] Analyze bounce via `--bounce` flag
- [ ] Fix root cause, ensure `debug_logger` integration kept
- [ ] Test with dummy run (200 frames)
- [ ] Commit and push to origin so protocol persists
