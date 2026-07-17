#!/usr/bin/env python3
"""
Joy-Con Debugger for Tank93
Run this to see exactly what your Joy-Con sends to pygame.
Press buttons, move stick, and it will print mapping.
Helps us fix Joy-Con control issues.
"""
import pygame
import time

pygame.init()
pygame.joystick.init()

def rescan():
    pygame.joystick.init()
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            joysticks.append(js)
        except Exception as e:
            print(f"Failed to init joystick {i}: {e}")
    return joysticks

joysticks = rescan()
print(f"Found {len(joysticks)} joystick(s)")
for idx, js in enumerate(joysticks):
    print(f"  {idx}: {js.get_name()} - axes:{js.get_numaxes()} btns:{js.get_numbuttons()} hats:{js.get_numhats()}")

if not joysticks:
    print("\nNo joystick found! Steps to connect Joy-Con on Mac:")
    print("1. System Settings > Bluetooth > ON")
    print("2. Hold SYNC button on Joy-Con (between SL/SR) 3 sec until lights blink")
    print("3. Click Connect in Mac BT list")
    print("4. Run this script again")
    print("\nWaiting 15 sec for Joy-Con to connect...")
    for _ in range(15):
        time.sleep(1)
        pygame.event.pump()
        count = pygame.joystick.get_count()
        if count > len(joysticks):
            print(f"New joystick detected! Count now {count}")
            joysticks = rescan()
            for idx, js in enumerate(joysticks):
                print(f"  {idx}: {js.get_name()}")
            break
        print(".", end="", flush=True)
    print()

print("\n=== LIVE TEST (20 sec) ===")
print("Move stick, press D-pad, press A/B/X/Y, SL/SR, L/R, +/-")
print("Press Ctrl+C to exit early")
print("")

screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Joy-Con Debug - Check Terminal")
clock = pygame.time.Clock()

start = time.time()
try:
    while time.time() - start < 20:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt
            if event.type == pygame.JOYDEVICEADDED:
                print(f"\n[ADDED] device_index={event.device_index}")
                joysticks = rescan()
            if event.type == pygame.JOYDEVICEREMOVED:
                print(f"\n[REMOVED] instance_id={event.instance_id}")
                joysticks = rescan()
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"[BUTTON DOWN] joy={event.instance_id if hasattr(event,'instance_id') else '?'} btn={event.button}")
            if event.type == pygame.JOYBUTTONUP:
                print(f"[BUTTON UP] btn={event.button}")

        # Poll current state
        for idx, js in enumerate(joysticks):
            try:
                axes = [js.get_axis(a) for a in range(js.get_numaxes())]
                # Only print if significant movement
                moving = any(abs(a)>0.3 for a in axes)
                btns = [b for b in range(js.get_numbuttons()) if js.get_button(b)]
                hats = [js.get_hat(h) for h in range(js.get_numhats())]
                if moving or btns or any(h!=(0,0) for h in hats):
                    print(f"Joy{idx} {js.get_name()}: Axes={[f'{a:.2f}' for a in axes]} Btns={btns} Hats={hats}")
            except Exception as e:
                print(f"Error reading joy {idx}: {e}")

        screen.fill((20,20,30))
        font = pygame.font.Font(None, 20)
        txt = font.render(f"Joysticks: {len(joysticks)} - See terminal", True, (255,255,255))
        screen.blit(txt, (20,20))
        txt2 = font.render("Move stick / press buttons", True, (200,200,200))
        screen.blit(txt2, (20,50))
        pygame.display.flip()
        clock.tick(30)

except KeyboardInterrupt:
    print("\nExited by user")

print("\n=== END ===")
print("Copy the printed lines and send them, especially:")
print("- Which button numbers correspond to Up/Down/Left/Right D-pad")
print("- Which button numbers are A/B/X/Y and SL/SR and +/-")
print("This will let me fix Joy-Con mapping perfectly")
pygame.quit()
