#!/usr/bin/env python3
"""
Generate web-pure assets from Python source of truth.
- maps.json from game/levels/battle_city.py
- settings.json from game/settings.py

Usage:
    python scripts/generate_web_assets.py          # generate
    python scripts/generate_web_assets.py --check  # CI: fail if dirty
    python scripts/generate_web_assets.py --verbose

This is the canonical sync pipeline defined in docs/WEB_SYNC_CONTRACT.md
"""
import json
import sys
import shutil
import pathlib
import argparse

ROOT = pathlib.Path(__file__).parent.parent
WEB_ASSETS = ROOT / "web-pure" / "assets"
WEB_IMAGES = WEB_ASSETS / "images"
WEB_SOUNDS = WEB_ASSETS / "sounds"

sys.path.insert(0, str(ROOT))

def gen_maps():
    """Generate maps.json from Python battle_city.py"""
    from game.levels.battle_city import LEVELS_13, LEVELS_26
    # Try to get enemy queues if available
    try:
        from game.levels.battle_city import ENEMY_QUEUES as EQUEUES
    except ImportError:
        try:
            from game.levels.battle_city import BOTS_RAW as BOTS_RAW
            # Convert bots_raw to queues if needed - BOTS_RAW is raw bot placements?
            # For now, keep optional
            EQUEUES = None
        except ImportError:
            EQUEUES = None

    data = {
        "levels_13": LEVELS_13,
        "levels_26": LEVELS_26,
        "stage_count": len(LEVELS_26),
    }
    # Also try feichao original queues from game.py imports
    try:
        # tilemap has LEVELS_26 etc too
        from game.tilemap import LEVELS_26 as T26
        from game.tilemap import LEVELS_13_ORIGINAL, LEVELS_26_ORIGINAL
        # keep but main is battle_city
    except ImportError:
        pass

    # Enemy queues: try to load from feichao if present
    try:
        from game.levels.battle_city import ENEMY_QUEUES as EQ
        data["enemy_queues"] = EQ
    except ImportError:
        # Fallback: try game/tilemap or battle_city raw
        try:
            from game.tilemap import ENEMY_QUEUES as EQ2
            data["enemy_queues"] = EQ2
        except ImportError:
            # Leave out, will be synthesized in JS if missing
            data["enemy_queues"] = []
    try:
        from game.levels.battle_city import BOTS_RAW
        data["bots_raw"] = BOTS_RAW
    except ImportError:
        data["bots_raw"] = []

    return data

