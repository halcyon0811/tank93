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

def discover_hosts(timeout=3):
    """Broadcast discovery + subnet scan fallback (for Lida No route case)"""
    # Use the improved implementation from game.network
    try:
        from game.network import discover_hosts as net_discover
        hosts = net_discover(timeout=timeout, verbose=True)
        # Convert (ip,port,addr) to (ip,port,reply) format expected by remote_client
        # net_discover returns (ip,port,addr) where addr is (ip,port)
        result = []
        for ip, port, addr in hosts:
            # fake reply dict
            result.append((ip, port, {"ip": ip, "port": port, "from": str(addr)}))
        return result
    except Exception as e:
        print(f"[Discovery] Using fallback local discovery due to {e}")
        import socket, json
        print(f"[Discovery] Scanning for Tank93 hosts on same WiFi (broadcasting to 255.255.255.255:9998 and 192.168.0.255:9998)...")
        found = []
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            msg = json.dumps({"type": "discovery", "player_id": 2}).encode()
            for bcast in ["255.255.255.255", "192.168.0.255", "192.168.1.255", "10.0.0.255"]:
                try:
                    sock.sendto(msg, (bcast, 9998))
                except:
                    pass
            for bcast in ["255.255.255.255"]:
                try:
                    sock.sendto(msg, (bcast, 9999))
                except:
                    pass
            start = time.time()
            while time.time() - start < timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    try:
                        reply = json.loads(data.decode())
                        if reply.get("type") == "host_info":
                            ip = reply.get("ip") or addr[0]
                            port = reply.get("port", 9999)
                            print(f"  Found host at {ip}:{port} from {addr} - {reply}")
                            if (ip, port) not in [(h[0], h[1]) for h in found]:
                                found.append((ip, port, reply))
                    except:
                        pass
                except socket.timeout:
                    break
        except Exception as e:
            print(f"[Discovery] Error: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        return found

def main():
    parser = argparse.ArgumentParser(description="Tank93 Remote P2 Client - Join host on same WiFi")
    parser.add_argument('--host', required=False, default=None, help='Host IP address (shown on host HUD). If not provided, will auto-discover via broadcast')
    parser.add_argument('--port', type=int, default=9999, help='Host port (default 9999)')
    args = parser.parse_args()

    print("=== Tank93 Remote P2 Client ===")
    if args.host:
        print(f"Intended host: {args.host}:{args.port} (from --host)")
    else:
        print("No --host provided, will auto-discover hosts on same WiFi via broadcast")
    print(f"Your local IP: {get_local_ip()}")
    print("\nControls for P2 remote:")
    print("  Keyboard: WASD or ARROWS to move, SPACE/ENTER to shoot")
    print("  Joy-Con: Stick to move, L/ZL/SL/SR shoulder to shoot (not D-pad)")
    print("  Press ESC or close window to quit")
    print("\nHost must be running: python3 main.py on same WiFi")
    print("Host will show: 'Remote P2 connected' when you start sending input")
    print("\nHow to find host IP:")
    print("  On host Mac, look at HUD: LAN Host: 192.168.x.x:9999")
    print("  Or in host terminal: [Network] Host listening on 192.168.x.x:9999")
    print("  Or on host run: python3 -c \"from game.network import get_local_ip; print(get_local_ip())\"")
    print()

    # Auto-discovery if no host provided
    if not args.host:
        print("=== Auto-discovery ===")
        found = discover_hosts(timeout=4)
        if not found:
            print("No hosts found via broadcast. Make sure:")
            print("  1. Host is running python3 main.py on same WiFi")
            print("  2. Both machines on same subnet (e.g., 192.168.0.x)")
            print("  3. Firewall allows UDP 9999 and 9998")
            print("  4. Try manual: python3 remote_client.py --host <host_ip_from_HUD>")
            print("\nTrying to find hosts via ARP scan of 192.168.0.x with port 9999 open...")
            # Quick scan of common 192.168.0.x hosts that responded to ping earlier
            # We will try to discover via main port as well
            return
        else:
            print(f"Found {len(found)} host(s):")
            for i, (ip, port, info) in enumerate(found):
                print(f"  [{i}] {ip}:{port} - {info}")
            # Choose first
            args.host, args.port = found[0][0], found[0][1]
            print(f"Auto-selected host {args.host}:{args.port}")

    print(f"\nConnecting to host {args.host}:{args.port}")
    print("Starting...")

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

    # Quick connectivity check - non-blocking for Lida case where discovery floods logs but game input never starts
    # If --host provided explicitly, we trust it and start game loop immediately even if test fails
    # Previous version did 3 attempts + 4 sec broadcast + 10 sec subnet scan = 15 sec blocked before game loop, causing only discovery packets to be seen
    print(f"\n[Testing] Quick check host {args.host}:{args.port} (will start game loop regardless, to allow immediate driving)...")
    import socket, json
    reachable = False
    quick_sock = None
    try:
        quick_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        quick_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        quick_sock.settimeout(1.5)
        test_msg = json.dumps({"type": "discovery", "player_id": 2}).encode()
        quick_sock.sendto(test_msg, (args.host, args.port))
        print(f"  Sent quick discovery to {args.host}:{args.port}, waiting 1.5s...")
        try:
            data, addr = quick_sock.recvfrom(1024)
            reply = json.loads(data.decode())
            print(f"  ✓ Host {args.host} responded! {reply} from {addr}")
            reachable = True
        except socket.timeout:
            print(f"  ⚠ No immediate reply (will still start game loop - Lida can try driving, and background retry will continue)")
            # Don't block, will start game loop and retry in background via send_input failures triggering discovery
        except OSError as e:
            print(f"  ⚠ Send failed (No route?): {e} - will still start game loop and keep trying to send input")
    except Exception as e:
        print(f"  Quick check error: {e} - proceeding to game loop anyway")
    finally:
        if quick_sock:
            try:
                quick_sock.close()
            except:
                pass

    if reachable:
        print(f"  ✓ Host reachable, starting game loop with 30Hz + change detection (fixed Lida drive bug)...")
    else:
        print(f"  → Starting game loop immediately (even though quick check failed).")
        print(f"    If you see discovery spam in host logs but no 'Lida CONNECTED', it means input packets not arriving (firewall/AP isolation)")
        print(f"    Try: ping {args.host} from this machine. If ping fails -> different WiFi or AP isolation.")
        print(f"    Firewall: macOS System Settings -> Firewall -> allow Python")
        print(f"    Alternative: both join phone hotspot")

    # For button mapping, try to load custom mapping
    from game.input_manager import load_mapping
    mapping = load_mapping()
    print(f"Using mapping: {mapping.get('name','default')}")

    running = True
    last_send = 0
    send_interval = 1/30  # 30 Hz for smoother control (was 20Hz, Lida reported cannot drive = need more responsive)
    consecutive_failures = 0
    last_fail_msg_time = 0
    last_sent_dir = None
    last_sent_shoot = False

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
            # FIX: Previously joy took absolute precedence even if None, keyboard fallback already via `or`
            # Now ensure keyboard always works even if joystick idle (important for Lida)
            final_dir = dir_joy or dir_keyboard
            final_shoot = shoot_joy or shoot_keyboard

            # Send at 30Hz + immediately on direction/shoot change for responsiveness (fix cannot drive)
            now = time.time()
            changed = (final_dir != last_sent_dir) or (final_shoot != last_sent_shoot)
            if changed or (now - last_send > send_interval):
                success = client.send_input(final_dir, final_shoot)
                if changed:
                    print(f"[Input] Sending dir={final_dir} shoot={final_shoot} (changed)")
                # update last sent for change detection
                last_sent_dir = final_dir
                last_sent_shoot = final_shoot
                if not success:
                    consecutive_failures += 1
                    # Reduced spam for No route case - don't block game loop with discovery (causes freeze and only discovery packets seen on host)
                    # Lida case: 192.168.0.131 -> 192.168.0.194 No route, but broadcast fallback should now make it work
                    if consecutive_failures % 90 == 0:  # every 3 seconds at 30 Hz
                        print(f"[Warning] Failed to send to {args.host}:{args.port} ({consecutive_failures} fails) - using broadcast fallback")
                        if time.time() - last_fail_msg_time > 10:  # only detailed diag every 10 sec, not 5
                            last_fail_msg_time = time.time()
                            print(f"  Diagnostics: local={get_local_ip()} host={args.host}:{args.port} - broadcast fallback active")
                            print(f"  Host should see packets via broadcast even if unicast No route (AP isolation workaround)")
                            print(f"  If still not working, try phone hotspot for both")
                            # Don't call discover_hosts here (blocks 2 sec) - that was causing host to see only discovery floods
                else:
                    if consecutive_failures > 0 and consecutive_failures % 90 == 0:
                        print(f"[Network] Recovered, now sending to {args.host} (failures reset)")
                    consecutive_failures = 0
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
