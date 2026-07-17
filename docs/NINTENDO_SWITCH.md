# Nintendo Switch Publishing Guide for Tank 93

This document explains how to take this Pygame prototype and publish it to Nintendo eShop.

## 1. Reality Check

| Question | Answer |
|----------|--------|
| Can Pygame run on Switch? | **No** - Switch doesn't support Python runtime in eShop games. Need port. |
| What engines does Nintendo support? | Unity, Unreal, Godot (via approved port), Custom C++ with SDK |
| Do I need a dev kit? | Yes eventually, but you can prototype with PC + Nintendo docs |
| Cost to publish? | Free to become developer, but ~$500-1000 for dev kit + lot check + ratings |
| Timeline? | Dev account 2-4 weeks, Port 2-6 weeks, Lot Check 4-8 weeks |

## 2. Become a Nintendo Developer

1. Go to https://developer.nintendo.com
2. Apply as Individual or Company (company easier for approval)
3. You need: website, documented game project (this prototype is perfect), privacy policy
4. Wait for approval (1-4 weeks)
5. Once approved, you get:
   - Access to Nintendo SDK + docs (under NDA)
   - Unity/Unreal/Godot Switch export modules
   - Dev forum, lot check guidelines
   - eShop pricing, ratings info

## 3. Choose Your Port Engine

### Option A: Godot 4 (Recommended - Free, suits this game)

