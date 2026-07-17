# Tank 90 Enhanced - Battle City Tribute

A modernized Tank 1990 / Battle City clone built with Pygame. Designed as a **PC prototype** structured for easy porting to **Nintendo Switch** (via Godot/Unity + Nintendo SDK).

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Pygame](https://img.shields.io/badge/pygame-2.6-green)
![Platform](https://img.shields.io/badge/platform-PC%20%7C%20Switch%20Ready-orange)

## Features (Enhanced Edition)

Classic Battle City + modern twists:

- **1-2P Local Co-op** (Joy-Con ready): WASD + Arrows + Gamepad support
- **4 Enemy Types**: Basic (gray), Fast (blue), Power (red), Armor (4HP)
- **5 Handcrafted Stages** with increasing difficulty
- **Tile Types**: Brick (breakable), Steel (needs power gun), Water (blocked), Forest (hide), Ice (slippery)
- **7 Power-ups**: 
  - ⭐ Star = upgrade (speed + steel-breaking gun)
  - Helmet = 10s shield
  - Clock = freeze enemies 5s
  - Shovel = steel walls around base 15s
  - Tank = +1 life
  - Grenade = kill all on screen
  - Gun = power bullets
- **Modernized Pixel Art**: HD rendering while keeping retro feel
- **Juicy Effects**: Explosions, spawn effects, tracers, screen shake ready
- **Data-driven Levels**: 13x13 big-tile system like original NES

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Controls

| Player | Move | Shoot | Notes |
|--------|------|-------|-------|
| P1 | WASD | SPACE / LCTRL | Joystick 1: LS + A/B |
| P2 | Arrow Keys | ENTER / RCTRL | Joystick 2: LS + A/B |
| Global |  |  | P=Pause, M=Mute, ESC=Menu |

Nintendo Switch mapping (when ported):
- LS = Move, A = Shoot, B = Special
- SL/SR for 2P Joy-Con single

## Project Structure (Switch-Port Ready)

```
tank90/
├── main.py              # Entry point
├── game/
│   ├── settings.py      # All constants - single source of truth for porting
│   ├── tilemap.py       # 26x26 grid, 5 levels defined as 13x13 (like NES)
│   ├── game.py          # Main loop, states, spawner (easy to port to Godot/Unity)
│   ├── entities/
│   │   ├── tank.py      # Base tank (logic separated from rendering)
│   │   ├── player.py    # Player input + upgrade system
│   │   ├── enemy.py     # AI: wander + chase + align shooting
│   │   ├── bullet.py    # Bullet + Base/Eagle
│   │   ├── powerup.py   # Power-up definitions
│   │   └── particles.py # Particle system (to port as shader)
│   └── ui/
│       └── hud.py       # HUD + Menu (decoupled)
├── docs/
│   ├── NINTENDO_SWITCH.md # Full eShop publishing guide
│   └── PORTING.md       # How to move to Godot/Unity
└── requirements.txt
```

### Why Pygame first?

- Fast prototyping, validates gameplay loop
- Logic in `settings.py` + pure python classes = easy to translate to C#/GDScript
- Tilemap format (13x13 ints) is engine-agnostic - can be imported directly into Godot TileMap or Unity Tilemap

## Gameplay Rules

1. Protect the Eagle (base) - if hit, game over
2. Destroy `N` enemies to clear stage (20 + level*2)
3. Max 4 enemies on field, spawns at top (0,0), (12,0), (24,0)
4. Points: Basic 100, Fast 200, Power 300, Armor 400, Stage clear bonus

## Nintendo Switch Publishing Roadmap

**TL;DR**: Pygame cannot run directly on Switch. You need to port to an official Nintendo SDK-supported engine.

**Path A - Recommended Godot 4 (Our template ready)**:
1. Apply for Nintendo Developer Program at https://developer.nintendo.com (free, needs company/individual verification)
2. Get access to Switch SDK after NDA
3. Use our Godot template (see docs/) - tilemap + logic already structured for Godot
4. Use W4 Games Switch export or official Godot Switch port (requires Nintendo permission)
5. Follow Lot Check guidelines

**Path B - Unity (Easiest eShop approval)**:
1. Same Nintendo dev account
2. Unity + Nintendo Switch Build Support module (via Nintendo dev portal)
3. Port: tilemap -> Unity Tilemap, tanks -> MonoBehaviour, input -> InputSystem with Joy-Con
4. Optimize: 60fps, 1920x1080 docked / 1280x720 handheld

**See `docs/NINTENDO_SWITCH.md` for full checklist**, including:
- Age rating (ESRB, PEGI), store assets, pricing
- Technical requirements: loading times, error handling, save data
- How to keep 60fps on Switch (draw calls, batching)
- Testing with Dev Kit

## Next Steps to Enhance

- [ ] Add sound (retro 8-bit SFX via pygame.mixer)
- [ ] Level editor (export 13x13 JSON)
- [ ] VS mode + more powerups
- [ ] Save high scores + stage progress
- [ ] Godot 4 port folder (I've prepared structure in docs)

## License Note

This is a tribute/fan project inspired by Battle City (Namco 1985). Original sprites/game design belong to respective owners. For eShop publishing, you must:
- Use original art/music (not ripped from Battle City)
- Rename (e.g., "Tank 90: Steel Defense")
- Our assets here are original geometric shapes - safe for commercial use

Enjoy! 
For Switch port, run `cat docs/NINTENDO_SWITCH.md`

