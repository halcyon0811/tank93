"""
Input Manager - Loads custom controller mapping from JSON
Supports mapping created by interactive_mapper.py
User says direction then hits it, we save mapping and use it here.
"""
import json
import os
import pathlib

ASSET_DIR = pathlib.Path(__file__).parent / "assets"
MAPPING_PATH = ASSET_DIR / "controller_mapping.json"
LEGACY_PATH = pathlib.Path(__file__).parent.parent / "joycon_calibration.json"

# Default mapping if no custom file
DEFAULT_MAPPING = {
    "maps": {
        "UP": {"type": "axis", "index": 1, "value": -1},
        "DOWN": {"type": "axis", "index": 1, "value": 1},
        "LEFT": {"type": "axis", "index": 0, "value": -1},
        "RIGHT": {"type": "axis", "index": 0, "value": 1},
    }
}

_cached_mapping = None

def load_mapping():
    global _cached_mapping
    if _cached_mapping is not None:
        return _cached_mapping

    # Try asset path
    for path in [MAPPING_PATH, LEGACY_PATH]:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    print(f"[Input] Loaded controller mapping from {path}: {data.get('name','unknown')}")
                    # Normalize
                    if "maps" in data:
                        _cached_mapping = data
                        return _cached_mapping
                    else:
                        # Legacy format from calibrate_joycon.py might be different
                        # Try to convert
                        maps = {}
                        for k, v in data.items():
                            if isinstance(v, (list, tuple)) and len(v) >= 3:
                                # Old format: ('axis', name, index, value) etc
                                pass
                            else:
                                maps[k.replace("LEFT_", "").replace("RIGHT_", "")] = v
                        if maps:
                            _cached_mapping = {"maps": maps, "name": "legacy"}
                            return _cached_mapping
            except Exception as e:
                print(f"[Input] Failed to load {path}: {e}")

    print("[Input] No custom mapping found, using default")
    _cached_mapping = {"maps": DEFAULT_MAPPING["maps"], "name": "default"}
    return _cached_mapping

