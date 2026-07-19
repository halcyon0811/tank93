import os, sys, pathlib, time, sqlite3
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['SDL_IME_SHOWUI']='0'
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import pytest

def _reinit_db():
    db_path = ROOT / "debug.db"
    # remove wal/shm first
    for suffix in ["-wal","-shm"]:
        try:
            (ROOT / f"debug.db{suffix}").unlink(missing_ok=True)
        except:
            pass
    try:
        db_path.unlink(missing_ok=True)
    except:
        pass
    time.sleep(0.1)
    # create new DB with schema
    conn = sqlite3.connect(str(db_path))
    from game.debug_logger import SCHEMA
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

@pytest.fixture(autouse=True)
def clean_db():
    # clean text log only, keep DB but reinit if needed
    try:
        (ROOT / "bug_trace.log").unlink(missing_ok=True)
    except:
        pass
    # ensure DB exists and has tables
    db_path = ROOT / "debug.db"
    if not db_path.exists():
        _reinit_db()
    else:
        # check table exists
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("SELECT COUNT(*) FROM sessions")
            conn.close()
        except:
            _reinit_db()
    yield
    try:
        from game.debug_logger import debug_logger
        # end session but don't delete DB file (keep for next test)
        debug_logger.end_session()
        time.sleep(0.1)
    except:
        pass

@pytest.fixture
def game(clean_db):
    from game.game import Game
    g = Game()
    # Wait for async network host to be ready (was blocking before, now async for fast startup)
    # Previously Game.__init__ blocked 5s for network, now 0.1s and network starts in bg thread
    for _ in range(20):  # wait up to 2 sec for network host
        if g.network_host is not None:
            break
        time.sleep(0.1)
    yield g
    try:
        from game.debug_logger import debug_logger
        debug_logger.end_session()
        time.sleep(0.1)
    except:
        pass

def get_db():
    from game.debug_logger import DebugLogger
    return DebugLogger()
