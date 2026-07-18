"""
Tank93 Comprehensive Debug Logger - SQLite based for 0-latency queries

Design:
- Single SQLite DB with WAL mode for concurrent read/write, 0-lock query
- Async queue + dedicated writer thread to avoid game loop stalls
- Structured events: session, state_changes, inputs, gameplay, performance, crashes, network
- Detailed breadcrumbs: every state transition, every enemy spawn/death, bullet hit, powerup, base damage, player death/respawn
- Auto-pruning: keep last N sessions or max DB size
- Query helpers for fast root cause analysis

Usage:
    from game.debug_logger import debug_logger, log_state, log_event, log_crash

Tables:
    sessions: id, started_at, git_commit, platform, fps_target, screen_size, joystick_info
    events: id, session_id, timestamp, frame, elapsed_ms, level, tag, message, extra_json, stack_trace
    state_changes: id, session_id, timestamp, frame, old_state, new_state, reason, extra_json, stack_trace
    gameplay: id, session_id, timestamp, frame, event_type, level_idx, player_id, data_json
    perfs: id, session_id, timestamp, frame, fps, dt_ms, update_ms, draw_ms, sprites_count, particles_count, enemies_count, bullets_count
    inputs: id, session_id, timestamp, frame, input_type, device, key_code, value, mapped_action
    exceptions: id, session_id, timestamp, frame, where, exception_type, message, traceback

Logs also mirror to bug_trace.log text file for quick tail.

Query:
    python -m game.debug_logger query --last --tag BUG --level ERROR
    python -m game.debug_logger query --session <id> --state-changes
    python -m game.debug_logger query --crashes
    python -m game.debug_logger stats
"""

import sqlite3
import pathlib
import json
import threading
import queue
import time
import datetime
import traceback
import os
import platform as plat
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

ROOT = pathlib.Path(__file__).parent.parent
DB_PATH = ROOT / "debug.db"
LOG_TXT_PATH = ROOT / "bug_trace.log"

