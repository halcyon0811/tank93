"""
Network Manager for Tank93 LAN Multiplayer
Allows second player to join remotely via same local network.

Host: Runs game and listens for P2 input on UDP port 9999
Client: Runs on second machine, sends its joystick/keyboard input to host

Usage:
  Host (main game): automatically starts server, shows IP in HUD
  Client (remote): python3 remote_client.py --host <host_ip>

Protocol:
  Client -> Host: JSON UDP packet: {"dir": "UP"/"DOWN"/etc or None, "shoot": bool, "player_id":2, "timestamp":float}
  Host -> Client: Optional ack, or could send game state (not needed for controller-only remote join)

For full remote view, client would need game state sync, but for now we implement
remote controller mode: P2 on remote machine controls tank on host screen via network.
Second user can see host screen via screen sharing, TV, or same room - simple LAN party.

Extended: Could also implement full state sync where client runs its own game and receives state
from host. For now, we do input-only forwarding for second player joining remotely.

Added: Auto-discovery via broadcast on port 9998 for easier join without IP.
Added: Comprehensive debug logging for Lida remote control issue (detailed logs in debug.db)
"""

import socket
import json
import threading
import time
import os

DEFAULT_PORT = 9999
DEFAULT_BROADCAST_PORT = 9998

def get_all_local_ips():
    """Get all local IPv4 addresses for display, for Lida join diagnostics"""
    ips = []
    try:
        # Try via netifaces-like via socket gethostbyname_ex
        import socket as _sock
        hostname = _sock.gethostname()
        try:
            _, _, ip_list = _sock.gethostbyname_ex(hostname)
            for ip in ip_list:
                if not ip.startswith("127.") and "." in ip:
                    if ip not in ips:
                        ips.append(ip)
        except:
            pass
        # Primary via 8.8.8.8 trick
        try:
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip not in ips:
                ips.insert(0, ip)
        except:
            pass
        # Parse ifconfig for en0-en9
        try:
            import subprocess
            for iface in ["en0", "en1", "en2", "en3", "wlan0", "eth0"]:
                try:
                    result = subprocess.check_output(["ifconfig", iface], text=True, stderr=subprocess.DEVNULL, timeout=1)
                    for line in result.split("\n"):
                        line=line.strip()
                        if line.startswith("inet ") and "127.0.0.1" not in line:
                            parts=line.split()
                            # second token is ip
                            ip = parts[1] if len(parts)>1 else None
                            if ip and "." in ip and ip not in ips and not ip.startswith("169.254"):
                                ips.append(ip)
                except:
                    continue
        except:
            pass
    except:
        pass
    if not ips:
        ips = ["127.0.0.1"]
    return ips

def get_local_ip():
    ips = get_all_local_ips()
    # Prefer 192.168.x or 10.x over others
    for ip in ips:
        if ip.startswith("192.168.") or ip.startswith("10."):
            return ip
    return ips[0] if ips else "127.0.0.1"

def get_ip_subnet(ip):
    """Return /24 subnet string e.g. 192.168.0.* -> 192.168.0."""
    try:
        parts = ip.split(".")
        if len(parts)==4:
            return ".".join(parts[:3]) + "."
    except:
        pass
    return None

