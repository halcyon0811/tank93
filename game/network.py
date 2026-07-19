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
"""
import socket
import json
import threading
import time
import os

DEFAULT_PORT = 9999
DEFAULT_BROADCAST_PORT = 9998

def get_local_ip():
    """Get local IP for display, works on Mac/Linux/Win"""
    try:
        # Try to get IP that would be used to connect to internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            # Fallback: gethostname
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                # Try en0 on Mac
                import subprocess
                try:
                    result = subprocess.check_output(["ifconfig", "en0"], text=True)
                    for line in result.split("\n"):
                        if "inet " in line and "127.0.0.1" not in line:
                            ip = line.split()[1]
                            break
                except:
                    pass
            return ip
        except:
            return "127.0.0.1"

class NetworkHost:
    """Host that receives remote P2 input"""
    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.running = False
        self.thread = None
        self.sock = None
        self.discovery_sock = None
        self.discovery_thread = None
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
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            # Also start discovery responder on broadcast port
            try:
                self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.discovery_sock.bind(("0.0.0.0", DEFAULT_BROADCAST_PORT))
                self.discovery_sock.settimeout(0.5)
                self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
                self.discovery_thread.start()
                print(f"[Network] Discovery responder listening on 0.0.0.0:{DEFAULT_BROADCAST_PORT}")
            except Exception as e:
                print(f"[Network] Discovery responder failed to start (optional): {e}")
            ip = get_local_ip()
            print(f"[Network] Host listening on {ip}:{self.port} for remote P2")
            print(f"[Network] Remote player can join with: python3 remote_client.py --host {ip}")
            print(f"[Network] Or auto-discover: python3 remote_client.py (no --host)")
            return ip
        except Exception as e:
            print(f"[Network] Failed to start host: {e}")
            import traceback
            traceback.print_exc()
            self.running = False
            return None

    def _discovery_loop(self):
        """Respond to broadcast discovery requests from clients on same WiFi"""
        while self.running:
            try:
                data, addr = self.discovery_sock.recvfrom(1024)
                try:
                    msg = json.loads(data.decode('utf-8'))
                    if msg.get("type") == "discovery" and msg.get("player_id") == 2:
                        # Reply with host info
                        ip = get_local_ip()
                        reply = {
                            "type": "host_info",
                            "ip": ip,
                            "port": self.port,
                            "game": "Tank93",
                            "players": 1,  # could add current players
                            "timestamp": time.time()
                        }
                        self.discovery_sock.sendto(json.dumps(reply).encode('utf-8'), addr)
                        print(f"[Network] Discovery request from {addr}, replied with {ip}:{self.port}")
                except json.JSONDecodeError:
                    # Ignore non-JSON
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
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                try:
                    msg = json.loads(data.decode('utf-8'))
                    # Validate
                    if isinstance(msg, dict) and "player_id" in msg:
                        # Also handle discovery via main port
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
                            print(f"[Network] Discovery via main port from {addr}, replied")
                            continue
                        with self.lock:
                            if msg.get("player_id") == 2:
                                self.remote_p2_input = {
                                    "dir": msg.get("dir"),
                                    "shoot": bool(msg.get("shoot", False)),
                                    "timestamp": time.time()
                                }
                                self.last_client_addr = addr
                                if not self.client_connected:
                                    print(f"[Network] Remote P2 connected from {addr}!")
                                self.client_connected = True
                                self.client_last_seen = time.time()
                        # Send ack
                        try:
                            ack = json.dumps({"status": "ok", "received": msg.get("dir")}).encode()
                            self.sock.sendto(ack, addr)
                        except:
                            pass
                except json.JSONDecodeError:
                    continue
            except socket.timeout:
                # Check if client timed out
                with self.lock:
                    if self.client_connected and time.time() - self.client_last_seen > 10:
                        print("[Network] Remote P2 disconnected (timeout)")
                        self.client_connected = False
                continue
            except Exception as e:
                if self.running:
                    print(f"[Network] Listen error: {e}")
                time.sleep(0.1)

    def get_remote_p2_input(self):
        """Get latest remote P2 input, with timeout"""
        with self.lock:
            # If no recent input (within 2 sec), treat as no input
            if time.time() - self.remote_p2_input.get("timestamp", 0) > 2.0:
                return {"dir": None, "shoot": False}
            return dict(self.remote_p2_input)

    def is_client_connected(self):
        with self.lock:
            return self.client_connected and (time.time() - self.client_last_seen < 5)

    def disconnect_client(self):
        """Force disconnect remote P2 (Lida) - for host to allow 1P restart"""
        with self.lock:
            was_connected = self.client_connected
            self.client_connected = False
            self.client_last_seen = 0
            self.remote_p2_input = {"dir": None, "shoot": False, "timestamp": 0}
            self.last_client_addr = None
        if was_connected:
            print("[Network] Remote P2 (Lida) manually disconnected by host")
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
    """Client that sends P2 input to host"""
    def __init__(self, host_ip, port=DEFAULT_PORT):
        self.host_ip = host_ip
        self.port = port
        self.sock = None
        self.running = False

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(1.0)
            self.running = True
            print(f"[Network] Client will send P2 input to {self.host_ip}:{self.port}")
            return True
        except Exception as e:
            print(f"[Network] Client failed to start: {e}")
            return False

    def send_input(self, direction, shoot):
        """Send P2 input to host"""
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
            self.sock.sendto(data, (self.host_ip, self.port))
            return True
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