Why Godot fits Tank 93:
- Original Battle City was 2D tile-based, Godot TileMap is perfect
- Our 13x13 int tilemap can be imported 1:1
- Godot's GDScript is similar to Python -> easy port
- W4 Games offers official Switch console port (https://w4games.com)

Godot Port Steps:
```
# Structure we already prepared for Godot:
- game/settings.py  ->  Godot Autoload/Settings.gd
- TileMap LEVELS    ->  Godot TileSet + TileMap nodes
- Tank class        ->  CharacterBody2D + GDScript
- Bullet            ->  Area2D + raycast
- Input: use Input Map: "p1_up", "joy_0_a" for Joy-Con
```

Todo for Godot version:
1. Create new Godot 4.4 project
2. Create TileSet with 5 tiles (brick, steel, water, grass, ice) - use our draw functions as reference to create PNG sprites (24x24)
3. Import LEVELS array into .tscn files
4. Recreate Tank.gd with same logic: speed, bullet limit, star levels
5. Implement controls:
   - Joy-Con single: SL+SR as L/R? Actually use single Joy-Con sideways: stick = direction
   - Godot: Input.get_joy_axis(0, JOY_AXIS_LEFT_X)
6. 60fps: in Project Settings -> enable VSync, set 1080p docked / 720p handheld via Window settings
7. Build: Export -> Nintendo Switch (needs Nintendo's custom Godot fork, only available after dev approval)

### Option B: Unity (Easiest Approval)

Unity is Nintendo's most tested engine, lot check easiest.

Port steps:
- Create 2D URP project
- Unity Tilemap: create rule tiles from our tile types
- Prefabs: Tank prefab with Rigidbody2D + CircleCollider2D
- Input System: Add Nintendo Switch support package, map Joy-Con
- Our Python logic: Tank.cs, EnemyAI.cs identical but in C#
- Build Settings: Switch -> Add NDP (Nintendo Developer Package) via Package Manager (only after dev approval)

Performance for Switch in Unity:
- Sprite Atlas all tank/tiles into 1 atlas
- Use object pooling for bullets/particles
- Target 60fps, docked 1920x1080, handheld 1280x720 (Unity handles automatically)

## 4. Technical Requirements for eShop (Lot Check)

Nintendo has ~100 page guidelines, but critical for Tank 93:

**Must Have:**
- [ ] 60fps stable (no drops below 55)
- [ ] Loading screen < 30 sec first boot, < 10 sec level load
- [ ] Proper handling of Sleep Mode (pause on HOME button)
- [ ] Save data: use Switch save API, handle corrupt save
- [ ] Error messages: show proper "Controller disconnected" etc via Nintendo API
- [ ] No crash on any button mashing / Joy-Con disconnect
- [ ] Icons: 256x256, 128x128, screenshots 1280x720 x 6-10
- [ ] Age rating: ESRB E, PEGI 3 (no violence issue since tanks cartoon)
- [ ] Handles both docked and handheld, single Joy-Con + Pro Controller

**Input for Tank 93 specifically:**
- Support: Single Joy-Con horizontal (1P), Dual Joy-Con (2P), Pro Controller
- Use Nintendo's "Appliance" input library to detect Joy-Con style
- Vibration: add HD Rumble when shooting/exploding (simple for lot check love)

**From our Pygame prototype, we already handle:**
- Pausing (P -> HOME)
- Mute (M -> Switch has system mute, but keep)
- HUD outside playfield (safe area aware)

## 5. Store Assets & Submission

You need (prepare now):
- Game title: Can't be "Tank 1990" trademarked. Use "Tank 93: Steel Defense" or similar
- Icon 512x512 original art (our modernized pixel is safe)
- Screenshots: 1920x1080 docked, 1280x720 handheld - 6 minimum
- Trailer: 30-60 sec, no copyrighted music
- Description: 2 languages minimum (EN + JP ideal)
- Price: $4.99-$9.99 for indie retro
- Rating: Apply via IARC at https://www.globalratings.com (free for eShop)
- Privacy Policy URL

## 6. Roadmap Timeline from Today

Week 1-2: Polish Pygame prototype (you are here), record gameplay video
Week 3: Apply to Nintendo dev program with video + this codebase as portfolio
Week 4-6: While waiting, start Godot/Unity port using same logic (I can generate Godot project next)
Week 7-10: Once approved, get SDK, build Switch version, test on dev kit (or use W4 cloud test)
Week 11-12: Prepare store assets, submit to lot check
Week 13-14: Fix lot check issues, rating, release

## 7. How This Pygame Code Helps the Port

| Pygame File | Godot Equivalent | Unity Equivalent |
|-------------|------------------|------------------|
| settings.py | Settings.gd (Autoload) | GameConstants.cs ScriptableObject |
| tilemap.py LEVELS | res://levels/Level1.tscn TileMap | Assets/Tilemaps/Level1.asset |
| tank.py | Tank.gd (CharacterBody2D) | Tank.cs + Rigidbody2D |
| enemy.py AI | Enemy.gd state machine | EnemyAI.cs NavMeshAgent? Or manual |
| bullet.py | Bullet.gd Area2D + raycast | Bullet.cs + collision |
| powerup.py | PowerUp.gd Area2D | PowerUp.cs OnTriggerEnter |
| particles.py | GPUParticles2D | Particle System + pooling |
| hud.py | CanvasLayer + Labels | Canvas + TextMeshPro |
| game.py | Main.tscn + Game.gd | GameManager.cs + Game Loop |

Logic like bullet power, star levels, shovel timer is same constants so port is 1:1.

## 8. Quick Start Godot Template (I can create next)

If you want me to create the Godot 4 template alongside this Pygame version, say "create godot port". I'll generate:
- Godot project.godot
- Settings.gd from settings.py
- Tileset PNGs from our draw functions
- Tank.gd, Enemy.gd, Bullet.gd
- Levels converted

Then you only need Nintendo SDK to export.

## 9. Legal - IMPORTANT

- Don't use "Battle City" name, "Tank 1990" is also risky (though common in China). Use original name.
- Don't rip NES sprites. Our current rendering is geometric shapes -> you own it. For final, commission pixel artist to make 32x32 HD tanks inspired but not copied.
- Music: need original chiptune. Use beepbox.co to make.
- To publish: you need to own all assets.

## 10. Checklist Before Applying to Nintendo

- [ ] Have playable video (record from this Pygame version with OBS)
- [ ] Have website or portfolio (GitHub repo of this game is enough)
- [ ] Show you can handle Joy-Con (we already do joystick)
- [ ] Show project structure and ability to finish (README explains Switch plan)
- [ ] Company registration optional but helps (LLC/individual?)

Good luck! This prototype is already 70% of the gameplay needed. Port is mostly translation, not redesign.

Want me to generate the Godot 4 project now so you have both PC Pygame + Godot ready for Nintendo?