class NetworkHost:
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.running = False
        self.thread = None
        self.discovery_thread = None
        self.sock = None
        self.discovery_sock = None
        self.remote_p2_input = {"dir": None, "shoot": False, "timestamp": 0}
        self.last_client_addr = None
        self.client_connected = False
        self.client_last_seen = 0
        self.lock = threading.Lock()

    def start(self):
        if self.running:
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.port))
            self.sock.settimeout(0.5)
            try:
                self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.discovery_sock.bind(("0.0.0.0", DEFAULT_BROADCAST_PORT))
                self.discovery_sock.settimeout(0.5)
            except Exception as e:
                print(f"[Network] Discovery socket failed: {e} (non-critical)")
                self.discovery_sock = None
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            if self.discovery_sock:
                self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
                self.discovery_thread.start()
            ip = get_local_ip()
            all_ips = get_all_local_ips()
            print(f"[Network] Host listening on {ip}:{self.port} for remote P2 (all interfaces 0.0.0.0:{self.port})")
            if len(all_ips)>1:
                print(f"[Network] All local IPs: {', '.join(all_ips)}")
                for aip in all_ips:
                    print(f"  -> python3 remote_client.py --host {aip}")
            else:
                print(f"[Network] Remote player can join with: python3 remote_client.py --host {ip}")
            print(f"[Network] Or auto-discover: python3 remote_client.py (no --host)")
            print(f"[Network] If Lida gets 'No route to host', check:")
            print(f"  - Both on same WiFi (same SSID), not guest network with AP isolation")
            print(f"  - macOS Firewall: System Settings -> Network -> Firewall -> allow Python")
            print(f"  - Try ping from Lida: ping {ip}")
            print(f"  - Host IP may change (DHCP), current: {ip}, all: {all_ips}")
            return ip
        except Exception as e:
            print(f"[Network] Failed to start host: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
            return None

    def _discovery_loop(self):
        while self.running:
            try:
                if not self.discovery_sock:
                    time.sleep(0.5)
                    continue
                data, addr = self.discovery_sock.recvfrom(1024)
                try:
                    msg = json.loads(data.decode('utf-8', errors='replace'))
                    if msg.get("type") == "discovery" and msg.get("player_id") == 2:
                        ip = get_local_ip()
                        reply = {
                            "type": "host_info",
                            "ip": ip,
                            "port": self.port,
                            "game": "Tank93",
                            "players": 1,
                            "timestamp": time.time()
                        }
                        self.discovery_sock.sendto(json.dumps(reply).encode('utf-8'), addr)
                        print(f"[Network] Discovery request from {addr}, replied with {ip}:{self.port}")
                        try:
                            from .logger_integration import safe_log_event
                            safe_log_event("NETWORK", f"Discovery request from {addr} replied {ip}:{self.port}", level="INFO")
                        except:
                            pass
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"[Network] Discovery handling error: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Network] Discovery listen error: {e}")
                time.sleep(0.1)

    def _listen_loop(self):
        try:
            from .logger_integration import safe_log_gameplay, safe_log_event
            HAS_DEBUG = True
        except:
            HAS_DEBUG = False
            def safe_log_gameplay(*a, **kw): pass
            def safe_log_event(*a, **kw): pass
        packet_count = 0
        # For Lida debug: track last time we saw packet from .131
        last_lida_log = 0
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                packet_count += 1
                # Lida specific debug: log any packet from 192.168.0.131 even if not JSON, to diagnose No route vs no send
                is_lida = '192.168.0.131' in str(addr) or str(addr).startswith("('192.168.0.13")
                if is_lida and time.time() - last_lida_log > 1.0:
                    # Log raw bytes length for diagnosis (discovery vs input)
                    try:
                        preview = data[:200].decode('utf-8', errors='replace')
                    except:
                        preview = repr(data[:100])
                    print(f"[Network] Packet from Lida {addr} len={len(data)} preview={preview[:120]}")
                    last_lida_log = time.time()
                try:
                    # Robust decode: ignore stray binary packets (e.g., 0xd0 byte crash reported)
                    text = data.decode('utf-8', errors='replace')
                    msg = json.loads(text)
                    if isinstance(msg, dict) and "player_id" in msg:
                        if msg.get("type") == "discovery":
                            ip = get_local_ip()
                            reply = {
                                "type": "host_info",
                                "ip": ip,
                                "port": self.port,
                                "game": "Tank93",
                                "timestamp": time.time()
                            }
                            self.sock.sendto(json.dumps(reply).encode('utf-8'), addr)
                            # Reduce spam: only print discovery occasionally, not every packet (Lida case floods)
                            if packet_count % 20 == 1 or is_lida:
                                print(f"[Network] Discovery via main port from {addr}, replied ({packet_count} pkts)")
                            if HAS_DEBUG:
                                safe_log_event("NETWORK", f"Discovery via main port from {addr}", level="INFO")
                            continue
                        with self.lock:
                            if msg.get("player_id") == 2:
                                is_new = not self.client_connected
                                self.remote_p2_input = {
                                    "dir": msg.get("dir"),
                                    "shoot": bool(msg.get("shoot", False)),
                                    "timestamp": time.time()
                                }
                                self.last_client_addr = addr
                                was_connected = self.client_connected
                                self.client_connected = True
                                self.client_last_seen = time.time()
                                if not was_connected:
                                    print(f"[Network] Remote P2 (Lida) connected from {addr}!")
                                if HAS_DEBUG:
                                    if is_new or not was_connected:
                                        safe_log_gameplay("NETWORK_LIDA_CONNECTED", data={"addr": str(addr), "packet_count": packet_count, "dir": msg.get("dir"), "shoot": msg.get("shoot")})
                                        safe_log_event("NETWORK", f"Lida CONNECTED from {addr} dir={msg.get('dir')} shoot={msg.get('shoot')} pkt={packet_count}", level="INFO", extra={"addr": str(addr)}, with_stack=False)
                                    elif packet_count % 60 == 0:
                                        safe_log_gameplay("NETWORK_LIDA_INPUT", data={"addr": str(addr), "dir": msg.get("dir"), "shoot": msg.get("shoot"), "packet_count": packet_count})
                        try:
                            ack = json.dumps({"status": "ok", "received": msg.get("dir")}).encode()
                            self.sock.sendto(ack, addr)
                        except:
                            pass
                except json.JSONDecodeError:
                    # Ignore stray non-JSON packets (e.g., from 192.168.0.140 or mDNS) - don't spam WARN
                    # Previously logged as WARN causing Lida confusion: JSON decode error from ('192.168.0.140', 9999)
                    # Now silent unless debug verbose
                    continue
            except socket.timeout:
                with self.lock:
                    if self.client_connected and time.time() - self.client_last_seen > 10:
                        print("[Network] Remote P2 disconnected (timeout)")
                        if HAS_DEBUG:
                            safe_log_gameplay("NETWORK_LIDA_DISCONNECT", data={"last_addr": str(self.last_client_addr), "packet_count": packet_count, "reason": "timeout 10s"})
                            safe_log_event("NETWORK", f"Lida disconnected timeout after {packet_count} packets", level="WARN")
                        self.client_connected = False
                continue
            except Exception as e:
                if self.running:
                    print(f"[Network] Listen error: {e}")
                    if HAS_DEBUG:
                        safe_log_event("NETWORK", f"Listen error: {e}", level="ERROR", with_stack=True)
                time.sleep(0.1)

    def get_remote_p2_input(self):
        with self.lock:
            if time.time() - self.remote_p2_input.get("timestamp", 0) > 5.0:
                return {"dir": None, "shoot": False, "timestamp": self.remote_p2_input.get("timestamp", 0)}
            return dict(self.remote_p2_input)

    def is_client_connected(self):
        with self.lock:
            return self.client_connected and (time.time() - self.client_last_seen < 10)

    def get_last_seen(self):
        with self.lock:
            return self.client_last_seen

    def get_client_addr(self):
        with self.lock:
            return self.last_client_addr

    def disconnect_client(self):
        with self.lock:
            was_connected = self.client_connected
            self.client_connected = False
            self.client_last_seen = 0
            self.remote_p2_input = {"dir": None, "shoot": False, "timestamp": 0}
            self.last_client_addr = None
        if was_connected:
            print("[Network] Remote P2 (Lida) manually disconnected by host")
            try:
                from .logger_integration import safe_log_gameplay, safe_log_event
                safe_log_gameplay("NETWORK_LIDA_KICK", data={"reason": "manual disconnect by host"})
                safe_log_event("NETWORK", "Lida manually disconnected by host", level="WARN")
            except:
                pass
        return was_connected

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        if self.discovery_sock:
            try:
                self.discovery_sock.close()
            except:
                pass
        if self.thread:
            try:
                self.thread.join(timeout=1)
            except:
                pass
        if self.discovery_thread:
            try:
                self.discovery_thread.join(timeout=1)
            except:
                pass