def get_direction_from_joystick(joystick, player_id=1, num_players=1):
    """
    Given a pygame joystick, return direction string based on custom mapping
    Handles combined Joy-Con (L/R) split for 2P: P1 uses right stick (axes 2,3), P2 uses left stick (0,1)
    Returns: 'UP','DOWN','LEFT','RIGHT', 'UP_LEFT', etc. or None
    """
    mapping_data = load_mapping()
    maps = mapping_data.get("maps", {})

    try:
        # Detect combined Joy-Con
        is_combined = False
        try:
            name = joystick.get_name().lower()
            if 'l/r' in name and joystick.get_numaxes() >= 4:
                is_combined = True
        except:
            pass

        # Check each direction in maps
        # For axes, we need to check threshold
        # Collect pressed directions
        pressed = []

        for dir_name in ["UP", "DOWN", "LEFT", "RIGHT"]:
            if dir_name not in maps:
                continue
            m = maps[dir_name]
            m_type = m.get("type")
            m_idx = m.get("index")
            m_val = m.get("value")

            # Handle combined Joy-Con split: P1 uses right stick (axes 2,3), P2 uses left (0,1)
            # So if mapping was for left stick (0,1), for P1 we need to check 2,3
            actual_idx = m_idx
            if is_combined and num_players == 2:
                if player_id == 1:
                    # P1 should use right stick, so if mapping is for left stick (0->2, 1->3)
                    if m_idx == 0:
                        actual_idx = 2
                    elif m_idx == 1:
                        actual_idx = 3
                else:
                    # P2 uses left stick, keep as is, but if mapping was for right stick, map back?
                    if m_idx == 2:
                        actual_idx = 0
                    elif m_idx == 3:
                        actual_idx = 1

            if m_type == "axis":
                if actual_idx < joystick.get_numaxes():
                    axis_val = joystick.get_axis(actual_idx)
                    # Check if axis matches expected direction with threshold 0.5
                    if m_val == 1 and axis_val > 0.5:
                        pressed.append(dir_name)
                    elif m_val == -1 and axis_val < -0.5:
                        pressed.append(dir_name)
            elif m_type == "button":
                if m_idx < joystick.get_numbuttons():
                    if joystick.get_button(m_idx):
                        pressed.append(dir_name)
            elif m_type == "hat":
                if m_idx < joystick.get_numhats():
                    hx, hy = joystick.get_hat(m_idx)
                    # For hat, value is (x,y) tuple
                    if isinstance(m_val, (list, tuple)):
                        if (hx, hy) == tuple(m_val):
                            pressed.append(dir_name)
                    else:
                        # If mapping was for hat but we only stored one axis? Check
                        if (hx, hy) != (0, 0):
                            # Determine direction from hat
                            if hy == 1:
                                pressed.append("UP")
                            elif hy == -1:
                                pressed.append("DOWN")
                            elif hx == -1:
                                pressed.append("LEFT")
                            elif hx == 1:
                                pressed.append("RIGHT")

        # Handle diagonal combinations
        if "UP" in pressed and "LEFT" in pressed:
            return "UP_LEFT"
        if "UP" in pressed and "RIGHT" in pressed:
            return "UP_RIGHT"
        if "DOWN" in pressed and "LEFT" in pressed:
            return "DOWN_LEFT"
        if "DOWN" in pressed and "RIGHT" in pressed:
            return "DOWN_RIGHT"
        if "UP" in pressed:
            return "UP"
        if "DOWN" in pressed:
            return "DOWN"
        if "LEFT" in pressed:
            return "LEFT"
        if "RIGHT" in pressed:
            return "RIGHT"

        return None
    except Exception as e:
        # Fallback: don't crash, return None
        # print(f"[Input] Error getting direction: {e}")
        return None

def get_buttons_from_joystick(joystick, player_id=1, num_players=1):
    """
    Returns dict of action -> bool based on mapping
    e.g., SHOOT, COIN, START
    Handles combined Joy-Con split
    """
    mapping_data = load_mapping()
    maps = mapping_data.get("maps", {})
    result = {}

    # Detect combined
    is_combined = False
    try:
        name = joystick.get_name().lower()
        if 'l/r' in name and joystick.get_numaxes() >= 4:
            is_combined = True
    except:
        pass

    for action in ["SHOOT", "COIN", "START", "ATTACK"]:
        if action not in maps:
            continue
        m = maps[action]
        m_type = m.get("type")
        m_idx = m.get("index")

        # Handle combined split for buttons: For combined, P1 uses right side buttons?
        # For Joy-Con, attack buttons are different per side. For simplicity, keep same index for both,
        # but if is_combined and player_id==1, try to map to right side equivalent if left side pressed?
        # For now, keep same index, but allow fallback to any button press for shoot (permissive)
        actual_idx = m_idx
        # For combined Joy-Con, if mapping is for left side button (e.g., D-pad), right side might have different index
        # We keep simple: use actual_idx as is
        try:
            if m_type == "button" and actual_idx < joystick.get_numbuttons():
                result[action] = joystick.get_button(actual_idx)
            elif m_type == "axis" and actual_idx < joystick.get_numaxes():
                # For axis as button (trigger)
                val = joystick.get_axis(actual_idx)
                expected = m.get("value", 1)
                if expected == 1:
                    result[action] = val > 0.5
                else:
                    result[action] = val < -0.5
            elif m_type == "hat" and actual_idx < joystick.get_numhats():
                hx, hy = joystick.get_hat(actual_idx)
                result[action] = (hx, hy) != (0, 0)
            else:
                result[action] = False
        except:
            result[action] = False

    return result

def reload_mapping():
    global _cached_mapping
    _cached_mapping = None
    return load_mapping()
