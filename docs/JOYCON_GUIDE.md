# Joy-Con Support for Tank93 - Complete Guide

Tank93 **fully supports Nintendo Switch Joy-Con** for local Python version. Web version Joy-Con is postponed (user request: only local).

## Quick Answer

**Yes, Joy-Con works!** Both separate (L as P1, R as P2) and combined L/R as single Pro controller.

- **Single Joy-Con (L)**: D-pad + stick = move, any face button = shoot
- **Single Joy-Con (R)**: Stick = move, face buttons = shoot
- **Combined L/R**: Becomes "Nintendo Switch Joy-Con (L/R)" - 6 axes - P1 uses axes 2,3 (right stick), P2 uses 0,1 (left stick) - for 2P co-op with one combined device

Current mapping is stored in `game/assets/controller_mapping.json` (your current file already correct for combined L/R):

```json
{
  "maps": {
    "RIGHT": {"type": "axis", "index": 0, "value": 1},
    "LEFT":  {"type": "axis", "index": 0, "value": -1},
    "UP":    {"type": "axis", "index": 1, "value": -1},
    "DOWN":  {"type": "axis", "index": 1, "value": 1},
    "SHOOT": {"type": "button", "index": 4, "value": 1}
  },
  "name": "Nintendo Switch Joy-Con (L/R)"
}
```

## Pairing Joy-Con

### macOS
1. System Settings → Bluetooth → ON
2. On Joy-Con, hold **SYNC** button (small black button between SL/SR) for 3 sec until lights blink fast
3. In Bluetooth list, click **Connect** next to `Joy-Con (L)` / `Joy-Con (R)` or `Joy-Con (L/R)` if both attached to grip
4. Lights should become solid
5. Verify:
   ```bash
   python3 debug_joycon.py
   # Should show: Found 1-2 joysticks: Joy-Con (L) axes=..., Joy-Con (R) etc
   ```
6. Run game:
   ```bash
   python3 main.py
   # Or headless to test:
   .venv/bin/python -c "import pygame; pygame.joystick.init(); print(pygame.joystick.get_count())"
   ```