class NetworkClient:
    def __init__(self, host_ip, port=DEFAULT_PORT):
        self.host_ip = host_ip
        self.port = port
        self.sock = None
        self.running = False

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.settimeout(1.0)
            self.running = True
            print(f"[Network] Client will send P2 input to {self.host_ip}:{self.port}")
            return True
        except Exception as e:
            print(f"[Network] Client failed to start: {e}")
            return False

    def send_input(self, direction, shoot):
        if not self.running or not self.sock:
            return False
        try:
            msg = {
                "player_id": 2,
                "dir": direction,
                "shoot": bool(shoot),
                "timestamp": time.time()
            }
            data = json.dumps(msg).encode('utf-8')
            # Use try to detect No route, but don't crash
            try:
                self.sock.sendto(data, (self.host_ip, self.port))
                return True
            except OSError as oe:
                # Errno 65 No route to host - common when host IP changed or AP isolation
                # Return False but don't spam every frame, caller handles counting
                # For Lida case: 192.168.0.131 -> 192.168.0.194 No route
                if "65" in str(oe) or "No route" in str(oe) or "Unreachable" in str(oe):
                    # Only print first few times to avoid spam, but still return False
                    if not hasattr(self, '_no_route_count'):
                        self._no_route_count = 0
                    self._no_route_count += 1
                    if self._no_route_count <= 3 or self._no_route_count % 60 == 0:
                        print(f"[Network] Send failed (No route to {self.host_ip}): {oe} (attempt {self._no_route_count})")
                        if self._no_route_count == 3:
                            print(f"  -> Lida checklist: same WiFi? firewall? host IP changed? Try discovery")
                return False
        except Exception as e:
            print(f"[Network] Send failed: {e}")
            return False

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass

