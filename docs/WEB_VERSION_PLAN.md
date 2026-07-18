# Tank93 Web Version Plan

## Goal
Make Tank93 runnable in web browser (https://halcyon0811.github.io/tank93 or itch.io) while keeping desktop version fully functional.

## Current Desktop Architecture
- **Entry:** `main.py` -> `Game().run()` (sync while True loop)
- **Display:** 960x720 windowed, 1920x1080 fullscreen via `FULLSCREEN | SCALED` or `(0,0)`
- **Input:** Keyboard (WASD, Arrows, SPACE), Joy-Con via `pygame.joystick`, custom mapping via `controller_mapping.json`, plus LAN remote P2 via UDP `game/network.py`
- **Networking:** UDP socket host on `:9999` in thread, projector HTTP server on `:8080` in thread
- **Sound:** `pygame.mixer` with 53 sounds, generated via numpy (punchy, realistic tank, brick)
- **File IO:** Writes `crash.log`, `debug.db` (SQLite WAL), reads `assets/General-Sprites.png` and sounds
- **Threading:** NetworkHost and Projector use `threading.Thread(daemon=True)`

## Web Challenges
- **Pygame on Web:** Browser doesn't have native pygame, needs WebAssembly via Emscripten / Pyodide. Tool: **Pygbag** (https://github.com/pygame-web/pygbag) - packages pygame game to WASM that runs in browser.
- **Sockets:** Browser JS cannot do raw UDP sockets (security). `game/network.py` UDP host will fail in web. Need to disable or replace with WebSockets/WebRTC (future). For v1 web, disable LAN host/client, keep local 1P/2P via keyboard/gamepad API.
- **Threading:** WASM is single-threaded, `threading.Thread` may not work well. Pygbag has limited threading support, but we should disable network/projector threads in web build and make them no-op.
- **File System:** Emscripten MEMFS is in-memory, not persistent. Writes to `crash.log`, `debug.db` will be lost on refresh. Should make optional or in-memory in web, or disable debug logger file writes in web.
- **Joystick:** Browser Gamepad API maps to `pygame.joystick` via Pygbag, but Joy-Con may not be supported. Keyboard should be primary for web, with gamepad as bonus.
- **PIL / numpy:** Pygbag includes numpy via Pyodide, but PIL may be missing. We already have fallback `try: from PIL import Image except: Image=None`. Same for sound generation - if numpy missing, fallback to authentic OGGs.
- **Async Loop:** Pygbag prefers `asyncio` loop. Current `while True: clock.tick(60)` is sync. Pygbag can patch it, but better to provide `async def` wrapper.
- **Audio:** `pygame.mixer` works in web via WebAudio, but may need user interaction to start audio (browser autoplay policy). Pygbag handles this with click to start.

## Solution: Pygbag

### What is Pygbag?
- Tool by pygame-web team: `pip install pygbag`
- Takes your `main.py` and builds web version: `pygbag main.py` -> serves on `http://localhost:8000`
- Output in `build/web/` - static files that can be hosted on GitHub Pages, itch.io, Netlify
- Handles pygame -> WebAssembly via Emscripten, includes async loop patching

### Installation
```bash
pip install pygbag
# Test locally:
pygbag --port 8000 main.py
# Open http://localhost:8000
```

### Build Output
```
build/web/
  - index.html (Pygbag template)
  - main.py (your game)
  - game/ (all modules)
  - ... assets
  - pygbag prelude
```

### Deployment Options
1. **GitHub Pages:**
   - Build: `pygbag --build main.py` -> creates `build/web`
   - Push `build/web` to `gh-pages` branch: `git subtree push --prefix build/web origin gh-pages`
   - Or copy to `docs/` folder if repo uses docs for Pages
   - URL: https://halcyon0811.github.io/tank93/

2. **itch.io:**
   - Build zip: `pygbag --archive main.py` or zip `build/web`
   - Upload to itch.io as HTML5 game, set viewport 960x720, enable fullscreen button

3. **Netlify/Vercel:**
   - Drag & drop `build/web` folder

4. **Local Network Projector (existing feature):**
   - Web version already serves on `:8080` for projector, but new web version will also be playable directly in projector's browser via `:8000` (Pygbag server) - no need for separate projector server in web build

## Required Code Changes for Web Compatibility

### 1. Create `web_main.py` (web entry point, no auto-venv, no network/projector threads)
```python
import pygame, sys, asyncio, os
# Disable problematic features in web
os.environ['SDL_IME_SHOWUI'] = '0'
sys.path.insert(0, '.')

# Detect if running in Emscripten (web)
IS_WEB = sys.platform == "emscripten"

from game.game import Game

async def main():
    game = Game(is_web=IS_WEB)  # Pass flag to disable network/projector, file writes
    await game.run_async()  # Need async version or keep sync and let pygbag patch

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Modify `game/game.py` to support `is_web` flag and async loop
- In `__init__(self, is_web=False)`: store flag, if is_web, don't start NetworkHost and Projector server (skip thread creation)
- In `run()`: add `async def run_async()` that does same loop but with `await asyncio.sleep(0)` each frame for Pygbag
- Keep existing `run()` for desktop, add `run_async()` for web that calls same logic
- Alternatively, Pygbag can run sync loop if we don't use async, but better to provide async version

Simplest: Keep existing `run()` but make it async-compatible by adding `if is_web: await asyncio.sleep(0)` via check.

Actually Pygbag docs say you can keep sync loop and it will work, but you should add `await asyncio.sleep(0)` or use `asyncio.run` wrapper. We'll implement both `run()` and `run_async()`.

### 3. Disable file writes in web
- In `game/debug_logger.py`, if `is_web`, use in-memory or no-op
- In `main.py`, don't write `crash.log` to disk in web, just print
- In `sound_manager.py`, don't try to save generated sounds to disk in web

### 4. Disable socket/threads in web
- In `game.py` __init__, if `is_web`, set `self.network_host = None` and `self.projector_ip = None` and skip starting threads
- This avoids `OSError: Address already in use` and threading issues in WASM

### 5. Handle audio autoplay
- Pygbag shows "Click to start" overlay to satisfy browser autoplay policy
- Ensure `pygame.mixer.init()` is called after user interaction? Pygbag handles, but we should keep current init

### 6. Controls for web
- Keyboard: WASD+SPACE (P1), Arrows+Enter (P2) - works in browser
- Gamepad: Browser Gamepad API maps to pygame.joystick via Pygbag - should work for Xbox/PS/Joy-Con via Bluetooth to browser (less reliable than native, but okay)
- No remote LAN join in web v1 (since UDP not possible), but we can keep local 2P co-op
- For future, could implement WebSocket-based multiplayer for web (replace UDP with WebSocket)

### 7. Performance
- Canvas scaling already implemented for fullscreen zoom - good for web where canvas is scaled to browser window
- Sound generation via numpy is heavy at startup (generates 53 sounds) - in web, may cause slow startup. We can keep authentic OGGs as fallback and skip generating realistic sounds in web if numpy not available (already have fallback)
- Reduce startup time: In web, maybe skip generating punchy/realistic and just use authentic OGGs (faster)

### 8. Build Scripts
Create `build_web.sh`:
```bash
#!/bin/bash
pip install pygbag
pygbag --build --PYGAME lane main.py --title "Tank93 - Battle City Tribute - 35 NES Maps"
# Output in build/web
echo "Build done, serve with: pygbag --port 8000 main.py"
```

Create `web_deploy.sh` for GitHub Pages.

## File Structure for Web Version
```
tank93/
  main.py (desktop, with auto-venv, network, projector)
  web_main.py (web entry, no auto-venv, is_web=True, async)
  game/
    game.py (add is_web flag, run_async, disable network/projector threads if web)
    projector.py (disable in web, or make no-op if is_web)
    network.py (disable in web)
    debug_logger.py (disable file writes if web)
    ...
  build/web/ (generated by pygbag, gitignored, for deployment)
  docs/WEB_VERSION_PLAN.md (this file)
  web/
    index.html (custom template for itch.io, optional)
```

## Testing Plan
1. Install pygbag: `pip install pygbag`
2. Test desktop still works: `python3 main.py`
3. Test web locally: `pygbag --port 8000 main.py` -> open http://localhost:8000, test keyboard, 1P/2P, shooting sounds, tank facing, boss, items
4. Check browser console for errors (missing assets, CORS, etc.)
5. Test on different browsers: Chrome, Firefox, Safari
6. Test on mobile browser (touch controls not implemented, but keyboard may not work - future: add touch)
7. If works, build for deploy: `pygbag --build main.py`
8. Deploy to GitHub Pages: `git subtree push --prefix build/web origin gh-pages`
9. Update README with web link

## Future Enhancements for Web
- Touch controls for mobile: Add on-screen D-pad and shoot buttons when `is_web` and `is_touch`
- WebSocket multiplayer: Replace UDP with WebSocket for remote P2 in web version
- PWA: Make it installable as PWA
- Itch.io: Upload with fullscreen button, mobile support

## Risks / Mitigations
- **Numpy not available in web:** We have fallback to authentic OGGs, so sound still works (just less punchy). Mitigation: Keep authentic OGGs as primary in web, skip generating realistic.
- **Threading not supported:** Disable network/projector threads in web via `is_web` flag.
- **File size:** 35 maps + sounds + sprites = maybe 5-10MB, okay for web, but we should ensure assets are included in build. Pygbag bundles all files in `game/assets/`.
- **Performance:** Generating 53 sounds via numpy at startup may be slow in WASM (10-20 sec). Mitigation: In web, skip generating better sounds and just use authentic OGGs (fast).
- **Audio autoplay:** Browser requires user click to start audio. Pygbag shows overlay, okay.

## Implementation Steps (in order)

1. **Create plan doc** (this file) - DONE
2. **Create `web_main.py`** - simple entry that sets `is_web` detection and calls `Game(is_web=True).run_async()`
3. **Modify `game/game.py`:**
   - Add `is_web` param to `__init__`, store
   - If is_web, skip NetworkHost and Projector start
   - Add `async def run_async()` that does same as `run()` but with `await asyncio.sleep(0)` each frame
   - Also keep original `run()` for desktop
   - In `draw()`, projector update should be no-op if is_web (since we are already in browser, no need to stream to :8080)
4. **Modify `game/debug_logger.py`:** If is_web, disable file writes or use memory
5. **Modify `main.py`:** Detect if running via pygbag (sys.platform == "emscripten") and handle accordingly, or keep separate web_main.py
6. **Create build scripts:** `build_web.sh`, `package.json` or `Makefile` with pygbag commands
7. **Test locally:** `pygbag main.py` and `pygbag web_main.py`
8. **Fix any issues found in testing (missing assets, etc.)**
9. **Deploy:** Build and push to gh-pages, update README with link

Let's proceed.
