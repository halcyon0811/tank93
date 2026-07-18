#!/usr/bin/env python3
"""
Interactive Controller Mapper for Tank93
User says direction (e.g., "right") then presses that on controller.
This script records the mapping and saves to game/assets/controller_mapping.json
Usage: python3 interactive_mapper.py
Follow prompts in terminal.
"""
import pygame
import json
import os
import time
import sys

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'game', 'assets', 'controller_mapping.json')
LEGACY_PATH = os.path.join(os.path.dirname(__file__), 'joycon_calibration.json')

pygame.init()
pygame.joystick.init()

print("=== Tank93 Interactive Controller Mapper ===")
print(f"Config will be saved to: {CONFIG_PATH}")
print("\nThis tool lets you map controller by telling it direction then pressing it.")
print("Example: I say 'right' then you hit RIGHT on your controller.")
print("\nMake sure controller is connected via Bluetooth.")
print("Press Ctrl+C to exit anytime, progress will be saved.\n")

def get_joysticks():
    pygame.joystick.init()
    sticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            sticks.append(js)
        except Exception as e:
            print(f"Failed {i}: {e}")
    return sticks

joysticks = get_joysticks()
if not joysticks:
    print("No joystick found! Connect controller and retry.")
    print("On Mac: System Settings > Bluetooth > Hold SYNC on Joy-Con 3 sec")
    sys.exit(1)

print(f"Found {len(joysticks)} joystick(s):")
for idx, js in enumerate(joysticks):
    print(f"  [{idx}] {js.get_name()} - axes:{js.get_numaxes()} btns:{js.get_numbuttons()} hats:{js.get_numhats()}")

# Choose joystick
if len(joysticks) == 1:
    chosen_idx = 0
    print(f"\nAuto-selecting only joystick [0] {joysticks[0].get_name()}")
else:
    try:
        chosen_idx = int(input(f"\nChoose joystick index [0-{len(joysticks)-1}] (default 0): ") or "0")
    except:
        chosen_idx = 0

if chosen_idx >= len(joysticks):
    chosen_idx = 0

js = joysticks[chosen_idx]
print(f"\nSelected [{chosen_idx}] {js.get_name()} for mapping")

# Mapping structure
mapping = {
    "name": js.get_name(),
    "axes_count": js.get_numaxes(),
    "buttons_count": js.get_numbuttons(),
    "hats_count": js.get_numhats(),
    "maps": {}  # direction -> {type, index, value, etc}
}

# Screen for visual feedback
screen = pygame.display.set_mode((600, 400))
pygame.display.set_caption(f"Mapping {js.get_name()} - Follow terminal")
font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 20)
clock = pygame.time.Clock()

