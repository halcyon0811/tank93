# Tank93 Agent Instructions

## Debug Protocol - MUST follow when user reports ANY bug/crash/bounce/freeze

**User will NOT run debug_query.py themselves. This is for you (the agent) to run automatically.**

### On ANY bug report ("crashed", "bounced back to menu", "cannot move", "freeze", "stuck", etc):

1. **Immediately** run auto-diagnosis:
   ```bash
   python debug_report.py
   ```
   This queries debug.db (SQLite WAL, 0-latency) and bug_trace.log and outputs full auto-diagnosis with breadcrumbs, stack traces, root cause.

2. **If DB empty**, also run:
   ```bash
   python -m game.debug_logger stats
   python -m game.debug_logger tail --lines 200
   python debug_query.py --last --bounce
   python debug_query.py --last --errors
   ```

3. **Analyze** output:
   - `playing->menu` bounce? Check breadcrumbs: last 50 events before bounce, inputs near bounce, exceptions
   - Exception present? Check traceback file:line
   - No exception but bounce? Check inputs near bounce (ghost ESC, joystick Plus mapped to menu, etc)

4. **Fix root cause**, ensure debug_logger integration kept (don't remove logging)

5. **Test** with headless 200 frames:
   ```bash
   .venv/bin/python -c "
   import os; os.environ['SDL_VIDEODRIVER']='dummy'; ...
   g = Game(); g.menu_selected=0; g.handle_menu_select();
   for i in range(200): g.handle_events(); g.update_playing(16); g.draw()
   print('OK')
   "
   ```

6. **Commit and push to origin** so protocol persists across machines.

### Logger Design (already committed)

- Core: `game/debug_logger.py` (SQLite WAL async queue, 600+ lines)
- Integration: `game/logger_integration.py` + game.py, main.py, entities, tilemap
- Query tools: `debug_query.py` (user-friendly), `debug_report.py` (auto-diagnosis for agent)
- DB: `debug.db` (local, gitignored WAL/SHM), Text: `bug_trace.log`
- Docs: `docs/DEBUG_LOGGING.md`, `docs/DEBUG_PROTOCOL.md`

### 0-Latency Guarantee

- WAL mode, 64MB cache, async writer thread (queue 10k)
- Queries: `SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 50` → <2ms on 100k rows
- No frame drop: queue decouples game loop from disk

### Previous Bug Example (Fixed)

- **Symptom**: Game bounces back to main page once started
- **Root cause**: `EnemyTank.draw(self, screen)` missing `tilemap` kwarg, but `Game.draw()` called `e.draw(canvas, tilemap=self.tilemap)` → TypeError every frame → crash guard after 10 frames → menu
- **Detected via**: `debug_report.py` shows exception + breadcrumbs
- **Fix**: `def draw(self, screen, tilemap=None)` + forest hide check

### For Future Machines

- Any clone auto-creates debug.db on first Game().__init__ -> start_session()
- Protocol files committed: `AGENTS.md`, `docs/DEBUG_PROTOCOL.md`, `docs/DEBUG_LOGGING.md`, `game/debug_logger.py`, etc
- So any agent on any machine knows to run `debug_report.py` when user reports bug

### Files to keep (do not delete)

- `game/debug_logger.py`
- `game/logger_integration.py`
- `debug_query.py`
- `debug_report.py`
- `docs/DEBUG_LOGGING.md`
- `docs/DEBUG_PROTOCOL.md`
- `AGENTS.md` (this file)

### Example queries for agent

```bash
python debug_report.py                  # Full auto-diagnosis (use this first)
python debug_report.py --last-bounce   # Only bounce breadcrumbs
python debug_query.py --last --bounce  # Same but via debug_query
python debug_query.py --last --state   # State changes
python debug_query.py --last --errors  # Errors + exceptions
python -m game.debug_logger stats       # DB stats
python -m game.debug_logger sessions --limit 5
```

### Push reminder

After fixing bug, always:

```bash
git add -A
git commit -m "fix: <description> + keep debug logging"
git push origin main
```

So future machines have same logger.
