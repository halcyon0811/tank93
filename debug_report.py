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

    # --- New observability sections for recent changes ---
    print(f"\n--- Network Issues (broadcast fallback, No route, old client) ---")
    try:
        net_events, net_gameplay = logger.query_network_issues(session_id=session_id, limit=20)
        if net_events or net_gameplay:
            for ev in net_events[:10]:
                print(f"  F{ev['frame']} [{ev['tag']}] {ev['message']}")
            for gp in net_gameplay[:10]:
                print(f"  F{gp['frame']} {gp['event_type']} {gp['data_json']}")
        else:
            print("  No network issues logged")
    except Exception as e:
        print(f"  Error querying network: {e}")

    print(f"\n--- Stuck / Edge / Outside Map (new fixes) ---")
    try:
        stuck = logger.query_stuck_events(session_id=session_id, limit=20)
        if stuck:
            for s in stuck[:10]:
                print(f"  F{s['frame']} {s['event_type']} {s['data_json']}")
        else:
            print("  No stuck/edge events - good, no tank stuck at edge or outside")
    except Exception as e:
        print(f"  Error querying stuck: {e}")

    print(f"\n--- Steel / Concrete Destruction (now destructible, harder than brick) ---")
    try:
        steel = logger.query_steel_events(session_id=session_id, limit=20)
        if steel:
            for s in steel[:10]:
                print(f"  F{s['frame']} {s['event_type']} {s['data_json']}")
        else:
            print("  No steel destruction yet")
    except Exception as e:
        print(f"  Error querying steel: {e}")

    print(f"\n--- Weapon Stacking (spread+homing both, PWR index) ---")
    try:
        weapons = logger.query_weapon_stacking(session_id=session_id, limit=20)
        if weapons:
            for w in weapons[:10]:
                print(f"  F{w['frame']} {w['event_type']} p={w['player_id']} {w['data_json']}")
        else:
            print("  No weapon stacking yet")
    except Exception as e:
        print(f"  Error querying weapons: {e}")

    print(f"\n--- Performance (startup was 5s blocking, now 0.1s async) ---")
    try:
        perf = logger.query_performance(session_id=session_id, limit=20)
        if perf:
            for p in perf[:10]:
                print(f"  F{p['frame']} {p['event_type']} {p['data_json']}")
        else:
            print("  No perf metrics logged")
    except Exception as e:
        print(f"  Error querying perf: {e}")

    print(f"\n--- Map Select (grid navigation, short names, no overlap) ---")
    try:
        map_gp, map_ev = logger.query_map_select(session_id=session_id, limit=20)
        if map_gp or map_ev:
            for m in map_gp[:10]:
                print(f"  F{m['frame']} {m['event_type']} {m['data_json']}")
            for m in map_ev[:10]:
                print(f"  F{m['frame']} [{m['tag']}] {m['message']}")
        else:
            print("  No map select events")
    except Exception as e:
        print(f"  Error querying map: {e}")

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

    # Additional auto-diagnosis for new features
    print(f"\n--- Auto-diagnosis for recent changes ---")
    try:
        # Check for stuck events - distinguish PLAYER_STUCK (real bug) vs ENEMY_STUCK_PUSH (normal avoidance)
        all_stuck = logger.query_stuck_events(session_id=session_id, limit=200)
        player_stuck = [s for s in all_stuck if 'PLAYER_STUCK' in s['event_type'] or 'PLAYER_AUTO_UNSTUCK' in s['event_type']]
        enemy_push = [s for s in all_stuck if 'ENEMY_STUCK_PUSH' in s['event_type']]
        if len(player_stuck) > 3:
            print(f"  ⚠ {len(player_stuck)} PLAYER stuck at edge - may still get stuck (threshold 3)")
            for ps in player_stuck[:3]:
                print(f"    F{ps['frame']} {ps['event_type']} {ps['data_json']}")
            print(f"    Run: python -m game.debug_logger query --last --stuck")
        else:
            print(f"  ✓ No player stuck at edge ({len(player_stuck)} player events, {len(enemy_push)} enemy pushes which is normal)")

        # Check for outside map - CLAMP_OUTSIDE is now expected to be fixed, should be 0
        outside = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? AND (event_type LIKE '%CLAMP_OUTSIDE%' OR data_json LIKE '%outside map%') ORDER BY id DESC LIMIT 10", (session_id,))
        if outside:
            print(f"  ⚠ {len(outside)} outside map clamps - enemy/player went outside playfield (should be 0 after fix)")
            for o in outside[:3]:
                print(f"    F{o['frame']} {o['event_type']} {o['data_json']}")
        else:
            print(f"  ✓ No outside map clamps (enemy outside bug fixed)")

        # Check for spawn clamp (enemy outside bug)
        spawn_clamp = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? AND event_type LIKE '%SPAWN_CLAMP%' OR event_type LIKE '%EDGE_AUTO_CLAMP%' ORDER BY id DESC LIMIT 10", (session_id,))
        if spawn_clamp:
            print(f"  ℹ {len(spawn_clamp)} spawn/edge auto-clamps (fix for outside)")

        # Check for broadcast fallback usage (Lida case)
        broadcast = logger.query_sql("SELECT * FROM events WHERE session_id=? AND message LIKE '%BROADCAST FALLBACK%' ORDER BY id DESC LIMIT 5", (session_id,))
        broadcast_gp = logger.query_sql("SELECT * FROM gameplay WHERE session_id=? AND event_type LIKE '%BROADCAST%' ORDER BY id DESC LIMIT 5", (session_id,))
        if broadcast or broadcast_gp:
            print(f"  ℹ Broadcast fallback active (Lida AP isolation workaround) - events:{len(broadcast)} gameplay:{len(broadcast_gp)}")
        # Check network
        net_events, net_gp = logger.query_network_issues(session_id=session_id, limit=20)
        if len(net_events) > 5 or len(net_gp) > 5:
            print(f"  ℹ {len(net_events)} network event logs, {len(net_gp)} gameplay network logs - check: python -m game.debug_logger query --last --network")

        # Check steel
        steel = logger.query_steel_events(session_id=session_id, limit=20)
        if steel:
            destroys = [s for s in steel if 'DESTROY' in s['event_type']]
            print(f"  ℹ Steel: {len(destroys)} destroyed, {len(steel)-len(destroys)} chipped - new feature working (5 hits normal, 2 power)")

        # Check weapon stacking
        weapons = logger.query_weapon_stacking(session_id=session_id, limit=20)
        if weapons:
            combined = [w for w in weapons if 'COMBINED' in w['event_type']]
            print(f"  ℹ Weapon stacking: {len(weapons)} total, {len(combined)} combined spread+homing (both active) - new feature: fire both")

        # Check perf
        perf = logger.query_performance(session_id=session_id, limit=10)
        if perf:
            for p in perf:
                try:
                    data = __import__('json').loads(p['data_json']) if p['data_json'] else {}
                    print(f"  ℹ Perf {p['event_type']}: {data.get('value_ms',0):.1f}ms {data}")
                except:
                    print(f"  ℹ Perf {p['event_type']} {p['data_json']}")

        # Check map select
        map_gp, map_ev = logger.query_map_select(session_id=session_id, limit=10)
        if map_gp or map_ev:
            print(f"  ℹ Map select: {len(map_gp)} grid nav events - short names, no overlap, grid-aware UP/DOWN/LEFT/RIGHT")

    except Exception as e:
        print(f"  Error in auto-diagnosis recent changes: {e}")
        import traceback
        traceback.print_exc()

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