def discover_hosts(timeout=3.0, verbose=True):
    """Broadcast discovery + subnet scan fallback for when broadcast blocked (Lida No route case)"""
    hosts = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        msg = json.dumps({"type": "discovery", "player_id": 2, "timestamp": time.time()}).encode('utf-8')
        # Broadcast list - try all common subnets
        bcasts = ['<broadcast>', '255.255.255.255', '192.168.0.255', '192.168.1.255', '10.0.0.255', '172.20.10.15']
        # Also add subnet bcast based on own IP
        my_ip = get_local_ip()
        subnet = get_ip_subnet(my_ip)
        if subnet:
            bcasts.append(subnet + "255")
        for bc in set(bcasts):
            try:
                sock.sendto(msg, (bc, DEFAULT_BROADCAST_PORT))
                sock.sendto(msg, (bc, DEFAULT_PORT))
            except:
                pass
        if verbose:
            print(f"[Discovery] Broadcasting for hosts on ports {DEFAULT_PORT} and {DEFAULT_BROADCAST_PORT}... from {my_ip}")
        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                try:
                    reply = json.loads(data.decode('utf-8', errors='replace'))
                    if reply.get("type") == "host_info":
                        ip = reply.get("ip") or addr[0]
                        port = reply.get("port", DEFAULT_PORT)
                        # deduplicate
                        if (ip, port) not in [(h[0], h[1]) for h in hosts]:
                            hosts.append((ip, port, addr))
                            if verbose:
                                print(f"[Discovery] Found host at {ip}:{port} from {addr} reply={reply}")
                except:
                    continue
            except socket.timeout:
                break
            except Exception:
                continue
        sock.close()
    except Exception as e:
        print(f"[Discovery] Broadcast failed: {e}")

    # If broadcast found nothing, try subnet scan (fixes No route when broadcast blocked but unicast works)
    if not hosts:
        if verbose:
            print(f"[Discovery] Broadcast found nothing, trying subnet scan fallback for Lida...")
        my_ip = get_local_ip()
        subnet = get_ip_subnet(my_ip)
        if subnet:
            hosts = scan_subnet_for_hosts(subnet, timeout_per_host=0.15, max_hosts=30, verbose=verbose)
    return hosts