# Ensure DB dir exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# --- Schema ---
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  -- 64MB cache
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    git_commit TEXT,
    platform TEXT,
    python_version TEXT,
    pygame_version TEXT,
    screen_w INTEGER,
    screen_h INTEGER,
    is_fullscreen INTEGER,
    is_mega INTEGER,
    fps_target INTEGER,
    joystick_count INTEGER,
    joystick_info TEXT,
    initial_level INTEGER,
    num_players INTEGER
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    level TEXT,   -- DEBUG, INFO, WARN, ERROR, FATAL
    tag TEXT,     -- STATE, INPUT, GAMEPLAY, PERF, CRASH, NETWORK, etc
    message TEXT,
    extra_json TEXT,
    stack_trace TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS state_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    old_state TEXT,
    new_state TEXT,
    reason TEXT,
    extra_json TEXT,
    stack_trace TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS gameplay (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    level_idx INTEGER,
    event_type TEXT, -- SPAWN_ENEMY, KILL_ENEMY, PLAYER_DEATH, PLAYER_RESPAWN, BULLET_HIT, BRICK_DESTROY, BASE_DAMAGE, POWERUP_SPAWN, POWERUP_PICK, STAGE_CLEAR, GAMEOVER, COIN_INSERT, etc
    player_id INTEGER,
    enemy_id INTEGER,
    data_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS perf_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    fps REAL,
    dt_ms REAL,
    update_ms REAL,
    draw_ms REAL,
    enemies_count INTEGER,
    bullets_count INTEGER,
    particles_count INTEGER,
    players_alive INTEGER,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    input_type TEXT, -- KEYDOWN, KEYUP, JOYBUTTONDOWN, JOYAXISMOTION, JOYHATMOTION, MOUSE
    device TEXT,
    code TEXT,
    value REAL,
    mapped_action TEXT,
    extra_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS exceptions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    ts TEXT NOT NULL,
    elapsed_ms INTEGER,
    frame INTEGER,
    where_loc TEXT,
    exc_type TEXT,
    message TEXT,
    traceback TEXT,
    extra_json TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_tag ON events(tag);
CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_frame ON events(frame);
CREATE INDEX IF NOT EXISTS idx_state_session ON state_changes(session_id);
CREATE INDEX IF NOT EXISTS idx_state_old_new ON state_changes(old_state, new_state);
CREATE INDEX IF NOT EXISTS idx_gameplay_session ON gameplay(session_id);
CREATE INDEX IF NOT EXISTS idx_gameplay_type ON gameplay(event_type);
CREATE INDEX IF NOT EXISTS idx_gameplay_level ON gameplay(level_idx);
CREATE INDEX IF NOT EXISTS idx_inputs_session ON inputs(session_id);
CREATE INDEX IF NOT EXISTS idx_exceptions_session ON exceptions_log(session_id);
CREATE INDEX IF NOT EXISTS idx_perf_session ON perf_samples(session_id);
"""

def _get_git_commit():
    try:
        import subprocess
        res = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), stderr=subprocess.DEVNULL, text=True)
        return res.strip()
    except Exception:
        return "unknown"

class DebugLogger:
    def __init__(self, db_path: pathlib.Path = DB_PATH):
        self.db_path = db_path
        self._queue = queue.Queue(maxsize=10000)
        self._writer_thread: Optional[threading.Thread] = None
        self._running = False
        self._session_id: Optional[int] = None
        self._session_start_time = None
        self._frame_counter = 0
        self._lock = threading.Lock()
        self._conn = None
        self._init_db()
        self._start_writer()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    def _writer_loop(self):
        # Dedicated writer thread with single connection
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        while self._running:
            try:
                item = self._queue.get(timeout=0.2)
                if item is None:  # sentinel
                    break
                qtype, data = item
                try:
                    if qtype == "sql":
                        sql, params = data
                        conn.execute(sql, params)
                        conn.commit()
                    elif qtype == "many":
                        sql, many_params = data
                        conn.executemany(sql, many_params)
                        conn.commit()
                    elif qtype == "executescript":
                        conn.executescript(data)
                        conn.commit()
                except Exception as e:
                    # Fallback: try log to file
                    try:
                        with open(LOG_TXT_PATH, "a") as f:
                            f.write(f"[LOGGER_WRITER_ERROR] {e} while {qtype}\n")
                    except:
                        pass
            except queue.Empty:
                continue
            except Exception as e:
                try:
                    with open(LOG_TXT_PATH, "a") as f:
                        f.write(f"[LOGGER_WRITER_FATAL] {e}\n{traceback.format_exc()}\n")
                except:
                    pass
        conn.close()

    def _start_writer(self):
        self._running = True
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name="DebugLoggerWriter")
        self._writer_thread.start()

    def stop(self):
        self._running = False
        try:
            self._queue.put_nowait(None)
        except:
            pass
        if self._writer_thread:
            self._writer_thread.join(timeout=1.0)

    def _now_iso(self):
        return datetime.datetime.now().isoformat()

    def _elapsed_ms(self):
        if self._session_start_time is None:
            return 0
        return int((time.time() - self._session_start_time) * 1000)

    def start_session(self, screen_w=960, screen_h=720, is_fullscreen=False, is_mega=False, fps_target=60,
                      joystick_count=0, joystick_info="", initial_level=0, num_players=1):
        self._session_start_time = time.time()
        self._frame_counter = 0
        started_at = self._now_iso()
        git_commit = _get_git_commit()
        plat_info = f"{plat.system()} {plat.release()} {plat.machine()}"
        py_ver = f"{sys.version.split()[0]}"
        try:
            import pygame
            pg_ver = pygame.version.ver if hasattr(pygame.version, 'ver') else str(pygame.version.vernum)
        except:
            pg_ver = "unknown"

        # Synchronous insert for session to get id immediately
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sessions (started_at, git_commit, platform, python_version, pygame_version,
                                  screen_w, screen_h, is_fullscreen, is_mega, fps_target,
                                  joystick_count, joystick_info, initial_level, num_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (started_at, git_commit, plat_info, py_ver, pg_ver,
              screen_w, screen_h, int(is_fullscreen), int(is_mega), fps_target,
              joystick_count, joystick_info, initial_level, num_players))
        conn.commit()
        self._session_id = cur.lastrowid
        conn.close()

        # Also write header to text log
        try:
            with open(LOG_TXT_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*100}\n")
                f.write(f"NEW SESSION id={self._session_id} at {started_at} commit={git_commit} platform={plat_info}\n")
                f.write(f"screen={screen_w}x{screen_h} fs={is_fullscreen} mega={is_mega} joy={joystick_count} info={joystick_info}\n")
                f.write(f"{'='*100}\n")
        except:
            pass

        self.log_event("SESSION", f"Session {self._session_id} started git={git_commit} {screen_w}x{screen_h} fs={is_fullscreen} mega={is_mega} joys={joystick_count}", level="INFO",
                       extra={"git": git_commit, "platform": plat_info, "joysticks": joystick_info})
        return self._session_id

    def end_session(self):
        if self._session_id is None:
            return
        ended_at = self._now_iso()
        # update sessions ended_at
        self._queue.put(("sql", ("UPDATE sessions SET ended_at=? WHERE id=?", (ended_at, self._session_id))))
        self.log_event("SESSION", f"Session {self._session_id} ended at {ended_at}", level="INFO")
        self._session_id = None

    def _enqueue(self, qtype, data):
        try:
            self._queue.put_nowait((qtype, data))
        except queue.Full:
            # Drop oldest if full to avoid blocking game
            try:
                self._queue.get_nowait()
                self._queue.put_nowait((qtype, data))
            except:
                pass

    def _format_stack(self, skip=2):
        try:
            stacks = traceback.format_stack()
            # skip last `skip` frames (current logger calls)
            relevant = stacks[:-skip]
            # keep last 12 frames
            return "".join(relevant[-12:])
        except:
            return ""

    def _write_text_log(self, level, tag, message, extra=None, stack=None):
        try:
            ts = datetime.datetime.now().isoformat()
            frame = self._frame_counter
            elapsed = self._elapsed_ms()
            line = f"[{ts}] [{level}] [F{frame} +{elapsed}ms] [{tag}] {message}"
            if extra:
                try:
                    extra_str = json.dumps(extra, ensure_ascii=False)[:800]
                    line += f" | {extra_str}"
                except:
                    pass
            with open(LOG_TXT_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                if stack:
                    f.write(stack + "\n")
        except:
            pass

    def log_event(self, tag: str, message: str, level: str = "INFO", extra: Optional[Dict[str, Any]] = None, with_stack: bool = False):
        if self._session_id is None:
            # If no session, still write to text log
            self._write_text_log(level, tag, message, extra, self._format_stack() if with_stack else None)
            return
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        extra_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else None
        stack = self._format_stack() if with_stack else None

        sql = """INSERT INTO events (session_id, ts, elapsed_ms, frame, level, tag, message, extra_json, stack_trace)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, level, tag, message[:2000], extra_json, stack)
        self._enqueue("sql", (sql, params))
        self._write_text_log(level, tag, message, extra, stack)
        # Also print WARN/ERROR to console
        if level in ("WARN", "ERROR", "FATAL"):
            print(f"[{level}] [{tag}] {message}")

    def log_state_change(self, old_state: str, new_state: str, reason: str, extra: Optional[Dict[str, Any]] = None):
        if self._session_id is None:
            return
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        extra_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else None
        stack = self._format_stack()

        sql = """INSERT INTO state_changes (session_id, ts, elapsed_ms, frame, old_state, new_state, reason, extra_json, stack_trace)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, old_state, new_state, reason[:500], extra_json, stack)
        self._enqueue("sql", (sql, params))

        level = "WARN" if old_state == "playing" and new_state == "menu" else "INFO"
        self._write_text_log(level, "STATE", f"{old_state} -> {new_state} | {reason}", extra, stack)
        # Also log as event for unified search
        self.log_event("STATE", f"{old_state} -> {new_state} | reason={reason}", level=level, extra=extra, with_stack=True)

    def log_gameplay(self, event_type: str, level_idx: int = -1, player_id: Optional[int] = None, enemy_id: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        if self._session_id is None:
            return
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        data_json = json.dumps(data, ensure_ascii=False, default=str) if data else None
        sql = """INSERT INTO gameplay (session_id, ts, elapsed_ms, frame, level_idx, event_type, player_id, enemy_id, data_json)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, level_idx, event_type, player_id, enemy_id, data_json)
        self._enqueue("sql", (sql, params))
        # Also brief event
        if event_type in ("BASE_DAMAGE", "GAMEOVER", "PLAYER_DEATH", "BOSS_RELEASE", "EXCEPTION"):
            self._write_text_log("INFO", "GAMEPLAY", f"{event_type} lvl={level_idx} p={player_id} data={data}")

    def log_input(self, input_type: str, device: str = "", code: str = "", value: float = 0, mapped_action: str = "", extra: Optional[Dict] = None):
        if self._session_id is None:
            return
        # Throttle high freq inputs? We log all but could sample
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        extra_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else None
        sql = """INSERT INTO inputs (session_id, ts, elapsed_ms, frame, input_type, device, code, value, mapped_action, extra_json)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, input_type, device, code, value, mapped_action, extra_json)
        self._enqueue("sql", (sql, params))

    def log_exception(self, where: str, exc: Exception, extra: Optional[Dict] = None):
        if self._session_id is None:
            return
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        exc_type = type(exc).__name__
        msg = str(exc)[:2000]
        tb_str = traceback.format_exc()
        extra_json = json.dumps(extra, ensure_ascii=False, default=str) if extra else None

        sql = """INSERT INTO exceptions_log (session_id, ts, elapsed_ms, frame, where_loc, exc_type, message, traceback, extra_json)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, where, exc_type, msg, tb_str, extra_json)
        self._enqueue("sql", (sql, params))
        self._write_text_log("ERROR", "EXCEPTION", f"{where} {exc_type}: {msg}", extra, tb_str)
        print(f"[EXCEPTION] {where} {exc_type}: {msg}")

    def log_perf(self, fps: float, dt_ms: float, update_ms: float = 0, draw_ms: float = 0,
                 enemies_count=0, bullets_count=0, particles_count=0, players_alive=0):
        if self._session_id is None:
            return
        # Sample every 30 frames to reduce DB spam
        if self._frame_counter % 30 != 0:
            return
        ts = self._now_iso()
        elapsed = self._elapsed_ms()
        frame = self._frame_counter
        sql = """INSERT INTO perf_samples (session_id, ts, elapsed_ms, frame, fps, dt_ms, update_ms, draw_ms,
                                           enemies_count, bullets_count, particles_count, players_alive)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (self._session_id, ts, elapsed, frame, fps, dt_ms, update_ms, draw_ms,
                  enemies_count, bullets_count, particles_count, players_alive)
        self._enqueue("sql", (sql, params))

    def increment_frame(self):
        with self._lock:
            self._frame_counter += 1
        return self._frame_counter

    # --- Query helpers for CLI ---
    def query_sql(self, sql, params=()):
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_sessions(self, limit=10):
        return self.query_sql("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,))

    def get_state_changes(self, session_id=None, limit=100):
        if session_id:
            return self.query_sql("SELECT * FROM state_changes WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit))
        else:
            return self.query_sql("SELECT * FROM state_changes ORDER BY id DESC LIMIT ?", (limit,))

    def get_events(self, session_id=None, tag=None, level=None, limit=100, search=None):
        sql = "SELECT * FROM events WHERE 1=1"
        params = []
        if session_id:
            sql += " AND session_id=?"
            params.append(session_id)
        if tag:
            sql += " AND tag=?"
            params.append(tag)
        if level:
            sql += " AND level=?"
            params.append(level)
        if search:
            sql += " AND (message LIKE ? OR extra_json LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return self.query_sql(sql, params)

    def get_exceptions(self, session_id=None, limit=50):
        if session_id:
            return self.query_sql("SELECT * FROM exceptions_log WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, limit))
        else:
            return self.query_sql("SELECT * FROM exceptions_log ORDER BY id DESC LIMIT ?", (limit,))

    def get_gameplay(self, session_id=None, event_type=None, limit=100):
        sql = "SELECT * FROM gameplay WHERE 1=1"
        params = []
        if session_id:
            sql += " AND session_id=?"
            params.append(session_id)
        if event_type:
            sql += " AND event_type=?"
            params.append(event_type)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return self.query_sql(sql, params)

    def get_crash_breadcrumbs(self, session_id):
        """Get last 30 events before a crash for root cause analysis"""
        # Get last state change to menu from playing
        crashes = self.query_sql("""
            SELECT * FROM state_changes 
            WHERE session_id=? AND old_state='playing' AND new_state='menu' 
            ORDER BY id DESC LIMIT 5
        """, (session_id,))
        result = []
        for crash in crashes:
            frame = crash["frame"]
            # Get 30 events before that frame
            events = self.query_sql("""
                SELECT * FROM events 
                WHERE session_id=? AND frame <= ? AND frame >= ?
                ORDER BY frame DESC, id DESC LIMIT 50
            """, (session_id, frame, max(0, frame-100)))
            result.append((crash, events))
        return result

    def stats(self):
        sessions = self.query_sql("SELECT COUNT(*) as c FROM sessions")[0]["c"]
        events = self.query_sql("SELECT COUNT(*) as c FROM events")[0]["c"]
        state_changes = self.query_sql("SELECT COUNT(*) as c FROM state_changes")[0]["c"]
        gameplay = self.query_sql("SELECT COUNT(*) as c FROM gameplay")[0]["c"]
        exceptions = self.query_sql("SELECT COUNT(*) as c FROM exceptions_log")[0]["c"]
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "sessions": sessions,
            "events": events,
            "state_changes": state_changes,
            "gameplay": gameplay,
            "exceptions": exceptions,
            "db_size_bytes": size,
            "db_path": str(self.db_path)
        }

    def prune_old_sessions(self, keep_last=20):
        """Keep only last N sessions to control DB size"""
        rows = self.query_sql("SELECT id FROM sessions ORDER BY id DESC LIMIT -1 OFFSET ?", (keep_last,))
        if not rows:
            return 0
        ids = [r["id"] for r in rows]
        if not ids:
            return 0
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        for table in ["events", "state_changes", "gameplay", "perf_samples", "inputs", "exceptions_log"]:
            cur.execute(f"DELETE FROM {table} WHERE session_id IN ({placeholders})", ids)
        cur.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", ids)
        conn.commit()
        conn.close()
        # Vacuum to reclaim space
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("VACUUM;")
        conn.close()
        return len(ids)


# Global singleton
debug_logger = DebugLogger()

# Convenience wrappers that match old _trace_log API but go to new logger
def log_event(tag, message, level="INFO", extra=None, with_stack=False):
    debug_logger.log_event(tag, message, level, extra, with_stack)

def log_state(old_state, new_state, reason, extra=None):
    debug_logger.log_state_change(old_state, new_state, reason, extra)

def log_gameplay(event_type, level_idx=-1, player_id=None, data=None):
    debug_logger.log_gameplay(event_type, level_idx, player_id, data=data)

def log_crash(where, exc, extra=None):
    debug_logger.log_exception(where, exc, extra)

def log_input(input_type, device="", code="", value=0, mapped_action="", extra=None):
    debug_logger.log_input(input_type, device, code, value, mapped_action, extra)

# Legacy compatibility for old code using _trace_log
def legacy_trace_log(tag, msg, with_stack=False, level="INFO"):
    debug_logger.log_event(tag, msg, level, extra=None, with_stack=with_stack)

# CLI
def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Tank93 Debug Logger Query CLI - 0 latency SQLite queries")
    sub = parser.add_subparsers(dest="cmd")

    q = sub.add_parser("query", help="Query logs")
    q.add_argument("--session", type=int, help="Session ID (default: last)")
    q.add_argument("--last", action="store_true", help="Use last session")
    q.add_argument("--tag", help="Filter by tag (e.g., STATE, BUG, CRASH, INPUT)")
    q.add_argument("--level", help="Filter by level (DEBUG, INFO, WARN, ERROR, FATAL)")
    q.add_argument("--search", help="Search message")
    q.add_argument("--state-changes", action="store_true", help="Show state changes")
    q.add_argument("--crashes", action="store_true", help="Show crashes")
    q.add_argument("--gameplay", help="Filter gameplay by event_type")
    q.add_argument("--inputs", action="store_true", help="Show inputs")
    q.add_argument("--limit", type=int, default=50, help="Limit rows")
    q.add_argument("--breadcrumbs", action="store_true", help="Show crash breadcrumbs for last menu bounce")

    s = sub.add_parser("sessions", help="List sessions")
    s.add_argument("--limit", type=int, default=20)

    st = sub.add_parser("stats", help="DB stats")

    pr = sub.add_parser("prune", help="Prune old sessions")
    pr.add_argument("--keep", type=int, default=20, help="Keep last N sessions")

    tail = sub.add_parser("tail", help="Tail text log")
    tail.add_argument("--lines", type=int, default=100)

    args = parser.parse_args()

    logger = DebugLogger()

    if not args.cmd or args.cmd == "query":
        session_id = args.session
        if args.last or session_id is None:
            # get last session id
            rows = logger.query_sql("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
            if rows:
                last_id = rows[0]["id"]
                if session_id is None:
                    session_id = last_id
                print(f"Using session {last_id} (last)")
            else:
                print("No sessions found")
                return

        if args.breadcrumbs:
            # Special: show last playing->menu with breadcrumbs
            print(f"\n=== Crash breadcrumbs for session {session_id} - last playing->menu bounces ===")
            crumbs = logger.get_crash_breadcrumbs(session_id)
            if not crumbs:
                print("No playing->menu state changes found in this session")
            for crash, events in crumbs:
                print(f"\n--- Bounce at frame {crash['frame']} elapsed {crash['elapsed_ms']}ms ---")
                print(f"  {crash['old_state']} -> {crash['new_state']} reason={crash['reason']}")
                print(f"  ts={crash['ts']}")
                if crash['extra_json']:
                    print(f"  extra={crash['extra_json'][:500]}")
                print(f"\n  Last events before bounce:")
                for ev in reversed(events[-20:]):  # chronological
                    print(f"    [F{ev['frame']} {ev['level']} {ev['tag']}] {ev['message']}")
            return

        if args.state_changes:
            rows = logger.get_state_changes(session_id=session_id, limit=args.limit)
            print(f"\n=== State changes for session {session_id} (last {args.limit}) ===")
            for r in rows:
                print(f"[F{r['frame']} +{r['elapsed_ms']}ms] {r['old_state']} -> {r['new_state']} | {r['reason']} | extra={r['extra_json']} | ts={r['ts']}")
            return

        if args.crashes:
            rows = logger.get_exceptions(session_id=session_id, limit=args.limit)
            print(f"\n=== Exceptions for session {session_id} (last {args.limit}) ===")
            for r in rows:
                print(f"\n[F{r['frame']} {r['ts']}] WHERE={r['where']} {r['exc_type']}: {r['message']}")
                if r['traceback']:
                    print(r['traceback'][:1000])
            return

        if args.gameplay:
            rows = logger.get_gameplay(session_id=session_id, event_type=args.gameplay, limit=args.limit)
            print(f"\n=== Gameplay {args.gameplay} for session {session_id} ===")
            for r in rows:
                print(f"[F{r['frame']} lvl={r['level_idx']} p={r['player_id']}] {r['event_type']} data={r['data_json']}")
            return

        if args.inputs:
            rows = logger.query_sql("SELECT * FROM inputs WHERE session_id=? ORDER BY id DESC LIMIT ?", (session_id, args.limit))
            print(f"\n=== Inputs for session {session_id} ===")
            for r in rows:
                print(f"[F{r['frame']} {r['input_type']} {r['device']} {r['code']}={r['value']} -> {r['mapped_action']}] extra={r['extra_json']}")
            return

        # Default: events query
        rows = logger.get_events(session_id=session_id, tag=args.tag, level=args.level, limit=args.limit, search=args.search)
        print(f"\n=== Events for session {session_id} tag={args.tag} level={args.level} search={args.search} (last {args.limit}) ===")
        for r in rows:
            print(f"[F{r['frame']} +{r['elapsed_ms']}ms {r['level']} {r['tag']}] {r['message']} | extra={r['extra_json']}")

    elif args.cmd == "sessions":
        rows = logger.get_sessions(limit=args.limit)
        print(f"\n=== Last {args.limit} sessions ===")
        for r in rows:
            print(f"ID={r['id']} started={r['started_at']} ended={r['ended_at']} commit={r['git_commit']} screen={r['screen_w']}x{r['screen_h']} fs={r['is_fullscreen']} joy={r['joystick_count']} lvl={r['initial_level']} players={r['num_players']}")

    elif args.cmd == "stats":
        s = logger.stats()
        print("\n=== Debug DB Stats ===")
        for k, v in s.items():
            print(f"  {k}: {v}")
        # Show recent errors count
        err_count = logger.query_sql("SELECT COUNT(*) as c FROM events WHERE level IN ('ERROR','FATAL')")[0]["c"]
        print(f"  error_events: {err_count}")
        exc_count = logger.query_sql("SELECT COUNT(*) as c FROM exceptions_log")[0]["c"]
        print(f"  exceptions: {exc_count}")

    elif args.cmd == "prune":
        deleted = logger.prune_old_sessions(keep_last=args.keep)
        print(f"Pruned {deleted} old sessions, kept last {args.keep}")

    elif args.cmd == "tail":
        if not LOG_TXT_PATH.exists():
            print(f"No text log at {LOG_TXT_PATH}")
            return
        with open(LOG_TXT_PATH, 'r') as f:
            lines = f.readlines()
            for l in lines[-args.lines:]:
                print(l.rstrip())

if __name__ == "__main__":
    _cli()