def gen_settings():
    """Generate full settings.json from game/settings.py - not just 8 fields"""
    import game.settings as S

    # Gather all relevant constants
    settings = {
        # Screen / Playfield
        "SCREEN_WIDTH": getattr(S, 'SCREEN_WIDTH', 960),
        "SCREEN_HEIGHT": getattr(S, 'SCREEN_HEIGHT', 720),
        "FPS": getattr(S, 'FPS', 60),
        "TILE_SIZE": getattr(S, 'TILE_SIZE', 24),
        "GRID_W": getattr(S, 'GRID_W', 26),
        "GRID_H": getattr(S, 'GRID_H', 26),
        "PLAYFIELD_W": getattr(S, 'PLAYFIELD_W', 624),
        "PLAYFIELD_H": getattr(S, 'PLAYFIELD_H', 624),
        "PLAYFIELD_X": getattr(S, 'PLAYFIELD_X', 48),
        "PLAYFIELD_Y": getattr(S, 'PLAYFIELD_Y', 48),
        "BASE_POS": list(getattr(S, 'BASE_POS', (12,24))),
        "PLAYER_SPAWN": [list(p) for p in getattr(S, 'PLAYER_SPAWN', [(8,24),(16,24)])],
        "ENEMY_SPAWNS": [list(p) for p in getattr(S, 'ENEMY_SPAWNS', [(0,0),(12,0),(24,0)])],
        "TANK_SIZE": getattr(S, 'TANK_SIZE', 32),
        "TANK_SPEED": getattr(S, 'TANK_SPEED', {"player":3.3,"enemy":1.8,"fast":3.0}),
        "BULLET_SPEED": getattr(S, 'BULLET_SPEED', 8.25),
        "BULLET_SIZE": getattr(S, 'BULLET_SIZE', 6),
        "MAX_BULLETS": getattr(S, 'MAX_BULLETS', {"player":2,"enemy":1}),

        # Armor
        "ARMOR_INITIAL_PLAYER": getattr(S, 'ARMOR_INITIAL_PLAYER', 100),
        "ARMOR_INITIAL_ENEMY": getattr(S, 'ARMOR_INITIAL_ENEMY', {}),
        "ARMOR_MAX_PLAYER": getattr(S, 'ARMOR_MAX_PLAYER', 300),
        "ARMOR_UPGRADE_STAR": getattr(S, 'ARMOR_UPGRADE_STAR', 25),
        "ARMOR_UPGRADE_TANK": getattr(S, 'ARMOR_UPGRADE_TANK', 50),
        "ARMOR_UPGRADE_GUN": getattr(S, 'ARMOR_UPGRADE_GUN', 30),
        "ARMOR_SHIELD_REDUCTION": getattr(S, 'ARMOR_SHIELD_REDUCTION', 0.3),

        # Brick / Steel durability
        "BRICK_HITS_NEEDED": getattr(S, 'BRICK_HITS_NEEDED', {"normal":2,"power":1,"rapid":3,"homing":4,"spread":2,"venom":2}),
        "STEEL_HITS_NEEDED": getattr(S, 'STEEL_HITS_NEEDED', {"normal":5,"power":3,"rapid":8,"homing":6,"spread":5,"venom":4}),

        # Gameplay counters
        "ENEMIES_PER_LEVEL": getattr(S, 'ENEMIES_PER_LEVEL', 20),
        "MAX_ENEMIES_ON_FIELD": getattr(S, 'MAX_ENEMIES_ON_FIELD', 4),
        "ENEMY_SPAWN_INTERVAL": getattr(S, 'ENEMY_SPAWN_INTERVAL', 150),

        # Powerups
        "POWERUP_TYPES": getattr(S, 'POWERUP_TYPES', ['helmet','clock','shovel','star','grenade','tank','gun','homing','spread','rapid','shrink','giant']),
        "POWERUP_DURATION": getattr(S, 'POWERUP_DURATION', {}),
        "STAR_LEVELS": getattr(S, 'STAR_LEVELS', 4),

        # Homing missile - critical for sync
        "HOMING_SPEED": getattr(S, 'HOMING_SPEED', 3.564),
        "HOMING_MAX_DISTANCE": getattr(S, 'HOMING_MAX_DISTANCE', 573),
        "HOMING_TURN_SPEED": getattr(S, 'HOMING_TURN_SPEED', 0.068),
        "HOMING_DETECTION_RANGE": getattr(S, 'HOMING_DETECTION_RANGE', 573),
        "HOMING_LOS_CHECK": getattr(S, 'HOMING_LOS_CHECK', True),
        "HOMING_ASTAR_REPLAN_INTERVAL": getattr(S, 'HOMING_ASTAR_REPLAN_INTERVAL', 36),
        "HOMING_AVOIDANCE_LOOKAHEAD": getattr(S, 'HOMING_AVOIDANCE_LOOKAHEAD', 2.6),
        "HOMING_WALL_SAFE_MARGIN": getattr(S, 'HOMING_WALL_SAFE_MARGIN', 0.28),
        "HOMING_STUCK_DESTROY_THRESHOLD": getattr(S, 'HOMING_STUCK_DESTROY_THRESHOLD', 16),

        # Shrink/Giant/Venom/Bomb
        "SHRINK_SCALE": getattr(S, 'SHRINK_SCALE', 0.5),
        "SHRINK_SPEED_MULT": getattr(S, 'SHRINK_SPEED_MULT', 2.0),
        "GIANT_SCALE": getattr(S, 'GIANT_SCALE', 2.0),
        "GIANT_DURATION": getattr(S, 'GIANT_DURATION', 900),
        "MONSTER_SPEED_MULT": getattr(S, 'MONSTER_SPEED_MULT', 1.0),
        "VENOM_DISSOLVE_TIME": getattr(S, 'VENOM_DISSOLVE_TIME', 1080),
        "VENOM_SPEED": getattr(S, 'VENOM_SPEED', 3.7125),
        "BULLET_COUNTER_ENABLED": getattr(S, 'BULLET_COUNTER_ENABLED', True),
        "VENOM_SPILLOVER_ENABLED": getattr(S, 'VENOM_SPILLOVER_ENABLED', True),
        "VENOM_SPILLOVER_RADIUS": getattr(S, 'VENOM_SPILLOVER_RADIUS', 72),
        "VENOM_SPILLOVER_INTERVAL": getattr(S, 'VENOM_SPILLOVER_INTERVAL', 20),
        "VENOM_SPILLOVER_DAMAGE": getattr(S, 'VENOM_SPILLOVER_DAMAGE', 1),
        "VENOM_SPILLOVER_ENEMY_DAMAGE_FACTOR": getattr(S, 'VENOM_SPILLOVER_ENEMY_DAMAGE_FACTOR', 1.0),
        "VENOM_SPILLOVER_PLAYER_DAMAGE_FACTOR": getattr(S, 'VENOM_SPILLOVER_PLAYER_DAMAGE_FACTOR', 0.5),
        "VENOM_SPILLOVER_BOSS_DAMAGE_FACTOR": getattr(S, 'VENOM_SPILLOVER_BOSS_DAMAGE_FACTOR', 0.7),
        "BOMB_ARMOR_DAMAGE": getattr(S, 'BOMB_ARMOR_DAMAGE', 100),
        "BOMB_POWER_DAMAGE": getattr(S, 'BOMB_POWER_DAMAGE', 2),

        # Arcade
        "INITIAL_LIVES": getattr(S, 'INITIAL_LIVES', 3),
        "COIN_LIVES": getattr(S, 'COIN_LIVES', 10),
        "MAX_LIVES": getattr(S, 'MAX_LIVES', 99),
        "CONTINUE_TIME": getattr(S, 'CONTINUE_TIME', 900),

        # Progressive difficulty (user request: counter + harder)
        "DIFFICULTY_MAX_ENEMIES_BASE": getattr(S, 'DIFFICULTY_MAX_ENEMIES_BASE', 4),
        "DIFFICULTY_MAX_ENEMIES_PER_STAGE": getattr(S, 'DIFFICULTY_MAX_ENEMIES_PER_STAGE', 0.5),
        "DIFFICULTY_MAX_ENEMIES_CAP": getattr(S, 'DIFFICULTY_MAX_ENEMIES_CAP', 12),
        "DIFFICULTY_SPAWN_BASE": getattr(S, 'DIFFICULTY_SPAWN_BASE', 150),
        "DIFFICULTY_SPAWN_PER_STAGE": getattr(S, 'DIFFICULTY_SPAWN_PER_STAGE', 4.8),
        "DIFFICULTY_SPAWN_MIN": getattr(S, 'DIFFICULTY_SPAWN_MIN', 24),
        "DIFFICULTY_RAMP_INTERVAL": getattr(S, 'DIFFICULTY_RAMP_INTERVAL', 720),
        "DIFFICULTY_RAMP_SPAWN_DECREMENT": getattr(S, 'DIFFICULTY_RAMP_SPAWN_DECREMENT', 8),
        "DIFFICULTY_ENEMY_TOTAL_PER_STAGE": getattr(S, 'DIFFICULTY_ENEMY_TOTAL_PER_STAGE', 2),
        "DIFFICULTY_ENEMY_TOTAL_PER_LOOP": getattr(S, 'DIFFICULTY_ENEMY_TOTAL_PER_LOOP', 5),
        "DIFFICULTY_SPEED_PER_LOOP": getattr(S, 'DIFFICULTY_SPEED_PER_LOOP', 0.12),
        "DIFFICULTY_SHOOT_PER_LOOP": getattr(S, 'DIFFICULTY_SHOOT_PER_LOOP', 0.15),
        "DIFFICULTY_LOOP_ARMOR_MULT": getattr(S, 'DIFFICULTY_LOOP_ARMOR_MULT', 1),

        # Player display
        "PLAYER_NAMES": getattr(S, 'PLAYER_NAMES', ["Chad","Lida"]),

        # Tile types + dirs for sanity
        "TILE_EMPTY": getattr(S, 'TILE_EMPTY', 0),
        "TILE_BRICK": getattr(S, 'TILE_BRICK', 1),
        "TILE_STEEL": getattr(S, 'TILE_STEEL', 2),
        "TILE_WATER": getattr(S, 'TILE_WATER', 3),
        "TILE_GRASS": getattr(S, 'TILE_GRASS', 4),
        "TILE_ICE": getattr(S, 'TILE_ICE', 5),
        "DIRS": {k: list(v) for k,v in getattr(S, 'DIRS', {}).items()},
        "EIGHT_DIRS": getattr(S, 'EIGHT_DIRS', ['UP','UP_RIGHT','RIGHT','DOWN_RIGHT','DOWN','DOWN_LEFT','LEFT','UP_LEFT']),

        # Colors (for web rendering parity)
        "COLORS": {
            "BRICK": list(getattr(S, 'COLOR_BRICK', (210,56,24))),
            "BRICK_DARK": list(getattr(S, 'COLOR_BRICK_DARK', (140,30,10))),
            "STEEL": list(getattr(S, 'COLOR_STEEL', (210,210,210))),
            "WATER": list(getattr(S, 'COLOR_WATER', (28,90,240))),
            "GRASS": list(getattr(S, 'COLOR_GRASS', (60,160,20))),
            "ICE": list(getattr(S, 'COLOR_ICE', (190,190,190))),
        }
    }

    # Normalize tuples to lists for JSON
    def normalize(v):
        if isinstance(v, tuple):
            return list(v)
        return v

    return settings

