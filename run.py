#!/usr/bin/env python3
"""Quick launcher with checks"""
import sys
try:
    import pygame
except ImportError:
    print("pygame not installed, run: pip install -r requirements.txt")
    sys.exit(1)

from game.game import Game
print("Starting Tank 90 Enhanced...")
print("P1: WASD+SPACE, P2: ARROWS+ENTER, P=Pause, ESC=Menu")
game = Game()
game.run()
