# Porting Checklist - Pygame to Switch-Ready Engine

## Pygame Specifics to Change

1. Coordinates: We use PLAYFIELD_X/Y offset for HUD. Keep same in Godot/Unity - playfield at (48,48)
2. TILE_SIZE 24 -> Keep 24 for logic, but render at 32 for HD
3. Grid 26x26 small tiles == 13x13 big tiles. Keep LEVELS array as is.

## Level Format (Engine Agnostic)

Our LEVELS is:
```python
LEVELS[stage][13][13] where value:
0 empty, 1 brick, 2 steel, 3 water, 4 grass, 5 ice
Convert to small 26x26 by 2x2 expansion.
```

Export for any engine:
```json
{
  "stage": 1,
  "tiles": [[...13x13...]]
}
```

## Input Abstraction

We already abstract input via:
- keys[WASD] + joystick.get_axis()
For Godot/Unity create Input map:
- p1_up, p1_down, p1_left, p1_right, p1_shoot
- p2_*
- joy_p1_shoot: Joy Button 0 (A)

## Game States to Keep

- menu: main, level, howto
- playing
- paused (HOME)
- stage_clear / gameover

## Save/Load for Switch

Will need save high score. Use:
- Godot: FileAccess + Nintendo save mount point (user://)
- Unity: PlayerPrefs + Switch save API

## Performance Tips for Switch (Tegra X1)

- Tank 93 is cheap: < 100 draw calls even unoptimized -> fine for Switch
- Keep 60fps: limit particles to 100, use object pool
- Use sprite atlas not individual draws (our Pygame draws rects - faster on Switch with atlas)

## Build Sizes

Pygame: 50MB with python
Godot: ~30MB Switch nro
Unity: ~200MB but okay

Target eShop size < 500MB

## Testing Without Dev Kit

- Test Joy-Con: use BetterJoy or real Joy-Con via Bluetooth on PC
- Test resolutions: 1280x720 handheld mode window
- Test sleep: simulate HOME pause
- Use Ryujinx emulator? Not official but for quick test (don't ship with it)
