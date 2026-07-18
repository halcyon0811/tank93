#!/usr/bin/env python3
"""
Remote P2 Client for Tank93 LAN Multiplayer
Run on second machine on same local network to control P2 tank on host.

Usage:
  python3 remote_client.py --host 192.168.1.100
  python3 remote_client.py --host 192.168.1.100 --port 9999

Controls:
  P2: ARROWS / WASD / Gamepad stick + SPACE/ENTER for shoot
  Or Joy-Con: stick + any action button

Host must be running: python3 main.py (it auto-starts server on port 9999)
"""
import argparse
import pygame
import time
import sys
import os

# Add game path for network module
sys.path.insert(0, os.path.dirname(__file__))
from game.network import NetworkClient, get_local_ip
from game.input_manager import get_direction_from_joystick, get_buttons_from_joystick

def get_keyboard_direction(keys):
    """Get direction from keyboard for P2 client"""
    up = keys[pygame.K_w] or keys[pygame.K_UP]
    down = keys[pygame.K_s] or keys[pygame.K_DOWN]
    left = keys[pygame.K_a] or keys[pygame.K_LEFT]
    right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

    if up and left:
        return 'UP_LEFT'
    if up and right:
        return 'UP_RIGHT'
    if down and left:
        return 'DOWN_LEFT'
    if down and right:
        return 'DOWN_RIGHT'
    if up:
        return 'UP'
    if down:
        return 'DOWN'
    if left:
        return 'LEFT'
    if right:
        return 'RIGHT'
    return None

def main():
    parser = argparse.ArgumentParser(description="Tank93 Remote P2 Client")
    parser.add_argument('--host', required=True, help='Host IP address (shown on host HUD)')
    parser.add_argument('--port', type=int, default=9999, help='Host port (default 9999)')
    args = parser.parse_args()

    print("=== Tank93 Remote P2 Client ===")
    print(f"Connecting to host {args.host}:{args.port}")
    print(f"Your local IP: {get_local_ip()}")
    print("\nControls for P2 remote:")
    print("  Keyboard: WASD or ARROWS to move, SPACE/ENTER to shoot")
    print("  Joy-Con: Stick to move, any action button to shoot")
    print("  Press ESC or close window to quit")
    print("\nHost must be running: python3 main.py")
    print("Host will show: 'Remote P2 connected' when you start sending input")
    print("\nStarting...")

    pygame.init()
    pygame.joystick.init()

    # Try to find joystick
    joysticks = []
    for i in range(pygame.joystick.get_count()):
        try:
            js = pygame.joystick.Joystick(i)
            js.init()
            joysticks.append(js)
            print(f"Found joystick {i}: {js.get_name()}")
        except:
            pass

    # If no joystick, keyboard only
    if not joysticks:
        print("No joystick found, using keyboard only")

    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption(f"P2 Remote Client -> {args.host}")
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    client = NetworkClient(args.host, args.port)
    if not client.start():
        print("Failed to start client")
        return

    # For button mapping, try to load custom mapping
    from game.input_manager import load_mapping
    mapping = load_mapping()
    print(f"Using mapping: {mapping.get('name','default')}")

    running = True
    last_send = 0
    send_interval = 1/20  # 20 Hz

    try:
        while running:
            dt = clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            keys = pygame.key.get_pressed()
            # Keyboard direction
            dir_keyboard = get_keyboard_direction(keys)
            shoot_keyboard = keys[pygame.K_SPACE] or keys[pygame.K_RETURN] or keys[pygame.K_RCTRL] or keys[pygame.K_LCTRL]

            # Joystick direction
            dir_joy = None
            shoot_joy = False
            if joysticks:
                # Use first joystick
                js = joysticks[0]
                # Try custom mapping first
                d = get_direction_from_joystick(js, player_id=2, num_players=2)
                if d:
                    dir_joy = d
                else:
                    # Fallback to axes
                    if js.get_numaxes() >= 2:
                        ax = js.get_axis(0)
                        ay = js.get_axis(1)
                        if abs(ax) < 0.3:
                            ax = 0
                        if abs(ay) < 0.3:
                            ay = 0
                        if ay < -0.5:
                            dir_joy = 'UP'
                        elif ay > 0.5:
                            dir_joy = 'DOWN'
                        elif ax < -0.5:
                            dir_joy = 'LEFT'
                        elif ax > 0.5:
                            dir_joy = 'RIGHT'

                btns = get_buttons_from_joystick(js, player_id=2, num_players=2)
                if btns.get("SHOOT") or btns.get("ATTACK"):
                    shoot_joy = True
                # Also any button press counts as shoot for permissive feel
                else:
                    # Check any action button (0-7) pressed
                    for b in range(min(js.get_numbuttons(), 8)):
                        if js.get_button(b):
                            # Don't count D-pad buttons 0-3 if they are used for movement? For Joy-Con L, D-pad is 0-3, but we already have axis for movement
                            # So only count buttons >=4 as shoot for Joy-Con L
                            if js.get_name().lower().find("joy-con (l)") != -1:
                                if b >= 4:
                                    shoot_joy = True
                            else:
                                shoot_joy = True

            # Combine: joystick takes precedence over keyboard if present
            final_dir = dir_joy or dir_keyboard
            final_shoot = shoot_joy or shoot_keyboard

            # Send at 20Hz or on change
            now = time.time()
            if now - last_send > send_interval:
                client.send_input(final_dir, final_shoot)
                last_send = now

            # Draw
            screen.fill((20, 20, 40))
            txt = font.render(f"Remote P2 -> {args.host}:{args.port}", True, (255,255,255))
            screen.blit(txt, (20, 20))
            txt2 = font.render(f"Dir: {final_dir or 'None'} Shoot: {final_shoot}", True, (100,255,100) if final_dir or final_shoot else (200,200,200))
            screen.blit(txt2, (20, 60))
            txt3 = font.render(f"Local IP: {get_local_ip()}", True, (150,150,200))
            screen.blit(txt3, (20, 100))
            txt4 = font.render("Controls: WASD/Arrows + SPACE", True, (180,180,180))
            screen.blit(txt4, (20, 140))
            txt5 = font.render("Joy-Con: Stick + L/ZL/SL/SR", True, (180,180,180))
            screen.blit(txt5, (20, 170))
            txt6 = font.render("ESC to quit", True, (150,150,150))
            screen.blit(txt6, (20, 240))

            pygame.display.flip()

    except KeyboardInterrupt:
        print("\nExiting")
    finally:
        client.stop()
        pygame.quit()
        print("Client stopped")

if __name__ == "__main__":
    main()
