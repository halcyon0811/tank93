#!/usr/bin/env python3
"""
Tank93 Web Version - Entry point for Pygbag / Pyodide / Browser
This is the web version that can run on https://halcyon0811.github.io/tank93/ or itch.io

Differences from desktop main.py:
- No auto-venv switching (emscripten has its own venv)
- is_web=True to disable LAN UDP host and projector HTTP server (not supported in browser)
- Uses async loop for browser compatibility
- No file writes for crash.log / debug.db (in-memory only in web)
- Controls: Keyboard only in web (WASD+SPACE for P1, Arrows+Enter for P2), Gamepad via browser Gamepad API
"""

import sys
import os
import asyncio

# Detect if running in browser (emscripten)
IS_WEB = sys.platform == "emscripten" or "pyodide" in sys.modules or os.environ.get("PYGBAG") == "1"

# For Pygbag, set some env vars
os.environ['SDL_IME_SHOWUI'] = '0'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

print(f"[Web] Starting Tank93 Web Version - is_web={IS_WEB} platform={sys.platform}")
print(f"[Web] Original 35 NES maps, 700 enemies, homing+spread+rapid items, monster boss")

# Import after env setup
import pygame
from game.game import Game

async def main():
    print("[Web] Initializing pygame...")
    # Don't call pygame.init() here, Game.__init__ does it, but ensure display
    try:
        # Create game in web mode
        game = Game(is_web=True)
        print(f"[Web] Game created - is_web={game.is_web}, is_mega={game.is_mega}, screen={game.screen.get_size()}")
        print("[Web] Starting async game loop - use WASD+SPACE for P1, ARROWS+ENTER for P2")
        print("[Web] If you have gamepad connected, it should work via browser Gamepad API")
        await game.run_async()
    except Exception as e:
        print(f"[Web] Fatal error in web_main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # For Pygbag, we need to run via asyncio
    # Pygbag will call this file as main and expect async
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Web] Interrupted")
    except SystemExit:
        print("[Web] Exit")
        raise
    except Exception as e:
        print(f"[Web] Crash in __main__: {e}")
        import traceback
        traceback.print_exc()
