#!/usr/bin/env python3
"""
Auto-debug report for OpenCode agent - 0 latency query
Run this when user reports a crash/bug. Outputs full diagnosis.

Usage:
  python debug_report.py
  python debug_report.py --session <id>
  python debug_report.py --last-bounce
  python debug_report.py --full

This is the tool the agent uses when user says "it crashed" or "it bounced back" etc.
No need for user to run debug_query.py themselves.
"""
import sys
import pathlib
import sqlite3
import json
from datetime import datetime

ROOT = pathlib.Path(__file__).parent
DB_PATH = ROOT / "debug.db"
TXT_PATH = ROOT / "bug_trace.log"

sys.path.insert(0, str(ROOT))
try:
    from game.debug_logger import DebugLogger
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False

def get_last_session_id():
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def format_row(r):
    return dict(r) if isinstance(r, sqlite3.Row) else r

def auto_diagnose(session_id=None):
    if not DB_PATH.exists():
        print(f"[Auto-Diag] No debug DB found at {DB_PATH} - no session logged yet")
        print(f"[Auto-Diag] Text log exists? {TXT_PATH.exists()} size={TXT_PATH.stat().st_size if TXT_PATH.exists() else 0}")
        if TXT_PATH.exists():
            print("\n--- Last 100 lines of bug_trace.log ---")
            with open(TXT_PATH, 'r') as f:
                lines = f.readlines()
                for l in lines[-100:]:
                    print(l.rstrip())
        return

    logger = DebugLogger()
    
    if session_id is None:
        rows = logger.query_sql("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        if not rows:
            print("[Auto-Diag] No sessions in DB")
            return
        session_id = rows[0]["id"]
    
    print(f"\n{'='*100}")
    print(f"AUTO DIAGNOSIS REPORT - Session {session_id}")
    print(f"Generated at {datetime.now().isoformat()}")
    print(f"{'='*100}\n")

    # Session info
    sessions = logger.query_sql("SELECT * FROM sessions WHERE id=?", (session_id,))
    if sessions:
        s = sessions[0]
        print(f"Session: ID={s['id']} started={s['started_at']} ended={s['ended_at']}")
        print(f"  Commit: {s['git_commit']} Platform: {s['platform']}")
        print(f"  Screen: {s['screen_w']}x{s['screen_h']} FS={s['is_fullscreen']} Mega={s['is_mega']}")
        print(f"  Joysticks: {s['joystick_count']} info={s['joystick_info']}")
        print(f"  Level: {s['initial_level']} Players: {s['num_players']}")
        print()

    # Stats
    stats = logger.stats()
    print(f"DB Stats: sessions={stats['sessions']} events={stats['events']} state_changes={stats['state_changes']} gameplay={stats['gameplay']} exceptions={stats['exceptions']} size={stats['db_size_bytes']} bytes")

    # State changes - critical for bounce detection
    state_changes = logger.query_sql("SELECT * FROM state_changes WHERE session_id=? ORDER BY frame ASC, id ASC", (session_id,))
    print(f"\n--- State Changes (total {len(state_changes)}) ---")
    for sc in state_changes:
        flag = " *** BOUNCE! ***" if sc['old_state']=='playing' and sc['new_state']=='menu' else ""
        print(f"  F{sc['frame']} +{sc['elapsed_ms']}ms: {sc['old_state']} -> {sc['new_state']} | {sc['reason']}{flag}")
    
    bounces = [sc for sc in state_changes if sc['old_state']=='playing' and sc['new_state']=='menu']
    if bounces:
        print(f"\n!!! DETECTED {len(bounces)} BOUNCE(S) playing->menu !!!")
        for b in bounces:
            print(f"  Frame {b['frame']} elapsed {b['elapsed_ms']}ms reason={b['reason']}")
            print(f"  Stack: {b['stack_trace'][:2000] if b['stack_trace'] else 'no stack'}")
    else:
        print("\nNo playing->menu bounce detected - not bounce bug")

    # Exceptions - root cause
    exceptions = logger.query_sql("SELECT * FROM exceptions_log WHERE session_id=? ORDER BY frame ASC", (session_id,))
    print(f"\n--- Exceptions (total {len(exceptions)}) ---")
    if not exceptions:
        print("  No exceptions logged - clean run")
    else:
        for ex in exceptions:
            print(f"\n  F{ex['frame']} WHERE={ex['where_loc']} {ex['exc_type']}: {ex['message']}")
            print(f"    traceback:\n{ex['traceback'][:1500]}")

    # Error events
    errors = logger.query_sql("SELECT * FROM events WHERE session_id=? AND level IN ('ERROR','FATAL') ORDER BY frame DESC LIMIT 20", (session_id,))
    print(f"\n--- Last 20 ERROR/FATAL Events ---")
    if not errors:
        print("  No error events")
    else:
        for ev in errors:
            print(f"  F{ev['frame']} [{ev['tag']}] {ev['message']}")
            if ev['extra_json']:
                print(f"    extra: {ev['extra_json'][:500]}")

    # Breadcrumbs for each bounce
    if bounces:
        for bounce in bounces:
            frame = bounce['frame']
            print(f"\n--- Breadcrumbs: 50 events before bounce at F{frame} ---")
            evs = logger.query_sql("SELECT * FROM events WHERE session_id=? AND frame <= ? ORDER BY frame DESC, id DESC LIMIT 50", (session_id, frame))
            for ev in reversed(evs):
                print(f"  F{ev['frame']} [{ev['level']} {ev['tag']}] {ev['message']}")

            print(f"\n--- Inputs 30 frames before bounce ---")
            inputs = logger.query_sql("SELECT * FROM inputs WHERE session_id=? AND frame BETWEEN ? AND ? ORDER BY frame ASC", (session_id, max(0, frame-30), frame))
            for inp in inputs:
                print(f"  F{inp['frame']} {inp['input_type']} {inp['device']} {inp['code']}={inp['value']} -> {inp['mapped_action']}")

            print(f"\n--- Gameplay 30 frames before bounce ---")
            gp = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? AND frame BETWEEN ? AND ? ORDER BY frame ASC", (session_id, max(0, frame-30), frame))
            for g in gp:
                print(f"  F{g['frame']} lvl={g['level_idx']} {g['event_type']} p={g['player_id']} data={g['data_json']}")

    # Last gameplay events
    print(f"\n--- Last 30 Gameplay Events ---")
    gps = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? ORDER BY id DESC LIMIT 30", (session_id,))
    for g in reversed(gps):
        print(f"  F{g['frame']} lvl={g['level_idx']} {g['event_type']} p={g['player_id']} data={g['data_json']}")

    # Perf samples
    perfs = logger.query_sql("SELECT * FROM perf_samples WHERE session_id=? ORDER BY frame DESC LIMIT 10", (session_id,))
    if perfs:
        print(f"\n--- Perf (last 10) ---")
        for p in perfs:
            print(f"  F{p['frame']} fps={p['fps']:.1f} dt={p['dt_ms']:.1f}ms upd={p['update_ms']:.1f} draw={p['draw_ms']:.1f} enemies={p['enemies_count']} bullets={p['bullets_count']} players_alive={p['players_alive']}")

    # Last events
    print(f"\n--- Last 40 Events (any level) ---")
    last_events = logger.query_sql("SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 40", (session_id,))
    for ev in reversed(last_events):
        print(f"  F{ev['frame']} [{ev['level']} {ev['tag']}] {ev['message']}")

    # Diagnosis summary
    print(f"\n{'='*100}")
    print("DIAGNOSIS SUMMARY")
    print(f"{'='*100}")
    if bounces and exceptions:
        print("Likely root cause: Exception causing crash guard to force menu")
        print(f"  Exceptions: {[e['exc_type'] for e in exceptions]}")
        print(f"  Check traceback above for exact file:line")
    elif bounces and not exceptions:
        print("Bounce without exception - likely intentional ESC or gameover timer or input mapped to menu")
        # Check inputs near bounce
        if bounces:
            frame = bounces[0]['frame']
            inputs_near = logger.query_sql("SELECT * FROM inputs WHERE session_id=? AND frame BETWEEN ? AND ? ORDER BY id DESC LIMIT 20", (session_id, max(0, frame-10), frame))
            if inputs_near:
                print(f"  Inputs near bounce F{frame}:")
                for inp in inputs_near:
                    print(f"    {inp['input_type']} {inp['code']} -> {inp['mapped_action']}")
            else:
                print("  No inputs near bounce - might be gameover timer or programmatic state change")
                # Check if gameover timer expired?
                gameovers = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? AND event_type='GAMEOVER' ORDER BY id DESC LIMIT 5", (session_id,))
                if gameovers:
                    print(f"  Recent gameovers: {gameovers}")
    elif exceptions:
        print(f"Exceptions found ({len(exceptions)}) but no bounce - may cause other bugs")
    else:
        print("No bounces, no exceptions - clean run or bug not captured? Check gameplay events for logic bugs")

    print(f"\nFull DB: {DB_PATH}")
    print(f"Text log: {TXT_PATH} (last 20 lines below)")
    if TXT_PATH.exists():
        with open(TXT_PATH, 'r') as f:
            lines = f.readlines()
            for l in lines[-20:]:
                print(l.rstrip())
    print(f"\n{'='*100}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tank93 Auto Debug Report - for agent use when user reports bug/crash")
    parser.add_argument("--session", type=int, help="Session ID (default last)")
    parser.add_argument("--full", action="store_true", help="Full dump including all tables")
    parser.add_argument("--last-bounce", action="store_true", help="Only show last bounce breadcrumbs")
    args = parser.parse_args()

    if args.last_bounce:
        # Quick bounce check
        if not DB_PATH.exists():
            print("No DB")
            sys.exit(0)
        from game.debug_logger import DebugLogger
        dl = DebugLogger()
        rows = dl.query_sql("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        if not rows:
            print("No sessions")
            sys.exit(0)
        sid = args.session or rows[0]["id"]
        # Run bounce query
        dl = DebugLogger()
        # Use debug_query logic
        import subprocess
        result = subprocess.run([sys.executable, "debug_query.py", "--last", "--bounce"], cwd=str(ROOT), capture_output=False)
        sys.exit(0)

    auto_diagnose(session_id=args.session)

    if args.full:
        print("\n\n--- FULL DB DUMP ---")
        from game.debug_logger import DebugLogger
        dl = DebugLogger()
        for table in ["events", "state_changes", "gameplay", "exceptions_log"]:
            print(f"\n--- Table {table} ---")
            rows = dl.query_sql(f"SELECT * FROM {table} WHERE session_id=? ORDER BY id DESC LIMIT 20", (get_last_session_id(),))
            for r in rows:
                print(dict(r))