def scan_subnet_for_hosts(subnet_prefix, timeout_per_host=0.2, max_hosts=40, verbose=True):
    """Scan subnet (e.g. 192.168.0.) for hosts listening on 9999 via unicast discovery.
    This bypasses broadcast blocking and AP isolation partial blocks. Used for Lida No route fix."""
    found = []
    my_ip = get_local_ip()
    # Build list of IPs to try: .1 to .254 excluding self
    # Prioritize .194 (previous host), .131 (client), and common .1, .100 etc
    candidates = []
    # First try likely host IPs from ARP table
    try:
        import subprocess
        arp_ips = []
        try:
            out = subprocess.check_output(["arp", "-a"], text=True, timeout=2, stderr=subprocess.DEVNULL)
            # parse lines like: ? (192.168.0.194) at ...
            import re
            for m in re.finditer(r"\((\d+\.\d+\.\d+\.\d+)\)", out):
                ip = m.group(1)
                if ip.startswith(subnet_prefix) and ip != my_ip:
                    arp_ips.append(ip)
        except:
            pass
        # Prioritize ARP ips first
        for ip in arp_ips:
            if ip not in candidates:
                candidates.append(ip)
    except:
        pass
    # Common router + typical host range near client
    try:
        base = int(my_ip.split(".")[-1])
        # check nearby 10 around client
        for offset in range(-10, 11):
            ip_num = base + offset
            if 1 <= ip_num <= 254:
                ip = f"{subnet_prefix}{ip_num}"
                if ip != my_ip and ip not in candidates:
                    candidates.append(ip)
    except:
        pass
    # Then fill rest 1-254 but limited to max_hosts
    for i in range(1, 255):
        ip = f"{subnet_prefix}{i}"
        if ip == my_ip or ip in candidates:
            continue
        if len(candidates) >= max_hosts:
            break
        candidates.append(ip)

    if verbose:
        print(f"[Discovery] Subnet scan {subnet_prefix}0/24 (my IP {my_ip}), checking {len(candidates)} hosts via unicast discovery...")

    # Use thread pool for fast scan
    import threading
    lock = threading.Lock()

    def try_host(target_ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(timeout_per_host)
            msg = json.dumps({"type": "discovery", "player_id": 2, "timestamp": time.time()}).encode()
            s.sendto(msg, (target_ip, DEFAULT_PORT))
            s.sendto(msg, (target_ip, DEFAULT_BROADCAST_PORT))
            try:
                data, addr = s.recvfrom(1024)
                reply = json.loads(data.decode('utf-8', errors='replace'))
                if reply.get("type") == "host_info":
                    with lock:
                        ip = reply.get("ip") or addr[0]
                        port = reply.get("port", DEFAULT_PORT)
                        if (ip, port) not in [(h[0], h[1]) for h in found]:
                            found.append((ip, port, addr))
                            if verbose:
                                print(f"[Discovery] Subnet scan FOUND host at {ip}:{port} (via {target_ip}) from {addr}")
            except socket.timeout:
                pass
            except:
                pass
            s.close()
        except:
            pass

    threads = []
    for t_ip in candidates[:max_hosts]:
        th = threading.Thread(target=try_host, args=(t_ip,), daemon=True)
        th.start()
        threads.append(th)
        # Small stagger to avoid flood
        time.sleep(0.005)

    for th in threads:
        th.join(timeout=1.0)

    return found
