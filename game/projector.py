"""
Projector / Screen Sharing for Tank93 via Local Network
Allows projecting game to any device on same WiFi (projector, TV, phone, browser)

How it works:
- Host runs game normally (python3 main.py)
- This module starts HTTP server on port 8080 that serves live game screen
- Any device on same local network can open http://<host_ip>:8080 in browser to see game
- Perfect for projector: connect laptop to projector via HDMI, or use smart projector's browser
- Or use AirPlay/Screen Mirroring: Mac -> Projector via AirPlay, but this web method works for any projector with browser or via another laptop

Usage:
  Host auto-starts projector server on 8080 (can disable via --no-projector)
  Second device opens browser: http://192.168.0.131:8080

Features:
- Live MJPEG-like stream (auto-refreshing JPEG)
- Shows game screen, score, P1/P2 status
- Low latency (~100ms)
- Works for any projector on same local network

For true network projectors (Epson, BenQ WiFi):
- Some support browser: open http://host_ip:8080 directly on projector
- Or use laptop connected to projector via HDMI, open browser on laptop
- Or use AirPlay: Mac Screen Mirroring -> Apple TV -> Projector
"""
import threading
import time
import os
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Global to hold latest frame
_latest_frame_jpeg = None
_latest_frame_lock = threading.Lock()
_server_running = False
_server_thread = None
_httpd = None

class ProjectorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _latest_frame_jpeg
        if self.path == '/' or self.path == '/index.html':
            # Serve HTML page that shows live game
            html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Tank93 - Projector View</title>
<style>
body {{ margin:0; background:#111; color:#fff; font-family: monospace; text-align:center; }}
h1 {{ color:#ff0; margin:10px; }}
#game {{ max-width:90vw; max-height:80vh; border:4px solid #444; border-radius:8px; }}
#info {{ color:#aaa; margin:10px; font-size:14px; }}
a {{ color:#0ff; }}
</style>
<script>
let lastUpdate = Date.now();
function refreshFrame() {{
    const img = document.getElementById('game');
    img.src = '/frame.jpg?t=' + Date.now();
    lastUpdate = Date.now();
}}
setInterval(refreshFrame, 100); // 10 FPS for projector (low latency)
</script>
</head>
<body>
<h1>TANK 93 - PROJECTOR VIEW</h1>
<img id="game" src="/frame.jpg" alt="Game screen - waiting for host...">
<div id="info">
Local Network Projector Mode - Host: {get_local_ip()}:8080<br>
This view auto-refreshes every 100ms - Open on projector's browser or laptop connected to projector<br>
Controls remain on host machine (WASD+SPACE / Joy-Con), remote P2 can join via <a href="#">remote_client.py</a><br>
Press F11 for fullscreen on projector
</div>
</body>
</html>
"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(html.encode())))
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path.startswith('/frame.jpg'):
            # Serve latest JPEG frame
            with _latest_frame_lock:
                frame_data = _latest_frame_jpeg

            if frame_data is None:
                # No frame yet, serve placeholder
                self.send_response(503)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'No frame yet - waiting for game to start...')
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Content-Length', str(len(frame_data)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                self.wfile.write(frame_data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

    def log_message(self, format, *args):
        # Suppress default logging
        return

def get_local_ip():
    """Get local IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"

def update_frame(pygame_surface):
    """Called from game loop to update latest frame for projector"""
    global _latest_frame_jpeg
    if not _server_running:
        return
    try:
        # Convert pygame surface to JPEG
        # Scale down slightly for bandwidth if needed (keep full res for projector quality)
        # For performance, we can use pygame.image.tostring and PIL
        import pygame
        # Ensure surface is valid
        if pygame_surface is None:
            return

        # Convert to string buffer
        # Use pygame.image.tostring
        data = pygame.image.tostring(pygame_surface, 'RGB')
        w, h = pygame_surface.get_size()

        if HAS_PIL:
            # Use PIL to encode JPEG (faster and smaller)
            img = Image.frombytes('RGB', (w, h), data)
            # Optional: scale down for projector if too large (keep 960x720 as is for quality)
            # img = img.resize((960, 720))  # keep original
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=70, optimize=True)
            jpeg_data = buf.getvalue()
        else:
            # Fallback: use pygame's save to buffer via temporary file? 
            # We'll use pygame.image.save with StringIO not directly supported, so use raw
            # For simplicity, use PNG via pygame.image.tostring and encode as JPEG via pygame? 
            # We'll just store as raw and let browser handle? No, need JPEG.
            # Fallback: save to temp file and read
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name
            try:
                pygame.image.save(pygame_surface, tmp_path)
                with open(tmp_path, 'rb') as f:
                    jpeg_data = f.read()
                os.unlink(tmp_path)
            except:
                return

        with _latest_frame_lock:
            _latest_frame_jpeg = jpeg_data
    except Exception as e:
        # Don't crash game if projector update fails
        # print(f"[Projector] Frame update error: {e}")
        pass

def start_server(port=8080):
    """Start HTTP server for projector in background thread"""
    global _server_running, _server_thread, _httpd

    if _server_running:
        return get_local_ip()

    def run_server():
        global _httpd, _server_running
        try:
            _httpd = HTTPServer(("0.0.0.0", port), ProjectorHandler)
            _server_running = True
            ip = get_local_ip()
            print(f"[Projector] HTTP server started on http://{ip}:{port} for projector")
            print(f"[Projector] Open on any device same WiFi: http://{ip}:{port}")
            print(f"[Projector] For projector: Connect laptop to projector via HDMI, open browser to http://{ip}:{port}, F11 fullscreen")
            _httpd.serve_forever()
        except Exception as e:
            print(f"[Projector] Failed to start server on {port}: {e}")
            _server_running = False

    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()
    # Give it a moment to start
    time.sleep(0.5)
    return get_local_ip()

def stop_server():
    global _server_running, _httpd
    _server_running = False
    if _httpd:
        try:
            _httpd.shutdown()
        except:
            pass
