# Tank93 Godot - OG Classic Tank Game - Exports Everywhere

Free Godot 4.4 project, builds WebGL + Android APK from one codebase.

## What is this?

Port of Python Tank93 (35 NES maps, progressive difficulty counter, vehicle choice tank vs monster truck 1.3x + flamethrower, authentic NES explosion with screenshake + flash, Joy-Con support) to Godot.

- **35 original NES maps** from `assets/maps.json` (generated from Python `game/levels/battle_city.py` via `scripts/generate_web_assets.py`)
- **Progressive difficulty** same as Python: `total_stages_cleared` persistent counter never modulo
  - `MAX 4->12` (`4 + floor(total*0.5)` cap 12)
  - `SPAWN 2.5s->0.4s` (`max(0.4s, 2.5s - total*0.08s)`)
  - `speed x1+loop*0.12`, `shoot x1+loop*0.15`, `total enemies base + total*2 + loop*5`
- **Vehicle choice** at landing page: TANK 1.0x or MONSTER TRUCK 1.3x + FLAME (default weapon flamethrower cone 7 flames short range)
- **Monster truck item** 2x bigger crushes bricks/steel/forest/enemies, NES blue truck with yellow stripes big black tires
- **Authentic NES explosion** blocky 8->16->20->smoke with screenshake 3-14 + white flash + debris + glow
- **Joy-Con** support via Input Map deadzone 0.32

## Open in Godot

1. Download Godot 4.4 from https://godotengine.org
2. Import > select `godot-tank93/project.godot`
3. Press F5 Play
4. Controls: WASD + SPACE (P1), Arrows + ENTER (P2), Gamepad stick + A (P1 shoot), V = toggle tank/truck at menu

## Week 1-2 Build ONE

Already done:
- Day 1-3: Settings.gd from settings.json 86 keys, TileMap 26x26, Main.tscn states menu/playing/paused/stage_clear
- Day 4-6: Player.gd (OG tank + monster truck 1.3x + flamethrower), Enemy.gd (A* big tile 13x13)
- Day 7-10: Juice - screenshake 3/6/10/14, flash 0.15-1.0s, particles 14-30, hitstop 0.05s time_scale 0.1 on boss/base, squash & stretch scale tween

One core loop, 30 sec to fun: Protect base, kill N tanks. 5 words: Protect base, crush tanks.

## Week 3 Ship Everywhere

### WebGL -> itch.io + CrazyGames (with ads)

In Godot:
- Project > Export > Web > Export `build/web/index.html`
- itch.io: New project > Upload zip > Embed in page, viewport 960x720, enable Mobile friendly, set 720x1280 vertical? But Tank is 4:3, keep 960x720 horizontal
- CrazyGames: Same WebGL + add their SDK. Create `crazygames-sdk.js`:
  ```js
  // In Main.gd _init_level call: JavaScriptBridge.eval("CrazyGames.SDK.Game.gameplayStart()")
  // On stage clear: gameplayStop + happyTime
  ```
  For MVP without SDK, just upload same zip. They will add ads: video between stages auto.

### Android APK -> Google Play with ads

- Install Android SDK via Godot > Editor > Export > Android > Download SDK (or Android Studio)
- Create keystore: `keytool -genkey -v -keystore debug.keystore -alias androiddebugkey -storepass android -keypass android -keyalg RSA -validity 10000`
- Export AAB (not APK now): Project > Export > Android > Export AAB `build/android/Tank93.aab`
- Google Play Console: New app > Closed testing track > Important: new personal accounts need 20 testers 14 days closed test before production. Create closed testing NOW, add 20 emails (friends or test family). Or use Organization account to bypass.
- Ads: Use `GodotAdMob` plugin https://github.com/PoingStudios/godot-admob-plugin
  - In Player.gd gameover: if deaths %3==0 -> show interstitial
  - Banner bottom always

### 3 Short Clips (7 sec each for TikTok/Reels/Shorts)

Record in OBS 9:16 vertical crop of 960x720 center:

1. **Close call:** Base 1HP, you place shovel last second + 2 tanks explode with screenshake + flash. Text overlay: "1000 hours in Battle City = this instinct"
2. **Monster truck crush:** Start as truck 1.3x, hold shoot flamethrower cone melting 5 bricks in a row + crush steel. Chainsaw SFX.
3. **Boss escape:** Caged monster base hit -> green boss escapes crushing walls -> you homing missile tracks it.

Same clip export 9:16 (TikTok/Reels/Shorts), 1:1 (Instagram), 16:9 (YouTube). Hashtags #battklecity #tank90 #nailong #indiedev #retrogaming

## Week 4 Measure and Double Down

If web >5k plays: pitch Poki. They need: WebGL link, 16:9, mobile touch joystick (we have basic gamepad but add on-screen touch). Email: developers@poki.com with 2 GIFs.

If mobile >30% D1 retention: add rewarded ad "Continue +3 lives" + Remove Ads IAP $1.99.

If nothing hits: reskin core loop - same 35 maps, but replace yellow tank sprite with Nailong (we have `nailong.jpeg` already). Don't start from scratch.

## 3 Rules That Make Small Games Profitable

1. One core loop, 30 sec to fun. Tank93: Protect base, kill tanks. Explained in 5 words.
2. Juice > features. This Godot port has: screenshake 3-14, flash 0.15-1.0, particles 14-30 debris + sparks, hitstop 0.05s, scale pulse 0.2->1.3 back, squash & stretch, flamethrower flicker orange-yellow. No RPG features needed.
3. Build for replay, not story. High score in Save.gd, best_stage, total_stages_cleared persistent, vehicle choice unlock, daily challenge TODO: random map of day.

## Project Structure

```
godot-tank93/
  project.godot
  export_presets.cfg (Web + Android)
  autoload/Settings.gd (86 keys from Python via generate_web_assets.py)
           Save.gd (high score, best stage, vehicle choice)
           GameData.gd (current level, total cleared, loop)
  scenes/Main.tscn + Main.gd (states menu/playing/paused/gameover/stage_clear + progressive difficulty)
  entities/Player.tscn + Player.gd (tank 1.0x or truck 1.3x + flamethrower cone 7 flames)
          Enemy.tscn + Enemy.gd (A* 13x13, speed_mult loop, shoot_mult)
          Bullet.tscn + Bullet.gd (homing 3.564 turn 0.068 fuel 574, flamethrower melt brick/forest/steel)
          Explosion.tscn + Explosion.gd (NES blocky 8->16->20->smoke + shake + flash + juice)
  assets/maps.json (35 stages), settings.json (86 keys), General-Sprites.png, nailong.jpeg
```

## Debug Logging (same taxonomy as Python)

Python has SQLite WAL logger, Godot uses print + Save for now. For full parity later, add `Logger.gd` autoload mirroring `web-pure/src/logger.js` ring buffer.

Tags shared: STATE, STUCK, STEEL, WEAPON, PERF, MAP, HUD, VEHICLE, MONSTER_TRUCK, FLAMETHROWER, EXPLOSION

## Next Steps

1. Open in Godot 4.4, hit F5
2. Day 11-13: Export Web, test on itch.io local `python3 -m http.server 8000` in `build/web/`
3. Day 14-16: Add CrazyGames SDK calls (optional for MVP)
4. Day 17-21: Export Android AAB
5. Day 22-30: Record 3 clips, post daily