### Windows
1. Settings → Bluetooth & devices → Add device → Bluetooth
2. Hold SYNC on Joy-Con until blink
3. Select `Joy-Con (L)` / `(R)` to pair
4. May need **BetterJoy** or **joycond-cemuhook** driver for combined L/R mode to work as one Pro controller (Windows doesn't combine by default)
5. Test with `python debug_joycon.py`

### Linux
1. `bluetoothctl` → `scan on` → wait for Joy-Con MAC → `pair <MAC>` → `trust <MAC>` → `connect <MAC>`
2. For combined mode, need `joycond` service: `sudo systemctl enable --now joycond` (on Ubuntu) to get `Nintendo Switch Combined Joy-Cons` device
3. Test with `python debug_joycon.py`

## Playing with Joy-Con

### 1P (Single Joy-Con)

- Connect **Joy-Con (L)** or **Joy-Con (R)** or **combined L/R**
- Run:
  ```bash
  python3 main.py
  ```
- Controls (per `player.py`):
  - **Stick** = move tank (8 directions)
  - **D-pad** (Joy-Con L) = also move (when stick idle)
  - **Any face button** (A/B/X/Y, L/R, triggers) = shoot (very permissive to fix "attack not working")
  - **Minus (button 8)** = Insert Coin (+10 lives)
  - **Plus (button 9)** = Pause / Start / Join
  - **X/Y** = Life share Chad↔Lida (when 2P)

### 2P Co-op with Joy-Con

**Option A: Two separate Joy-Cons (recommended)**

- Pair **both** L and R separately (not combined):
  ```bash
  python3 debug_joycon.py
  # Should show 2 joysticks: Joy-Con (L) and Joy-Con (R)
  ```
- Game auto-sorts: `Joy-Con (L) → P1 (Chad)`, `Joy-Con (R) → P2 (Lida)` via `sort_key` in `game.py:115-137`
- Run `python3 main.py` - P1 stick = L, P2 stick = R, no cross-control (fixed in `player.py:125-157` ignore keyboard when joystick active)

**Option B: One combined L/R device (Linux/macOS with grip or joycond)**

- Pair as **combined** (attach both to grip, or Linux joycond merges them):
  ```bash
  # Shows: Nintendo Switch Joy-Con (L/R) axes=6
  ```
- This single device has 6 axes: 0,1=left stick, 2,3=right stick, 4,5=triggers
- Game splits it: P1 uses axes 2,3 (right stick), P2 uses 0,1 (left stick) — see `player.py:252-275`
- Known bug workaround: if left affects right, game tries swapped axes (tries 2,3 then fallback 0,1)

### Debugging Joy-Con

```bash
# Live view what Joy-Con sends
python3 debug_joycon.py
# 20 sec live test: move stick, press D-pad, A/B/X/Y, SL/SR, L/R, +/-
# It prints: Axes=[0.00, 1.00] Btns=[4] Hats=[]

# Interactive remap (you say direction, then press it)
python3 interactive_mapper.py
# Prompts UP/DOWN/LEFT/RIGHT/SHOOT/COIN/START, saves to game/assets/controller_mapping.json

# Old calibrator (legacy)
python3 calibrate_joycon.py
# Saves joycon_calibration.json
```

### Current Mapping File

`game/assets/controller_mapping.json` is auto-loaded by `game/input_manager.py` → `player.py:220-236`:

- Priority: custom mapping from JSON first, then hardcoded Joy-Con logic
- Handles combined split: P1 right stick 2,3 → P2 left 0,1
- If no custom file: defaults to axes 0=horizontal, 1=vertical

### Logs for Joy-Con Troubleshooting

All Joy-Con inputs are logged to debug DB (SQLite 0-latency):

```bash
python debug_report.py              # auto-diagnosis including joystick errors
python debug_query.py --last --state
python debug_query.py --last --errors
python -m game.debug_logger stats    # shows joystick_info_str
```

Game logs:
- `JOY_ERR` on SystemError from virtual joystick (macOS bug, auto-blocks JOYAXISMOTION)
- `JOY_BTN` for button presses with player_id hint
- `JOYHAT` for hat motions
- `INPUT` for key/joy with device code

If you see "Too many joystick errors - disabling all joysticks", game falls back to keyboard (handled in `game.py:1006-1013`).

### Settings for Joy-Con 90° Rotation Bug

Some Joy-Cons report swapped axes (Up→Right etc). Fixed in `game/settings.py`:

```python
JOYCON_L_SWAP = True
JOYCON_L_INVERT_Y = True
JOYCON_R_SWAP = True
JOYCON_R_INVERT_Y = True
JOYCON_SWAP_AXES = True  # fallback
```

Change these if your Joy-Con is rotated 90°. File is reloaded live? No, restart game after edit.

### Known Issues & Fixes Done

- **Cross-control left affects right**: Fixed - in 2P mode with joystick, keyboard ignored (player.py:146-157), and combined split tries both axis pairs (252-275)
- **Attack not working on Right Joy-Con**: Fixed - very permissive shoot detection (any button 0-7, triggers axis 4/5) in player.py:448-500
- **D-pad mapped to attack**: Fixed - Right Joy-Con face buttons are SHOOT not movement (player.py:372-383), Left D-pad movement only
- **Menu stuck due to noisy JOYAXISMOTION**: Fixed - blocked in game.py:143-146
- **SystemError on macOS virtual joystick**: Caught in game.py:989-1019, auto-disables joysticks after 8 errors
- **2P sync bug swapped L/R**: Fixed - sorted by name L before R in game.py:115-137 and rescan_joysticks()

### Rescan Joysticks In-Game

Press **J** key to rescan Joy-Cons (calls `rescan_joysticks()` sorted L→R consistent). Useful if you pair mid-game.

### FAQ

**Q: I have 0 joysticks detected but Joy-Con shows connected in Bluetooth**
- macOS sometimes needs game to request input: run `main.py`, then press button on Joy-Con, then press J to rescan
- Also try `debug_joycon.py` which pumps events for 15 sec waiting

**Q: Joy-Con shows as "Pro Controller" with 6 axes?**
- That's combined mode - expected on macOS when both L+R attached to grip or Linux with joycond
- Game handles it: splits for 2P, or uses as 1P if only 1 player

**Q: One Joy-Con moves both tanks?**
- Unpair/repair as separate devices, not combined. Or in game, ensure 2 distinct joysticks shown in `debug_joycon.py`
- Check logs `game.py` sorts L before R

**Q: Can I use Joy-Con for web version?**
- Web Joy-Con postponed per user request. Python local version is fully supported. Web uses Gamepad API which needs similar mapping but not yet implemented (was started then paused). For now, use Python local for Joy-Con.

**Q: How to reset mapping?**
```bash
rm game/assets/controller_mapping.json joycon_calibration.json
# Next run uses defaults axes 0/1 + button 4 shoot
# Or rerun interactive_mapper.py
```

**Q: What about Switch Pro Controller?**
- Works same - 2 sticks + D-pad. Pro has 6 axes, game falls back to left stick, right stick if left idle

### Architecture References

- `game/input_manager.py`: loads JSON, get_direction_from_joystick() with combined split, get_buttons_from_joystick()
- `game/entities/player.py:118-521`: handle_input() with custom mapping priority, Joy-Con L/R detection, axis calibration, deadzone 0.32, ice sliding
- `game/game.py:136-147`: joystick init + blocking noisy motion events
- `game/settings.py:286-303`: JOYCON_* calibration constants, D-pad maps
- `game/assets/controller_mapping.json`: current mapping (axis 0 horizontal, 1 vertical, button 4 shoot for L/R combined)
- `debug_joycon.py`: live tester
- `interactive_mapper.py`: creates mapping JSON via prompts

### Testing Without Physical Joy-Con

Headless E2E tests don't need Joy-Con - they mock keyboard. But you can test logic:

```bash
pytest tests/test_menu_navigation.py -v -k joy
# Tests JOYHAT left/right toggling 1P/2P
.venv/bin/python -m pytest tests/test_progressive_difficulty.py -v
```

### Future (Web Joy-Con - Planned but Paused)

User said "no need to do web support yet". When resumed, plan:
- Port `input_manager.py` logic to JS `src/input_manager.js`
- Use `navigator.getGamepads()` (already partially in web-pure/game.js, but was reverted for now? Actually web now has basic axes[0/1] + button 0, needs Joy-Con L/R detection similar to Python)
- Map same 90° fixes to JS
- Test with `https://gamepad-tester.com`

For now, local Python is the Joy-Con path.
