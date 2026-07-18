#!/usr/bin/env python3
"""Quick launcher with checks - auto-uses .venv if needed"""
import os, sys, pathlib

def _ensure_pygame():
    try:
        import pygame
        return True
    except ImportError:
        root = pathlib.Path(__file__).parent.resolve()
        venv_python = root / ".venv" / "bin" / "python"
        venv_site = root / ".venv" / "lib"
        if venv_site.exists():
            for p in venv_site.glob("python*/site-packages"):
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))
            try:
                import pygame
                return True
            except ImportError:
                pass
        if venv_python.exists() and pathlib.Path(sys.executable).resolve() != venv_python.resolve():
            print(f"[Auto-venv] Switching to {venv_python}")
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
        return False

if not _ensure_pygame():
    print("pygame not installed, run: pip install -r requirements.txt")
    sys.exit(1)

from game.game import Game
print("Starting Tank 93 Enhanced...")
print("P1: WASD+SPACE, P2: ARROWS+ENTER, P=Pause, ESC=Menu")
game = Game()
game.run()