def copy_sprites(verbose=False):
    """Ensure sprite sheet is synced"""
    src = ROOT / "game" / "assets" / "General-Sprites.png"
    dst = WEB_IMAGES / "General-Sprites.png"
    if src.exists():
        WEB_IMAGES.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
            if verbose:
                print(f"Copied {src} -> {dst}")
            return True
        else:
            if verbose:
                print(f"Sprite up to date: {dst}")
    else:
        if verbose:
            print(f"WARN: {src} not found, skipping sprite copy")
    return False

def main():
    parser = argparse.ArgumentParser(description="Generate web assets from Python source")
    parser.add_argument('--check', action='store_true', help='Check if generated files would change (CI mode)')
    parser.add_argument('--verbose', action='store_true', help='Verbose')
    args = parser.parse_args()

    WEB_ASSETS.mkdir(parents=True, exist_ok=True)

    # Generate maps
    maps_data = gen_maps()
    maps_path = WEB_ASSETS / "maps.json"
    existing_maps = None
    if maps_path.exists():
        try:
            with open(maps_path, 'r') as f:
                existing_maps = json.load(f)
        except:
            pass

    maps_json_str = json.dumps(maps_data)
    if args.check:
        if existing_maps is None:
            print(f"FAIL: {maps_path} missing - need to generate")
            return 1
        # Compare levels only (stage_count etc) - ignore formatting
        if existing_maps.get('levels_26') != maps_data['levels_26'] or existing_maps.get('levels_13') != maps_data['levels_13']:
            print(f"FAIL: {maps_path} out of sync with Python source (LEVELS_26/13 differ). Run scripts/generate_web_assets.py to regenerate.")
            print(f"  stages: existing={len(existing_maps.get('levels_26',[]))} new={len(maps_data['levels_26'])}")
            return 1
        # Also check settings
        settings_data = gen_settings()
        settings_path = WEB_ASSETS / "settings.json"
        if not settings_path.exists():
            print(f"FAIL: {settings_path} missing")
            return 1
        with open(settings_path, 'r') as f:
            existing_settings = json.load(f)
        # Check critical fields
        critical = ["BULLET_SPEED","TANK_SPEED","HOMING_SPEED","HOMING_TURN_SPEED","ARMOR_INITIAL_PLAYER","BRICK_HITS_NEEDED","VENOM_DISSOLVE_TIME"]
        diffs = []
        for k in critical:
            if existing_settings.get(k) != settings_data.get(k):
                diffs.append(f"{k}: existing={existing_settings.get(k)} vs new={settings_data.get(k)}")
        if diffs:
            print(f"FAIL: {settings_path} out of sync:")
            for d in diffs:
                print(f"  {d}")
            return 1
        print("OK: web assets in sync")
        return 0
    else:
        with open(maps_path, 'w') as f:
            json.dump(maps_data, f)
        if args.verbose:
            print(f"Wrote {maps_path} stages={len(maps_data['levels_26'])} 26x26={len(maps_data['levels_26'][0])}x{len(maps_data['levels_26'][0][0])}")
        else:
            print(f"Generated {maps_path} ({len(maps_data['levels_26'])} stages)")

        settings_data = gen_settings()
        settings_path = WEB_ASSETS / "settings.json"
        with open(settings_path, 'w') as f:
            json.dump(settings_data, f, indent=2)
        print(f"Generated {settings_path} ({len(settings_data)} keys) - full settings from Python source")

        copy_sprites(verbose=args.verbose)
        return 0

if __name__ == '__main__':
    sys.exit(main())
