#!/usr/bin/env python3
"""
Tank 93 Enhanced - Main Entry
Pygame prototype for PC, structured for Nintendo Switch port via Godot/Unity.

Controls:
 P1: WASD + SPACE (shoot) + Q for special | Gamepad LS + A
 P2: ARROWS + ENTER (shoot) + P special | Gamepad 2
 General: M mute, P pause, ESC menu
"""
import os
import sys
import pathlib

# --- Auto-venv: if pygame not found in system, use .venv ---
def _ensure_pygame():
    try:
        import pygame  # noqa: F401
        return True
    except ImportError:
        # Try to find .venv relative to this file
        root = pathlib.Path(__file__).parent.resolve()
        venv_python = root / ".venv" / "bin" / "python"
        venv_site = root / ".venv" / "lib"
        # Look for site-packages
        if venv_site.exists():
            for p in venv_site.glob("python*/site-packages"):
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))
            try:
                import pygame  # noqa: F401
                return True
            except ImportError:
                pass
        # If .venv python exists and we're not it, re-exec with it
        if venv_python.exists() and pathlib.Path(sys.executable).resolve() != venv_python.resolve():
            print(f"[Auto-venv] Switching to {venv_python} for pygame-ce")
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
        return False

if not _ensure_pygame():
    print("pygame not found. Trying to install...")
    # Last resort: try pip install pygame-ce for current interpreter via --break-system-packages if needed
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame-ce", "-q", "--break-system-packages"])
        import pygame  # noqa: F401
    except Exception as e:
        print(f"Failed to auto-install pygame-ce: {e}")
        print("Please run: source .venv/bin/activate && pip install -r requirements.txt")
        sys.exit(1)

os.environ['SDL_IME_SHOWUI'] = '0'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from game.game import Game
from game.debug_logger import debug_logger
import traceback

if __name__ == "__main__":
    try:
        # Check for --fullscreen argument
        fullscreen_arg = "--fullscreen" in sys.argv or "-f" in sys.argv or "--fs" in sys.argv
        game = Game()
        if fullscreen_arg:
            print("[Main] Starting in fullscreen mode (from --fullscreen flag)")
            # Use toggle to go fullscreen (starts windowed, toggle to fullscreen)
            # Need to have display already created, so toggle after init
            game.toggle_fullscreen()
        # Log session start already done in Game.__init__
        try:
            debug_logger.log_event("MAIN", "Game started via main.py", level="INFO", extra={"argv": sys.argv, "fullscreen": fullscreen_arg})
        except:
            pass
        game.run()
    except SystemExit:
        # Normal exit via menu quit
        try:
            debug_logger.log_event("MAIN", "Game exited via SystemExit (quit)", level="INFO")
            debug_logger.end_session()
            debug_logger.stop()
        except:
            pass
        raise
    except Exception as e:
        print(f"CRASH: {e}")
        traceback.print_exc()
        try:
            debug_logger.log_exception("main.py", e, extra={"argv": sys.argv})
            debug_logger.log_event("CRASH", f"Fatal crash in main.py: {e}", level="FATAL", extra={"argv": sys.argv}, with_stack=True)
            debug_logger.end_session()
            debug_logger.stop()
        except:
            pass
        # Write crash log
        try:
            with open("crash.log", "w") as f:
                f.write(f"Crash: {e}\n")
                traceback.print_exc(file=f)
            print("Crash log written to crash.log")
        except:
            pass
        # Keep window open briefly then exit
        try:
            import pygame
            pygame.quit()
        except:
            pass
        sys.exit(1)
