#!/usr/bin/env python3
"""
Tank 90 Enhanced - Main Entry
Pygame prototype for PC, structured for Nintendo Switch port via Godot/Unity.

Controls:
 P1: WASD + SPACE (shoot) + Q for special | Gamepad LS + A
 P2: ARROWS + ENTER (shoot) + P special | Gamepad 2
 General: M mute, P pause, ESC menu
"""
from game.game import Game

if __name__ == "__main__":
    game = Game()
    game.run()
