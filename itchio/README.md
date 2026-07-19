# Tank93 - itch.io Preparation

This folder contains builds ready for itch.io upload as HTML5 game.

## Builds

### 1) Pure JS Version (Recommended for itch.io) - `tank93-purejs-web.zip` (540KB)
- **No Python**, pure JavaScript Canvas, fastest loading
- Features: 35 original NES maps, tank facing fix, enemy stuck fix, monster base → boss (normal speed 1.8), random items to enemies on boss release, homing M + spread 8 + rapid R x3 PERM until death, freeze attackable, gradual enemies 20→106, real tank sounds from distant_tank_shots.mp3, brick hit hybrid, fullscreen zoomed (F11), LAN remote P2 (disabled in web, but local 2P co-op works)
- Controls: WASD+SPACE P1, ARROWS+ENTER P2, Gamepad via Browser Gamepad API, F11 fullscreen
- How to test locally: `cd web-pure && python3 -m http.server 8003` → http://localhost:8003/
- Upload to itch.io as HTML5, viewport 960x720, enable fullscreen button

### 2) Pygbag Version (Python WASM) - `tank93-pygbag-web.zip` (8.0M)
- **Python in browser** via WebAssembly (Pyodide + Emscripten), Pygame 2.6.1
- Same features as desktop Python version, but runs in browser
- Includes all 53 sounds (real tank cannon, brick hit hybrid), 35 maps, monster boss, etc.
- Larger (8M) due to Python runtime + assets in apk/tar.gz
- How to test locally: `pygbag --port 8000 web_main.py` → http://localhost:8000
- Upload to itch.io as HTML5, same as above

## How to Upload to itch.io

1. Go to https://itch.io/dashboard
2. Click **Create new project** or select existing Tank93
3. Set:
   - Title: **Tank93 - Battle City Tribute - 35 Original NES Maps**
   - Kind of project: **Game**
   - Classification: **Game**
   - Kind: **HTML**
4. Upload ZIP:
   - For **fastest loading, small size**: Upload `tank93-purejs-web.zip` (540KB)
   - For **full Python features**: Upload `tank93-pygbag-web.zip` (8M, includes Python runtime)
   - Or upload both as separate HTML5 games and let player choose
5. In itch.io embed options:
   - Check **This file will be played in the browser**
   - Viewport: `960 x 720` (or 1280x720 for HD)
   - Enable **Fullscreen button**
   - Enable **Mobile friendly** (for pure JS version, touch controls not yet implemented but will work with keyboard)
   - Check **Automatically start on page load** (optional)
6. Description (copy from README.md):
   - 35 original NES maps, 700 enemies, tank facing fixed, enemy stuck fix, monster base that releases boss when hit (boss slowed to normal speed 1.8, same as basic),
   - After boss out, randomly assigns items (homing, spread, rapid) to current enemies,
   - Items: homing missile (M-orange tracking), spread 8-way (purple), rapid 3x (pink) - PERM until death, kept across stages,
   - Freeze now attackable, gradual enemies (20→106, max 4→8, spawn 2.5s→0.8s),
   - Real tank sounds from freesound community distant tank shots (17.6s, 7 shots) for attack and brick hit hybrid,
   - Fullscreen zoomed (F11/Cmd+F), LAN remote P2 via same WiFi (python3 remote_client.py --host IP), projector http://host:8080 via browser,
   - Controls: P1 WASD+SPACE, P2 ARROWS+ENTER, Joy-Con L/R, Gamepad
7. Add tags: `battle-city`, `tank`, `nes`, `retro`, `arcade`, `35-maps`, `co-op`, `multiplayer`, `boss`, `powerups`
8. Save & Publish

## Local Testing Before Upload

```bash
# Pure JS version
cd web-pure
python3 -m http.server 8003
# Open http://localhost:8003/

# Pygbag version
pygbag --port 8000 web_main.py
# Open http://localhost:8000
# Click to start audio (browser autoplay policy)
```

## GitHub Pages Deployment (already done)

- Pygbag build pushed to `gh-pages` branch via:
  ```bash
  pygbag --build web_main.py
  git subtree push --prefix build/web origin gh-pages
  ```
- URL: https://halcyon0811.github.io/tank93/ (may need enabling in repo Settings > Pages > Source: gh-pages / root)
- Pure JS version could also be deployed to GitHub Pages via `web-pure/` folder if you set Pages source to `web-pure/` or copy to `docs/`

## Files in this folder

- `tank93-purejs-web.zip` - Pure JS, 540KB, 15 files, index.html at root, fastest loading, no Python, recommended for itch.io
- `tank93-pygbag-web.zip` - Python WASM, 8.0M, 4 files (index.html, favicon.png, apk, tar.gz), full Python runtime, same features as desktop
- `pygbag/` and `purejs/` folders - unpacked versions for inspection

## Which to choose for itch.io?

- **For itch.io front page, fastest load, mobile friendly:** Use **pure JS** (`tank93-purejs-web.zip`) - 540KB, loads in 1-2 sec
- **For full desktop parity with Python sounds and all features:** Use **pygbag** (`tank93-pygbag-web.zip`) - 8M, loads in 3-5 sec, includes Python runtime
- **Best:** Upload both as separate games or as one with pure JS as primary and Pygbag as alternative download

## Future

- Add touch controls for mobile web (on-screen D-pad + shoot)
- WebSocket multiplayer for web (replace UDP LAN)
- PWA support (installable)
- Leaderboard via itch.io API

Enjoy! Tank93 - 35 original NES maps - now playable in browser, no Python needed for pure JS version.