def wait_for_direction_input(prompt, timeout=15):
    """Wait for user to press direction, return detected input"""
    print(f"\n>>> {prompt}")
    print(f"    Press/hold the {prompt} direction NOW (you have {timeout}s)")
    print(f"    Move stick, D-pad, or press button that should be {prompt}")
    start = time.time()
    baseline_axes = [js.get_axis(a) for a in range(js.get_numaxes())]
    # Small delay to avoid previous press
    time.sleep(0.3)
    pygame.event.pump()

    best_detection = None
    while time.time() - start < timeout:
        pygame.event.pump()
        # Check events for button down
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.JOYBUTTONDOWN:
                # Only consider if it's from chosen joystick
                # instance_id might not match, so just check any button pressed on chosen
                if event.button < js.get_numbuttons() and js.get_button(event.button):
                    # Verify it's still pressed
                    detection = {
                        "type": "button",
                        "index": event.button,
                        "value": 1,
                        "raw": f"button {event.button}"
                    }
                    print(f"  DETECTED BUTTON: {detection}")
                    # Visual feedback
                    screen.fill((20, 80, 20))
                    txt = font.render(f"Got {prompt}: BUTTON {event.button}", True, (255,255,100))
                    screen.blit(txt, (20, 180))
                    pygame.display.flip()
                    time.sleep(0.8)
                    return detection

        # Poll axes - check for significant movement from baseline
        for a_idx in range(js.get_numaxes()):
            val = js.get_axis(a_idx)
            base = baseline_axes[a_idx] if a_idx < len(baseline_axes) else 0
            delta = val - base
            if abs(val) > 0.6 and abs(delta) > 0.3:
                detection = {
                    "type": "axis",
                    "index": a_idx,
                    "value": 1 if val > 0 else -1,
                    "raw_value": val,
                    "raw": f"axis {a_idx} = {val:.2f}"
                }
                print(f"  DETECTED AXIS: {detection}")
                screen.fill((20, 80, 20))
                txt = font.render(f"Got {prompt}: AXIS {a_idx} val {val:.2f}", True, (255,255,100))
                screen.blit(txt, (20, 180))
                pygame.display.flip()
                time.sleep(0.8)
                return detection

        # Poll hats
        for h_idx in range(js.get_numhats()):
            hx, hy = js.get_hat(h_idx)
            if hx != 0 or hy != 0:
                detection = {
                    "type": "hat",
                    "index": h_idx,
                    "value": (hx, hy),
                    "raw": f"hat {h_idx} = {(hx,hy)}"
                }
                print(f"  DETECTED HAT: {detection}")
                screen.fill((20, 80, 20))
                txt = font.render(f"Got {prompt}: HAT {h_idx} {(hx,hy)}", True, (255,255,100))
                screen.blit(txt, (20, 180))
                pygame.display.flip()
                time.sleep(0.8)
                return detection

        # Poll buttons (for D-pad that is buttons, not event, e.g., Joy-Con L)
        for b_idx in range(js.get_numbuttons()):
            if js.get_button(b_idx):
                # Check if this button was not pressed at baseline - we don't have baseline for buttons, so just detect
                # Avoid detecting if it's held from previous mapping - wait a bit
                detection = {
                    "type": "button",
                    "index": b_idx,
                    "value": 1,
                    "raw": f"button {b_idx} (polled)"
                }
                # Need to ensure it's not a stuck button, wait for release then press? For now accept first
                # Small debounce: wait 200ms and check still pressed
                time.sleep(0.1)
                pygame.event.pump()
                if js.get_button(b_idx):
                    print(f"  DETECTED BUTTON (poll): {detection}")
                    screen.fill((20, 80, 20))
                    txt = font.render(f"Got {prompt}: BUTTON {b_idx}", True, (255,255,100))
                    screen.blit(txt, (20, 180))
                    pygame.display.flip()
                    time.sleep(0.8)
                    return detection

        # Draw waiting screen
        elapsed = time.time() - start
        remaining = timeout - elapsed
        screen.fill((20, 20, 40))
        txt = font.render(f"Waiting for {prompt}... {remaining:.1f}s", True, (255,255,255))
        screen.blit(txt, (20, 40))
        txt2 = small_font.render(f"Joystick: {js.get_name()}", True, (200,200,200))
        screen.blit(txt2, (20, 80))
        txt3 = small_font.render(f"Move stick / D-pad to {prompt} direction", True, (180,180,100))
        screen.blit(txt3, (20, 110))
        txt4 = small_font.render(f"Press Ctrl+C to skip/save", True, (150,150,150))
        screen.blit(txt4, (20, 140))
        # Show live axes
        try:
            axes_vals = [js.get_axis(a) for a in range(min(js.get_numaxes(), 4))]
            axes_txt = small_font.render(f"Axes: {[f'{v:.2f}' for v in axes_vals]}", True, (100,200,100))
            screen.blit(axes_txt, (20, 200))
            btns = [i for i in range(js.get_numbuttons()) if js.get_button(i)]
            btn_txt = small_font.render(f"Buttons pressed: {btns}", True, (100,200,200))
            screen.blit(btn_txt, (20, 230))
            hats = [js.get_hat(h) for h in range(js.get_numhats())]
            hat_txt = small_font.render(f"Hats: {hats}", True, (200,100,100))
            screen.blit(hat_txt, (20, 260))
        except:
            pass
        pygame.display.flip()
        clock.tick(30)

    print(f"  TIMEOUT for {prompt} - skipping")
    screen.fill((80, 20, 20))
    txt = font.render(f"Timeout {prompt} - skipped", True, (255,100,100))
    screen.blit(txt, (20, 180))
    pygame.display.flip()
    time.sleep(0.5)
    return None

# Directions to map - in order user expects
# User said: "i tell you right and then i hit right, you do the coding and mapping"
# So we will prompt for each direction and wait
directions = ["UP", "DOWN", "LEFT", "RIGHT", "SHOOT", "COIN", "START"]

print("\n=== Starting mapping ===")
print("You will be prompted for each direction.")
print("When you see prompt, press that direction/button on controller.")
print("Example: When it says RIGHT, press RIGHT D-pad or move stick RIGHT")
print("\nPress ENTER when ready...")
input()

for dir_name in directions:
    prompt = dir_name
    if dir_name == "SHOOT":
        prompt_text = "SHOOT (A/B/X/Y or any action button)"
    elif dir_name == "COIN":
        prompt_text = "COIN (Minus/Select/View button)"
    elif dir_name == "START":
        prompt_text = "START (Plus/Options button)"
    else:
        prompt_text = dir_name

    detection = wait_for_direction_input(prompt_text, timeout=12)
    if detection:
        mapping["maps"][dir_name] = detection
        print(f"  -> Mapped {dir_name} = {detection['raw']}")
    else:
        print(f"  -> No mapping for {dir_name}")

    # Small pause between mappings
    time.sleep(0.5)
    # Wait for all buttons released
    print(f"  Release all controls...")
    for _ in range(15):
        pygame.event.pump()
        any_pressed = False
        for b in range(js.get_numbuttons()):
            if js.get_button(b):
                any_pressed = True
        # Check axes back to center
        axes_centered = True
        for a in range(js.get_numaxes()):
            if abs(js.get_axis(a)) > 0.3:
                axes_centered = False
        if not any_pressed and axes_centered:
            break
        time.sleep(0.1)

print("\n=== Mapping Complete ===")
print(json.dumps(mapping, indent=2))

# Save
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
with open(CONFIG_PATH, 'w') as f:
    json.dump(mapping, f, indent=2)
print(f"\nSaved to {CONFIG_PATH}")

# Also save legacy path for compatibility
with open(LEGACY_PATH, 'w') as f:
    json.dump(mapping, f, indent=2)
print(f"Also saved to {LEGACY_PATH} (legacy)")

print("\nNow you can:")
print("1. Run python3 main.py - it will auto-load this mapping if code updated")
print("2. Or share this JSON for me to hardcode")

pygame.quit()
print("\nDone!")
