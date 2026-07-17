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
os.environ['SDL_IME_SHOWUI'] = '0'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from game.game import Game
import traceback
import sys

if __name__ == "__main__":
    try:
        game = Game()
        game.run()
    except Exception as e:
        print(f"CRASH: {e}")
        traceback.print_exc()
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
