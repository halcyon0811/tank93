#!/usr/bin/env python3
"""
Quick debug query helper - 0 latency SQLite queries for Tank93

Examples:
  python debug_query.py --last --state
  python debug_query.py --last --errors
  python debug_query.py --last --bounce
  python debug_query.py --sessions
  python debug_query.py --stats
  python debug_query.py --gameplay ENEMY_SPAWN
  python debug_query.py --search "menu" --tag STATE
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent / "tank93"))
# Actually this file lives in root tank93/, so need to adjust
# If running from tank93/tank93/
if not (pathlib.Path(__file__).parent / "game" / "debug_logger.py").exists():
    # Running from outer tank93/
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
else:
    sys.path.insert(0, str(pathlib.Path(__file__).parent))

from game.debug_logger import DebugLogger
import argparse

def main():
    parser = argparse.ArgumentParser(description="Tank93 0-latency debug DB query")
    parser.add_argument("--session", type=int, help="Session ID")
    parser.add_argument("--last", action="store_true", help="Use last session")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--level", help="Filter by level")
    parser.add_argument("--search", help="Search message contains")
    parser.add_argument("--state", action="store_true", help="Show state changes")
    parser.add_argument("--errors", action="store_true", help="Show ERROR/FATAL events + exceptions")
    parser.add_argument("--bounce", action="store_true", help="Show last playing->menu bounce with breadcrumbs")
    parser.add_argument("--sessions", action="store_true", help="List sessions")
    parser.add_argument("--stats", action="store_true", help="DB stats")
    parser.add_argument("--gameplay", help="Filter gameplay by event_type (e.g., ENEMY_SPAWN, BASE_DAMAGE, POWERUP_PICK)")
    parser.add_argument("--inputs", action="store_true", help="Show inputs")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--tail", type=int, help="Tail text log bug_trace.log lines")
    args = parser.parse_args()

    logger = DebugLogger()

    # Resolve session id
    session_id = args.session
    if args.last or session_id is None:
        rows = logger.query_sql("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
        if rows:
            last_id = rows[0]["id"]
            if session_id is None:
                session_id = last_id
            if not args.sessions and not args.stats and not args.tail:
                print(f"Using session {last_id} (last)")

    if args.sessions:
        rows = logger.get_sessions(limit=args.limit)
        print(f"\n=== Last {args.limit} sessions ===")
        for r in rows:
            print(f"ID={r['id']} started={r['started_at']} ended={r['ended_at']} commit={r['git_commit']} screen={r['screen_w']}x{r['screen_h']} fs={r['is_fullscreen']} joy={r['joystick_count']} lvl={r['initial_level']} players={r['num_players']}")
        return

    if args.stats:
        s = logger.stats()
        print("\n=== Debug DB Stats (0-latency SQLite) ===")
        for k, v in s.items():
            print(f"  {k}: {v}")
        err = logger.query_sql("SELECT COUNT(*) as c FROM events WHERE level IN ('ERROR','FATAL')")[0]["c"]
        print(f"  error_events: {err}")
        exc = logger.query_sql("SELECT COUNT(*) as c FROM exceptions_log")[0]["c"]
        print(f"  exceptions: {exc}")
        print(f"\nDB: {logger.db_path}")
        print(f"TXT: {pathlib.Path(logger.db_path).parent / 'bug_trace.log'}")
        return

    if args.tail:
        from pathlib import Path
        p = Path(logger.db_path).parent / "bug_trace.log"
        if not p.exists():
            print(f"No text log at {p}")
            return
        with open(p, 'r') as f:
            lines = f.readlines()
            for l in lines[-args.tail:]:
                print(l.rstrip())
        return

    if session_id is None:
        print("No session ID, use --last or --session <id> or --sessions to list")
        return

    if args.bounce:
        print(f"\n=== Bounce analysis for session {session_id} (playing->menu) ===")
        crumbs = logger.get_crash_breadcrumbs(session_id)
        if not crumbs:
            print("No playing->menu bounces found - good!")
            # Show last state changes
            rows = logger.get_state_changes(session_id=session_id, limit=20)
            print("\nLast state changes:")
            for r in rows:
                print(f"  F{r['frame']} {r['old_state']} -> {r['new_state']} | {r['reason']} | {r['ts']}")
        else:
            for crash, events in crumbs:
                print(f"\n--- BOUNCE at frame {crash['frame']} elapsed {crash['elapsed_ms']}ms ---")
                print(f"  {crash['old_state']} -> {crash['new_state']} reason={crash['reason']}")
                print(f"  ts={crash['ts']} extra={crash['extra_json']}")
                print(f"  stack:\n{crash['stack_trace'][:1000] if crash['stack_trace'] else 'no stack'}")
                print(f"\n  Last 30 events before bounce:")
                for ev in reversed(events[-30:]):
                    print(f"    F{ev['frame']} [{ev['level']} {ev['tag']}] {ev['message']}")
                # Also show exceptions near that frame
                excs = logger.query_sql("SELECT * FROM exceptions_log WHERE session_id=? AND frame BETWEEN ? AND ? ORDER BY frame DESC", (session_id, max(0, crash['frame']-50), crash['frame']+5))
                if excs:
                    print(f"\n  Exceptions near bounce:")
                    for ex in excs:
                        print(f"    F{ex['frame']} WHERE={ex['where_loc']} {ex['exc_type']}: {ex['message']}")
                        if ex['traceback']:
                            print(f"    {ex['traceback'][:500]}")
        return

    if args.state:
        rows = logger.get_state_changes(session_id=session_id, limit=args.limit)
        print(f"\n=== State changes for session {session_id} (last {args.limit}) ===")
        for r in rows:
            print(f"[F{r['frame']} +{r['elapsed_ms']}ms] {r['old_state']} -> {r['new_state']} | {r['reason']} | {r['ts']}")
            if r['extra_json']:
                print(f"  extra: {r['extra_json'][:300]}")
        return

    if args.errors:
        rows = logger.get_events(session_id=session_id, level="ERROR", limit=args.limit)
        print(f"\n=== ERROR events for session {session_id} ===")
        for r in rows:
            print(f"[F{r['frame']} {r['tag']}] {r['message']} | {r['extra_json']}")
            if r['stack_trace']:
                print(f"  stack: {r['stack_trace'][:500]}")
        rows2 = logger.get_exceptions(session_id=session_id, limit=args.limit)
        print(f"\n=== Exceptions for session {session_id} ===")
        for r in rows2:
            print(f"[F{r['frame']}] WHERE={r['where_loc']} {r['exc_type']}: {r['message']}")
            if r['traceback']:
                print(r['traceback'][:800])
        return

    if args.gameplay:
        rows = logger.get_gameplay(session_id=session_id, event_type=args.gameplay, limit=args.limit)
        print(f"\n=== Gameplay {args.gameplay} for session {session_id} ===")
        for r in rows:
            print(f"[F{r['frame']} lvl={r['level_idx']} p={r['player_id']}] {r['event_type']} data={r['data_json']}")
        return

    if args.inputs:
        rows = logger.query_sql("SELECT * FROM inputs WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, args.limit))
        print(f"\n=== Inputs for session {session_id} (last {args.limit}) ===")
        for r in rows:
            print(f"[F{r['frame']} {r['input_type']} {r['device']} {r['code']}={r['value']} -> {r['mapped_action']}] {r['extra_json']}")
        return

    # Default: events
    rows = logger.get_events(session_id=session_id, tag=args.tag, level=args.level, limit=args.limit, search=args.search)
    print(f"\n=== Events for session {session_id} tag={args.tag} level={args.level} search={args.search} ===")
    for r in rows:
        print(f"[F{r['frame']} +{r['elapsed_ms']}ms {r['level']} {r['tag']}] {r['message']} | extra={r['extra_json']}")

if __name__ == "__main__":
    main()
