#!/usr/bin/env python3
"""
Quick Joy-Con calibration for Tank93
Run this and follow prompts to fix left/right/up/down
It will create joycon_calibration.json used by game
"""
import pygame
import json
import time
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'joycon_calibration.json')

pygame.init()
pygame.joystick.init()
screen = pygame.display.set_mode((500, 400))
pygame.display.set_caption("Joy-Con Calibration - Follow terminal")
font = pygame.font.Font(None, 24)
clock = pygame.time.Clock()

def get_joysticks():
    pygame.joystick.init()
    sticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            sticks.append(js)
        except:
            pass
    return sticks

def wait_for_input(prompt, timeout=10):
    print(f"\n>>> {prompt}")
    print("Move stick or press D-pad (5 sec)")
    start = time.time()
    while time.time() - start < timeout:
        pygame.event.pump()
        for js in get_joysticks():
            # Check axes
            for a in range(js.get_numaxes()):
                val = js.get_axis(a)
                if abs(val) > 0.6:
                    print(f"  Detected {js.get_name()} axis {a} = {val:.2f}")
                    return ('axis', js.get_name(), a, val)
            # Check buttons
            for b in range(js.get_numbuttons()):
                if js.get_button(b):
                    print(f"  Detected {js.get_name()} button {b}")
                    return ('button', js.get_name(), b, 1)
            # Check hats
            for h in range(js.get_numhats()):
                hx, hy = js.get_hat(h)
                if hx != 0 or hy != 0:
                    print(f"  Detected {js.get_name()} hat {h} = {(hx,hy)}")
                    return ('hat', js.get_name(), h, (hx,hy))
        # Draw
        screen.fill((20,20,30))
        txt = font.render(prompt, True, (255,255,100))
        screen.blit(txt, (20, 150))
        txt2 = font.render("Move stick / press D-pad - see terminal", True, (200,200,200))
        screen.blit(txt2, (20, 180))
        pygame.display.flip()
        clock.tick(30)
        time.sleep(0.05)
    print("  Timeout - no input")
    return None

print("=== Joy-Con Calibration ===")
print("This will create joycon_calibration.json")
print("Make sure Joy-Cons are connected via Bluetooth")
print("Found joysticks:")
for js in get_joysticks():
    print(f"  - {js.get_name()} axes={js.get_numaxes()} btns={js.get_numbuttons()} hats={js.get_numhats()}")

input("\nPress ENTER to start calibration for LEFT Joy-Con (or P1)...")

calib = {}

# Calibrate left
for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
    result = wait_for_input(f"LEFT Joy-Con: Press {direction} (D-pad or stick) - 5 sec", 5)
    if result:
        calib[f'LEFT_{direction}'] = result
        print(f"  Saved LEFT_{direction} = {result}")

input("\nPress ENTER for RIGHT Joy-Con (P2)...")
for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
    result = wait_for_input(f"RIGHT Joy-Con: Press {direction} - 5 sec", 5)
    if result:
        calib[f'RIGHT_{direction}'] = result
        print(f"  Saved RIGHT_{direction} = {result}")

print("\nCalibration done, saving to", CONFIG_PATH)
with open(CONFIG_PATH, 'w') as f:
    json.dump(calib, f, indent=2)
print(json.dumps(calib, indent=2))
print("\nNow run game, it will use calibration if found.")
print("If still wrong, delete file and rerun.")
pygame.quit()
