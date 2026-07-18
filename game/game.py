"""Main Game class - handles states, spawner, collisions"""
import pygame
import random
import math
import sys
import pathlib
import datetime
import traceback as tb
from .settings import *
from .tilemap import TileMap, LEVELS

# --- Comprehensive debug logger (SQLite 0-latency) ---
try:
    from .debug_logger import debug_logger, DB_PATH as DEBUG_DB_PATH, LOG_TXT_PATH as DEBUG_TXT_PATH
    from .debug_logger import log_event as _log_event, log_state as _log_state_change_db, log_gameplay as _log_gameplay, log_crash as _log_crash, log_input as _log_input
    HAS_DEBUG_LOGGER = True
    TRACE_LOG_PATH = DEBUG_TXT_PATH
    DEBUG_DB_ENABLED = True
except ImportError as e:
    print(f"[DebugLogger] Failed to import debug_logger: {e}, falling back to file-only")
    HAS_DEBUG_LOGGER = False
    DEBUG_DB_ENABLED = False
    DEBUG_DB_PATH = pathlib.Path(__file__).parent.parent / "debug.db"
    TRACE_LOG_PATH = pathlib.Path(__file__).parent.parent / "bug_trace.log"

    def _log_event(tag, message, level="INFO", extra=None, with_stack=False):
        try:
            import datetime as _dt
            ts = _dt.datetime.now().isoformat()
            from .debug_logger import LOG_TXT_PATH as _p
            with open(_p, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{level}] [{tag}] {message}\n")
        except:
            pass
    def _log_state_change_db(old_state, new_state, reason, extra=None):
        pass
    def _log_gameplay(*a, **kw):
        pass
    def _log_crash(*a, **kw):
        pass
    def _log_input(*a, **kw):
        pass

# Legacy shims for existing instrumented code
def _trace_log(tag, msg, with_stack=False, level="INFO"):
    # Route to new logger
    try:
        _log_event(tag, msg, level=level, extra=None, with_stack=with_stack)
    except Exception:
        print(f"[{level}] [{tag}] {msg}")

def _trace_state_change(old_state, new_state, reason, extra=""):
    try:
        # extra may be string in old code, convert to dict if needed
        extra_dict = extra if isinstance(extra, dict) else {"extra": extra} if extra else None
        if HAS_DEBUG_LOGGER:
            debug_logger.log_state_change(old_state, new_state, reason, extra=extra_dict)
        else:
            _log_state_change_db(old_state, new_state, reason, extra=extra_dict)
        # Also text log via _log_event
        level = "WARN" if new_state == 'menu' and old_state == 'playing' else "INFO"
        _log_event("STATE", f"{old_state} -> {new_state} | reason={reason} | {extra}", level=level, extra=extra_dict, with_stack=True)
    except Exception:
        print(f"[STATE] {old_state} -> {new_state} | {reason}")
# Try import authentic 35-stage data
try:
    from .levels.battle_city import ENEMY_QUEUES as ENEMY_QUEUES_ORIGINAL, BOTS_RAW as BOTS_RAW_ORIGINAL, STAGE_COUNT as ORIGINAL_STAGE_COUNT
    from .tilemap import LEVELS_13_ORIGINAL, LEVELS_26_ORIGINAL  # noqa: F401 keep available
except ImportError:
    ENEMY_QUEUES_ORIGINAL = []
    BOTS_RAW_ORIGINAL = []
    ORIGINAL_STAGE_COUNT = len(LEVELS)
    LEVELS_13_ORIGINAL = []
    LEVELS_26_ORIGINAL = []

# Sound manager - authentic NES Battle City 35-stage SFX (feichao93 pack + 8-bit retro)
try:
    from .sound_manager import sound_manager as snd_mgr
    from .sound_manager import SoundManager
except ImportError:
    snd_mgr = None
from .entities.bullet import Bullet, Base
from .entities.player import PlayerTank
from .entities.enemy import EnemyTank
from .entities.powerup import PowerUp
from .entities.particles import ParticleSystem
from .ui.hud import HUD

class Game:
    def __init__(self, is_web=False):
        self.is_web = is_web
        if is_web:
            print("[Game] Running in WEB mode - disabling LAN host and projector server (not supported in browser)")
            print("[Game] Web controls: WASD+SPACE for P1, Arrows+Enter for P2, or Gamepad")
        import os
        os.environ.setdefault('SDL_IME_SHOWUI', '0')
        os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
        try:
            pygame.init()
        except Exception as e:
            print(f"Pygame init failed: {e}")
            raise
        self.joysticks = []
        self.joystick_enabled = True
        try:
            pygame.joystick.init()
            temp = []
            for i in range(pygame.joystick.get_count()):
                try:
                    js = pygame.joystick.Joystick(i)
                    js.init()
                    temp.append(js)
                except Exception:
                    continue
            def sort_key(js):
                try:
                    n = js.get_name().lower()
                except:
                    n = ""
                if 'joy-con (l)' in n:
                    return (0, n)
                if 'joy-con (r)' in n:
                    return (1, n)
                if 'l/r' in n:
                    return (2, n)
                if 'joy-con' in n:
                    return (3, n)
                return (4, n)
            temp.sort(key=sort_key)
            self.joysticks = temp
        except Exception as e:
            print(f"Joystick init failed, running without joystick: {e}")
            self.joystick_enabled = False
            self.joysticks = []

        try:
            pygame.event.set_allowed(pygame.JOYDEVICEADDED)
            pygame.event.set_allowed(pygame.JOYDEVICEREMOVED)
        except:
            pass
        # FIX: block noisy motion events causing menu stuck / SystemError on macOS virtual joystick
        try:
            pygame.event.set_blocked(pygame.JOYAXISMOTION)
            pygame.event.set_blocked(pygame.JOYBALLMOTION)
        except:
            pass

        # Screen size - bigger for mega maps to keep tank size same (32px tank vs 24px tile, playfield 1248px)
        # For mega, need at least MEGA_PLAYFIELD_W + HUD + margins = 1248+250+96 = 1594, height 1248+96=1344
        # Use 1600x1400 for mega, 960x720 for normal
        self.is_mega = MEGA_ENABLED
        screen_w, screen_h = (MEGA_SCREEN_WIDTH, MEGA_SCREEN_HEIGHT + 400) if self.is_mega else (SCREEN_WIDTH, SCREEN_HEIGHT)
        # Cap to reasonable monitor size, but allow bigger for mega
        if self.is_mega:
            # 1248 playfield height needs taller window, use 1350 height
            screen_w = MEGA_PLAYFIELD_W + 320  # 1248+320=1568
            screen_h = MEGA_PLAYFIELD_H + 100  # 1348
            # Limit to screen max but keep ratio - use 1600x1400 if fits, else scale?
            # For Mac, max is usually 2560x1600, so 1568x1348 fits
            # We'll create window 1600x900 and add internal scrolling? Simpler: 1600x900 with smaller HUD
            # For now use 1600x900 and let playfield be scrollable? But requirement says just bigger map
            # Let's use 1600x900 and center playfield with camera - simplest: keep screen 1600x900 and draw 1248 playfield fully visible
            screen_w = MEGA_SCREEN_WIDTH  # 1600
            screen_h = 900
            # If mega playfield 1248 tall won't fit in 900, we need taller - use 1400
            screen_h = 1400
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((screen_w, screen_h))
        pygame.display.set_caption("Tank 93 Enhanced - Battle City Tribute - F11/F for Fullscreen")
        self.clock = pygame.time.Clock()
        self.hud = HUD(is_mega=self.is_mega)

        # --- Comprehensive debug session start (SQLite + text) ---
        try:
            joystick_info_str = ""
            if self.joysticks:
                infos = []
                for js in self.joysticks:
                    try:
                        infos.append(f"{js.get_name()} axes={js.get_numaxes()} btns={js.get_numbuttons()} hats={js.get_numhats()} iid={js.get_instance_id()}")
                    except Exception as ex:
                        infos.append(f"error {ex}")
                joystick_info_str = "; ".join(infos)
            if HAS_DEBUG_LOGGER:
                debug_logger.start_session(screen_w=screen_w, screen_h=screen_h, is_fullscreen=self.is_fullscreen,
                                           is_mega=self.is_mega, fps_target=FPS,
                                           joystick_count=len(self.joysticks), joystick_info=joystick_info_str,
                                           initial_level=0, num_players=1)
            _trace_log("INIT", f"Game init complete is_mega={self.is_mega} joysticks={len(self.joysticks)} screen={screen_w}x{screen_h}", level="INFO")
            if self.joysticks:
                for idx, js in enumerate(self.joysticks):
                    try:
                        _trace_log("INIT", f"  JS{idx}: {js.get_name()} axes={js.get_numaxes()} btns={js.get_numbuttons()} hats={js.get_numhats()} iid={js.get_instance_id()}")
                    except Exception as e:
                        _trace_log("INIT", f"  JS{idx}: error getting info {e}", level="WARN")
            _log_gameplay("SESSION_START", level_idx=0, data={"screen_w": screen_w, "screen_h": screen_h, "is_mega": self.is_mega, "joysticks": joystick_info_str})
        except Exception as e:
            print(f"[Trace] Failed to init log: {e}")
            import traceback
            traceback.print_exc()

        self.state = 'menu'
        self.menu_selected = 0
        self.menu_mode = 'main'
        self.num_players = 1
        self.current_level = 0
        self.high_score = 0
        self.menu_hat_cooldown = 0
        self.menu_stuck_timer = 0
        self.joystick_error_count = 0

        self.tilemap = None
        self.base = None
        self.players = []
        self.enemies = []
        self.bullets = []
        self.powerups = []
        self.particles = ParticleSystem()
        self.enemies_total = ENEMIES_PER_LEVEL
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        self.muted = False
        self.gameover_won = False

        self.coins = 0
        self.coins_total = 0
        self.continue_timer = 0
        self.credits = {1: 0, 2: 0}

        # Mega map mode flag - already set above from MEGA_ENABLED
        try:
            from .levels.mega_maps import MEGA_LEVELS_52, MEGA_ENEMY_QUEUES, MEGA_STAGE_COUNT
            self.mega_levels = MEGA_LEVELS_52
            self.mega_queues = MEGA_ENEMY_QUEUES
            self.mega_count = MEGA_STAGE_COUNT
        except ImportError as e:
            print(f"Mega maps not found: {e}, using normal")
            self.mega_levels = None
            self.mega_queues = None
            self.mega_count = 0
            self.is_mega = False

        # LAN Multiplayer - Remote P2 join via same local network - disabled in web (no UDP in browser)
        self.network_host = None
        self.network_host_ip = None
        if not getattr(self, 'is_web', False):
            try:
                from .network import NetworkHost, get_local_ip
                self.network_host = NetworkHost()
                self.network_host_ip = self.network_host.start()
                if self.network_host_ip:
                    print(f"[Game] LAN Host ready - P2 can join remotely via same WiFi")
                    print(f"[Game] Remote: python3 remote_client.py --host {self.network_host_ip}")
            except Exception as e:
                print(f"[Game] Network host failed to start: {e}")
                self.network_host = None
                self.network_host_ip = None
        else:
            print("[Game] Web mode: LAN host disabled (no UDP in browser)")

        # Projector Mode - disabled in web (web already is projector via browser)
        self.projector_ip = None
        self.projector_port = 8080
        if not getattr(self, 'is_web', False):
            try:
                from .projector import start_server
                self.projector_ip = start_server(port=self.projector_port)
                if self.projector_ip:
                    print(f"[Game] Projector server ready - Open on same WiFi:")
                    print(f"[Game] Projector: http://{self.projector_ip}:{self.projector_port} - for projector or any browser")
            except Exception as e:
                print(f"[Game] Projector server failed to start: {e}")
                self.projector_ip = None
        else:
            print("[Game] Web mode: Projector server disabled (web already is projector)")

    def toggle_fullscreen(self):
        """Toggle fullscreen mode - for projector or immersive play, with content zoomed"""
        old_fs = getattr(self, 'is_fullscreen', False)
        try:
            self.is_fullscreen = not self.is_fullscreen
            _trace_log("FULLSCREEN", f"Toggling fullscreen {old_fs} -> {self.is_fullscreen} state={getattr(self,'state','?')} stack:", with_stack=True)
            if self.is_fullscreen:
                # Use SCALED flag so 960x720 content is zoomed to fill fullscreen (fixes 'content not zoomed' issue)
                # SCALED keeps logical size as SCREEN_WIDTH x SCREEN_HEIGHT but scales to desktop res
                try:
                    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
                    print(f"[Display] Switched to FULLSCREEN SCALED mode {SCREEN_WIDTH}x{SCREEN_HEIGHT} -> fullscreen, content zoomed - press F11/F to exit, ESC to exit fullscreen")
                    _trace_log("FULLSCREEN", f"Entered FULLSCREEN SCALED {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
                except Exception as e:
                    # Fallback to (0,0) fullscreen if SCALED not supported
                    print(f"[Display] SCALED fullscreen failed ({e}), trying (0,0) fullscreen")
                    _trace_log("FULLSCREEN", f"SCALED failed {e}, fallback (0,0)", level="WARN")
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    print("[Display] Switched to FULLSCREEN mode (0,0) - press F11/F to exit, ESC to exit fullscreen")
            else:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                print("[Display] Switched to WINDOWED mode")
                _trace_log("FULLSCREEN", "Entered WINDOWED mode")
            pygame.display.set_caption("Tank 93 Enhanced - Battle City Tribute - F11/F for Fullscreen - Content Zoomed")
        except Exception as e:
            _trace_log("FULLSCREEN", f"Toggle failed {e} old_fs={old_fs} new={self.is_fullscreen}", with_stack=True, level="ERROR")
            print(f"[Display] Fullscreen toggle failed: {e}")
            try:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.is_fullscreen = False
            except:
                pass

    def _get_enemy_queue_for_level(self, level_idx):
        lvl = level_idx % (self.mega_count if self.is_mega and self.mega_levels else len(LEVELS))
        if self.is_mega and self.mega_queues and lvl < len(self.mega_queues):
            return list(self.mega_queues[lvl])
        if ENEMY_QUEUES_ORIGINAL and lvl < len(ENEMY_QUEUES_ORIGINAL):
            return list(ENEMY_QUEUES_ORIGINAL[lvl])
        return None

    def _get_enemies_total_for_level(self, level_idx):
        if self.is_mega and self.mega_queues:
            lvl = level_idx % len(self.mega_queues)
            base = len(self.mega_queues[lvl]) if lvl < len(self.mega_queues) else 30
            extra = lvl * 3 + (lvl // 5) * 4
            return base + extra
        lvl = level_idx % len(LEVELS)
        if ENEMY_QUEUES_ORIGINAL and lvl < len(ENEMY_QUEUES_ORIGINAL):
            base = len(ENEMY_QUEUES_ORIGINAL[lvl])
            extra = lvl * 2 + (lvl // 5) * 3
            return base + extra
        return ENEMIES_PER_LEVEL + lvl * 3 + (lvl // 4) * 2

    def init_level(self, level_idx, num_players=1):
        old_state = getattr(self, 'state', 'unknown')
        _trace_log("LEVEL", f"init_level called level_idx={level_idx} num_players={num_players} old_state={old_state} is_mega={self.is_mega} current_level_before={self.current_level}", with_stack=True)
        if self.is_mega and self.mega_levels:
            self.current_level = level_idx % len(self.mega_levels)
            level_data = self.mega_levels[self.current_level]
            self.tilemap = TileMap(level_data, is_mega=True)
            self.tilemap.ensure_spawn_clear()
            # Steel fort around center base
            self.tilemap.build_base_walls(TILE_STEEL, concrete_steel=True)
            self.base = Base(is_mega=True)
        else:
            self.current_level = level_idx % len(LEVELS)
            level_data = LEVELS[self.current_level]
            self.tilemap = TileMap(level_data, is_mega=False)
            self.tilemap.ensure_spawn_clear()
            self.tilemap.build_base_walls(TILE_BRICK)
            self.base = Base()
        self.players = []
        self.enemies = []
        self.bullets = []
        self.powerups = []
        self.particles = ParticleSystem()

        # authentic enemy queue for this stage
        self.enemy_queue = self._get_enemy_queue_for_level(self.current_level)
        # shuffle slightly like NES? Original spawns in grouped order but with some randomness
        # Keep grouped order authentic but allow occasional shuffle of remaining? We'll keep as-is for faithfulness
        # If queue is None, random weighted spawning will be used (legacy)

        # players - use mega spawns if mega mode
        spawns = MEGA_PLAYER_SPAWN if self.is_mega else PLAYER_SPAWN
        for i in range(num_players):
            gx, gy = spawns[i]
            p = PlayerTank(i+1, gx, gy, is_mega=self.is_mega)
            self.players.append(p)

        self.enemies_total = self._get_enemies_total_for_level(self.current_level)
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        # Gradual enemy increase - more enemies as level progresses and within level
        # Max on field: start 4, +1 per 2 levels, capped at 8, plus ramp within level
        self.max_enemies_on_field = min(8, MAX_ENEMIES_ON_FIELD + self.current_level // 2)
        self.base_max_enemies = self.max_enemies_on_field
        # Spawn interval: start 2.5s, -0.1s per level, min 0.8s, plus within-level ramp
        self.dynamic_spawn_interval = max(int(0.8 * FPS), int(ENEMY_SPAWN_INTERVAL - self.current_level * 0.12 * FPS))
        self.base_spawn_interval = self.dynamic_spawn_interval
        self.difficulty_ramp_timer = 0
        # Monster boss system
        self.boss_enemy = None
        self.boss_released = False
        self.boss_fight_timer = 0
        self.monster_boss_defeated = False
        prev_state = getattr(self, '_prev_state_for_trace', old_state)
        self.state = 'playing'
        _trace_state_change(old_state, 'playing', f"init_level level={self.current_level} players={num_players}", extra=f"enemies_total={self.enemies_total}")
        # Comprehensive gameplay log
        try:
            _log_gameplay("LEVEL_INIT", level_idx=self.current_level, data={"num_players": num_players, "enemies_total": self.enemies_total, "max_on_field": self.max_enemies_on_field, "spawn_interval": self.dynamic_spawn_interval, "enemy_queue_len": len(self.enemy_queue) if self.enemy_queue else 0})
        except:
            pass
        # SFX: For first stage (new game), play authentic NES intro "Battle City Tank 1990 NES Intro Live 8bit by deegee (5.59 sec)"
        # For subsequent stages, play stage_start jingle. Battlefield has NO BGM (authentic NES) - removed silly loop.
        if snd_mgr:
            try:
                if self.current_level == 0:
                    # First stage new game - play real intro music
                    snd_mgr.play_battle_intro()
                else:
                    snd_mgr.play_stage_start()
                # BGM disabled – authentic NES had no battlefield music, only SFX (user said silly)
                # snd_mgr.play_bgm('bgm_battle')  # removed
            except:
                pass

    def init_next_level(self):
        # preserve players
        prev_players = self.players
        if self.is_mega and self.mega_levels:
            self.current_level = (self.current_level + 1) % len(self.mega_levels)
            level_data = self.mega_levels[self.current_level]
            self.tilemap = TileMap(level_data, is_mega=True)
            self.tilemap.ensure_spawn_clear()
            self.tilemap.build_base_walls(TILE_STEEL, concrete_steel=True)
            self.base = Base(is_mega=True)
        else:
            self.current_level = (self.current_level + 1) % len(LEVELS)
            level_data = LEVELS[self.current_level]
            self.tilemap = TileMap(level_data, is_mega=False)
            self.tilemap.ensure_spawn_clear()
            self.tilemap.build_base_walls(TILE_BRICK)
            self.base = Base()
        self.enemies = []
        self.bullets = []
        self.powerups = []
        self.particles = ParticleSystem()
        self.enemy_queue = self._get_enemy_queue_for_level(self.current_level)
        self.enemies_total = self._get_enemies_total_for_level(self.current_level)
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        # Gradual increase per level
        self.max_enemies_on_field = min(8, MAX_ENEMIES_ON_FIELD + self.current_level // 2)
        self.base_max_enemies = self.max_enemies_on_field
        self.dynamic_spawn_interval = max(int(0.8 * FPS), int(ENEMY_SPAWN_INTERVAL - self.current_level * 0.12 * FPS))
        self.base_spawn_interval = self.dynamic_spawn_interval
        self.difficulty_ramp_timer = 0
        # Monster boss system - reset per level
        self.boss_enemy = None
        self.boss_released = False
        self.boss_fight_timer = 0
        self.monster_boss_defeated = False
        # respawn players at start with protections - preserve items across stages
        spawns = MEGA_PLAYER_SPAWN if self.is_mega else PLAYER_SPAWN
        new_players = []
        for i, old_p in enumerate(prev_players):
            gx, gy = spawns[i]
            p = PlayerTank(old_p.player_id, gx, gy, is_mega=self.is_mega)
            p.score = old_p.score
            p.lives = old_p.lives
            p.star_level = old_p.star_level
            # Preserve items across stages (homing, spread, rapid) - only lost on death, not on stage clear
            p.homing_timer = getattr(old_p, 'homing_timer', 0)
            p.spread_timer = getattr(old_p, 'spread_timer', 0)
            p.rapid_timer = getattr(old_p, 'rapid_timer', 0)
            p.homing_active = getattr(old_p, 'homing_active', False)
            p.spread_active = getattr(old_p, 'spread_active', False)
            p.rapid_active = getattr(old_p, 'rapid_active', False)
            # Also preserve helmet if still active? Keep star level only per classic, but items should persist
            p.helmet_timer = getattr(old_p, 'helmet_timer', 0)
            p.invulnerable_timer = getattr(old_p, 'helmet_timer', 0)  # if had helmet, keep shield briefly
            p.update_bullet_power()
            new_players.append(p)
        self.players = new_players
        self.state = 'playing'
        if snd_mgr:
            try:
                # Stage 2-35 also start jingle
                snd_mgr.play_stage_start()
            except:
                pass

    def _on_stage_clear(self):
        if snd_mgr:
            try:
                snd_mgr.play_stage_clear()
            except:
                pass

    def _on_game_over(self):
        if snd_mgr:
            try:
                snd_mgr.play_game_over()
            except:
                pass

    def insert_coin(self, player_id=None):
        """Arcade: Each coin gives COIN_LIVES (10) and allows rejoin"""
        self.coins += 1
        self.coins_total += 1
        # Determine target player
        target = None
        if player_id is not None:
            # Find existing player with this id
            for p in self.players:
                if p.player_id == player_id:
                    target = p
                    break
        else:
            # Find first dead player needing lives
            for p in self.players:
                if not p.alive and p.lives < 0:
                    target = p
                    break

        if target:
            # Give 10 lives
            target.add_lives(COIN_LIVES)
            # Try respawn immediately if dead
            if not target.alive:
                gx, gy = PLAYER_SPAWN[target.player_id-1]
                # clear area around spawn
                if self.tilemap:
                    self.tilemap.clear_area(gx-1, gy-1, 4, 4)
                # check if can spawn (not blocked by enemy)
                can_spawn = True
                test_rect = pygame.Rect(PLAYFIELD_X+gx*TILE_SIZE, PLAYFIELD_Y+gy*TILE_SIZE, TANK_SIZE, TANK_SIZE)
                for en in self.enemies:
                    if en.alive and test_rect.colliderect(en.rect):
                        can_spawn = False
                # if blocked, still set alive but will respawn next frame
                target.respawn(gx, gy)
                if not can_spawn:
                    # give extra protection if spawn blocked
                    target.spawn_protection = 300
                self.particles.add_spawn(target.rect.centerx, target.rect.centery)
                self.particles.add_explosion(target.rect.centerx, target.rect.centery, (255,215,0), 15)
            # If was gameover, continue same stage
            if self.state == 'gameover' and not self.gameover_won:
                # Repair base if destroyed
                if self.base and not self.base.alive:
                    self.base.reset()
                    if self.tilemap:
                        self.tilemap.ensure_spawn_clear()
                        self.tilemap.build_base_walls(TILE_BRICK)
                self.state = 'playing'
                self.continue_timer = 0
                # Rumble disabled per user request
                if ENABLE_RUMBLE:
                    try:
                        target_js = None
                        if target and hasattr(self, 'joysticks'):
                            idx = target.player_id - 1
                            if 0 <= idx < len(self.joysticks):
                                target_js = self.joysticks[idx]
                            if target_js and 'l/r' in target_js.get_name().lower():
                                if target.player_id == 1:
                                    target_js.rumble(0.8, 0.0, 300)
                                else:
                                    target_js.rumble(0.0, 0.8, 300)
                            elif target_js and hasattr(target_js, 'rumble'):
                                target_js.rumble(0.5, 0.9, 300)
                    except:
                        pass
            return True
        else:
            # No existing dead player – maybe P2 wants to join late in 1P game
            if len(self.players) < 2:
                # Create new player 2 if not exists, or 1 if none
                new_id = 2 if any(p.player_id==1 for p in self.players) else 1
                if player_id is not None:
                    new_id = player_id
                # Avoid duplicate
                if not any(p.player_id==new_id for p in self.players):
                    gx, gy = PLAYER_SPAWN[new_id-1]
                    np = PlayerTank(new_id, gx, gy, lives=COIN_LIVES)
                    np.score = 0
                    self.players.append(np)
                    self.num_players = len(self.players)
                    self.particles.add_spawn(np.rect.centerx, np.rect.centery)
                    if self.state == 'gameover' and not self.gameover_won:
                        if self.base and not self.base.alive:
                            self.base.reset()
                            if self.tilemap:
                                self.tilemap.ensure_spawn_clear()
                                self.tilemap.build_base_walls(TILE_BRICK)
                        self.state = 'playing'
                        self.continue_timer = 0
                    return True
            # If all players alive, just give lives to first player as bonus
            if self.players:
                # Give to player with lowest lives
                poorest = min(self.players, key=lambda p: p.lives)
                poorest.add_lives(COIN_LIVES)
                self.particles.add_explosion(poorest.rect.centerx, poorest.rect.centery, (255,215,0), 10)
                return True
        return False

    def player_join(self, player_id):
        """Player presses START to join, needs coin (10 lives)"""
        _trace_log("INPUT", f"player_join called player_id={player_id} state={self.state} players={len(self.players)}")
        try:
            _log_gameplay("PLAYER_JOIN_ATTEMPT", level_idx=self.current_level, player_id=player_id, data={"state": self.state, "players": len(self.players)})
        except:
            pass
        # If player already exists and dead with lives<0, insert coin for him
        for p in self.players:
            if p.player_id == player_id:
                if not p.alive and p.lives < 0:
                    return self.insert_coin(player_id)
                else:
                    # already playing, ignore
                    return False
        # If player doesn't exist, create him (costs a coin = 10 lives)
        return self.insert_coin(player_id)

    def spawn_enemy(self):
        if self.enemies_spawned >= self.enemies_total:
            return
        # Use dynamic max that increases gradually
        max_on_field = getattr(self, 'max_enemies_on_field', MAX_ENEMIES_ON_FIELD)
        if len(self.enemies) >= max_on_field:
            return
        # find spawn point that is not blocked - improved to prevent enemy stuck bug
        # Previous logic only checked exact spawn rect overlap, but after first enemy moves slightly (36px),
        # second could spawn too close and cause stuck when they overlap exactly.
        # Now we check distance > TANK_SIZE*1.8 to ensure separation and avoid deadlock where
        # two enemies occupy same spot and block each other's movement forever.
        tries = 0
        enemy_spawns = MEGA_ENEMY_SPAWNS if self.is_mega else ENEMY_SPAWNS
        ts = MEGA_TILE_SIZE if self.is_mega else TILE_SIZE
        while tries < 30:
            sx, sy = random.choice(enemy_spawns)
            # check if occupied - more robust
            blocked = False
            spawn_cx = PLAYFIELD_X + sx * ts + ts//2
            spawn_cy = PLAYFIELD_Y + sy * ts + ts//2
            test_rect = pygame.Rect(PLAYFIELD_X + sx*ts, PLAYFIELD_Y + sy*ts, TANK_SIZE, TANK_SIZE)
            for e in self.enemies:
                if not e.alive:
                    continue
                # Original rect check
                if test_rect.colliderect(e.rect):
                    blocked = True
                    break
                # Distance check to avoid close spawns that cause stuck deadlock
                import math
                dist = math.hypot(e.x - spawn_cx, e.y - spawn_cy)
                if dist < TANK_SIZE * 1.8:  # need separation
                    blocked = True
                    break
            if not blocked:
                for p in self.players:
                    if p.alive:
                        if test_rect.colliderect(p.rect):
                            blocked = True
                            break
                        # also distance for player
                        import math
                        dist_p = math.hypot(p.x - spawn_cx, p.y - spawn_cy)
                        if dist_p < TANK_SIZE * 2:
                            blocked = True
                            break
            if not blocked:
                # authentic queue if available, else fallback weighted random
                etype = None
                if hasattr(self, 'enemy_queue') and self.enemy_queue:
                    # pop from queue front (authentic order: e.g. Stage1 18*basic then 2*fast)
                    # For variety, original NES also spawns in that grouped order.
                    if self.enemies_spawned < len(self.enemy_queue):
                        etype = self.enemy_queue[self.enemies_spawned]
                if etype is None:
                    # fallback weighted (early stages more basic, later more armor)
                    # weight by level difficulty
                    if self.current_level < 5:
                        weights = ['basic']*60 + ['fast']*20 + ['power']*15 + ['armor']*5
                    elif self.current_level < 15:
                        weights = ['basic']*30 + ['fast']*30 + ['power']*25 + ['armor']*15
                    else:
                        weights = ['basic']*15 + ['fast']*25 + ['power']*30 + ['armor']*30
                    etype = random.choice(weights)
                enemy = EnemyTank(sx, sy, etype, is_mega=self.is_mega)
                # Original NES: powerup tanks are at indices 3,7,12,17 (0-based) -> 4 per level
                # feichao remix uses [3,7,12,17]; classic [3,10,17]. We'll follow remix for more fun.
                # If queue is authentic, carrier logic already random 25% in EnemyTank; but we force original powerup positions for authenticity
                if hasattr(self, 'enemy_queue') and self.enemy_queue:
                    powerup_indices = [3, 7, 12, 17]  # remix 4 per stage
                    if self.enemies_spawned in powerup_indices:
                        enemy.powerup_carrier = True
                self.enemies.append(enemy)
                self.enemies_spawned += 1
                self.particles.add_spawn(enemy.rect.centerx, enemy.rect.centery)
                try:
                    _log_gameplay("ENEMY_SPAWN", level_idx=self.current_level, data={"type": etype, "grid_x": sx, "grid_y": sy, "spawned": self.enemies_spawned, "total": self.enemies_total, "on_field": len(self.enemies), "carrier": getattr(enemy, 'powerup_carrier', False)})
                except:
                    pass
                break
            tries+=1

    def release_monster_boss(self):
        """Called when monster base is hit - releases monster as enemy boss tank"""
        if self.boss_released:
            return  # already released
        print("[BOSS] Monster released! Spawning boss tank!")
        self.boss_released = True
        self.boss_fight_timer = 15 * FPS  # 15 seconds to kill boss before game over? Or just track
        # Spawn boss at base position (center for mega)
        bx, by = self.tilemap.base_pos
        self.tilemap.clear_area(bx-1, by-1, 4, 4)
        from .entities.enemy import EnemyTank
        boss = EnemyTank(bx, by, 'monster_boss', is_mega=self.is_mega)
        # Make boss extra strong and at base center
        boss.set_position(bx, by)
        # Give it some initial protection but less
        boss.spawn_protection = 30
        boss.invulnerable_timer = 30
        self.enemies.append(boss)
        self.boss_enemy = boss
        self.particles.add_spawn(boss.rect.centerx, boss.rect.centery)
        self.particles.add_explosion(boss.rect.centerx, boss.rect.centery, (100,255,100), 30)
        # Sound
        try:
            from .sound_manager import sound_manager
            sound_manager.play_explosion(big=True)
            sound_manager.play_powerup_appear()
        except:
            pass
        # Also break base walls to show release
        self.tilemap.clear_area(bx-1, by-1, 4, 4)

        # === NEW: After boss gets out, randomly assign items to current enemies ====
        # User request: "after boss gets out, randomly assign items to current enemy"
        # We assign random powerup carrier status and/or combat abilities (homing, spread, rapid)
        # to existing enemies on field to make fight more chaotic and rewarding
        try:
            import random
            # Count current enemies excluding boss
            other_enemies = [e for e in self.enemies if e is not boss and e.alive]
            if other_enemies:
                print(f"[BOSS] Assigning random items to {len(other_enemies)} current enemies!")
                item_pool_ability = ['homing', 'spread', 'rapid']
                for en in other_enemies:
                    if random.random() < 0.6:  # 60% chance to get an item
                        # 50% become powerup carrier (will drop random powerup when killed)
                        if random.random() < 0.5:
                            en.powerup_carrier = True
                            print(f"  -> Enemy at {en.grid_x},{en.grid_y} now carrier (will drop item)")
                        # 40% gain combat ability
                        if random.random() < 0.4:
                            chosen = random.choice(item_pool_ability)
                            if chosen == 'homing':
                                en.homing_active = True
                                print(f"  -> Enemy at {en.grid_x},{en.grid_y} got HOMING ability!")
                            elif chosen == 'spread':
                                en.spread_active = True
                                print(f"  -> Enemy at {en.grid_x},{en.grid_y} got SPREAD (8-way) ability!")
                            elif chosen == 'rapid':
                                en.rapid_active = True
                                en.shoot_chance *= 2.5
                                en.cooldown = max(0, en.cooldown - 20)
                                print(f"  -> Enemy at {en.grid_x},{en.grid_y} got RAPID x3 ability!")
                        # Visual feedback - small explosion for item assign
                        self.particles.add_explosion(en.rect.centerx, en.rect.centery, (100, 200, 255), 10)
        except Exception as e:
            print(f"[BOSS] Item assign failed: {e}")
            import traceback
            traceback.print_exc()

    def rescan_joysticks(self):
        """Rescan for Joy-Cons, call when user presses J or connects controller
           Fixed for 2P sync bug: sort so Joy-Con (L) = P1, (R) = P2 consistently"""
        try:
            pygame.joystick.init()
            found = []
            for i in range(pygame.joystick.get_count()):
                try:
                    js = pygame.joystick.Joystick(i)
                    js.init()
                    found.append(js)
                except Exception as e:
                    print(f"Joystick {i} init failed: {e}")
                    continue
            # Sort for consistent P1/P2 assignment: L before R, then others
            # This fixes synced movement where P1/P2 got swapped randomly
            def sort_key(js):
                try:
                    name = js.get_name().lower()
                except:
                    name = ""
                # L should come first for P1
                if 'joy-con (l)' in name:
                    return (0, name)
                if 'joy-con (r)' in name:
                    return (1, name)
                if 'l/r' in name:
                    return (2, name)  # combined last, will be split
                if 'joy-con' in name:
                    return (3, name)
                return (4, name)
            found.sort(key=sort_key)
            self.joysticks = found
            for i, js in enumerate(self.joysticks):
                try:
                    print(f"Found joystick {i}: {js.get_name()} axes={js.get_numaxes()} btns={js.get_numbuttons()} hats={js.get_numhats()} -> P{i+1}")
                except:
                    pass
            self.joystick_enabled = len(self.joysticks) > 0
            try:
                pygame.event.set_allowed(pygame.JOYDEVICEADDED)
                pygame.event.set_allowed(pygame.JOYDEVICEREMOVED)
                pygame.event.set_blocked(pygame.JOYAXISMOTION)
                pygame.event.set_blocked(pygame.JOYBALLMOTION)
            except:
                pass
        except Exception as e:
            print(f"Rescan failed: {e}")

    def handle_events(self):
        if hasattr(self, 'menu_hat_cooldown') and self.menu_hat_cooldown > 0:
            self.menu_hat_cooldown -= 1
        # Emergency: if menu stuck for 180 frames (3 sec) without input, allow ANY key (including mouse) to start
        if not hasattr(self, 'menu_stuck_timer'):
            self.menu_stuck_timer = 0
            self.joystick_error_count = 0
        if self.state == 'menu':
            self.menu_stuck_timer += 1
        else:
            self.menu_stuck_timer = 0

        try:
            events = pygame.event.get()
        except (SystemError, KeyError, Exception) as e:
            self.joystick_error_count = getattr(self, 'joystick_error_count', 0) + 1
            _trace_log("JOY_ERR", f"Joystick event error count={self.joystick_error_count} err={e} state={self.state}", with_stack=True, level="ERROR")
            print(f"Joystick event error ({self.joystick_error_count}) recovering: {e}")
            try:
                pygame.event.clear()
            except:
                pass
            try:
                pygame.event.set_blocked(pygame.JOYAXISMOTION)
                pygame.event.set_blocked(pygame.JOYBALLMOTION)
            except:
                pass
            events = []
            # After 8 errors, disable joysticks entirely - keyboard will work
            if self.joystick_error_count > 8 and len(getattr(self, 'joysticks', [])) > 0:
                print("Too many joystick errors - disabling all joysticks, using keyboard only")
                _trace_log("JOY_ERR", f"Disabling all joysticks after {self.joystick_error_count} errors", level="ERROR")
                try:
                    self.joysticks.clear()
                    pygame.joystick.quit()
                except:
                    pass
            # Force start on joystick error - assume user wants to play
            if self.state == 'menu' and self.menu_stuck_timer > 180:
                print("Force starting game due to joystick spam")
                _trace_log("MENU_STUCK", f"Force starting game from joystick error state={self.state} stuck_timer={self.menu_stuck_timer}", with_stack=True)
                self.handle_menu_select()
                return
        for event in events:
            if event.type == pygame.QUIT:
                print(f"[Event] QUIT received - exiting via os._exit")
                try:
                    pygame.quit()
                except:
                    pass
                # Force immediate exit for real window close
                import os
                print(f"[Event] Calling os._exit(0) now")
                os._exit(0)
                print(f"[Event] os._exit did not exit, trying sys.exit")
                sys.exit(0)
                print(f"[Event] sys.exit did not exit, raising SystemExit")
                raise SystemExit(0)
            # Joystick hotplug - important for Switch Joy-Con
            try:
                if event.type == pygame.JOYDEVICEADDED:
                    try:
                        idx = getattr(event, 'device_index', 0)
                        # pygame may have count that includes new device already
                        if idx < pygame.joystick.get_count():
                            js = pygame.joystick.Joystick(idx)
                            js.init()
                            if js.get_instance_id() not in [j.get_instance_id() for j in self.joysticks]:
                                self.joysticks.append(js)
                                print(f"Controller connected: {js.get_name()} - Total {len(self.joysticks)}")
                    except Exception as e:
                        # Ignore hotplug errors (common on macOS with virtual joysticks)
                        pass
                if event.type == pygame.JOYDEVICEREMOVED:
                    try:
                        iid = getattr(event, 'instance_id', None)
                        if iid is not None:
                            self.joysticks = [j for j in self.joysticks if j.get_instance_id() != iid]
                            print(f"Controller disconnected - remaining {len(self.joysticks)}")
                    except:
                        pass
            except Exception:
                pass
            if event.type == pygame.JOYBUTTONDOWN:
                try:
                    # Determine which player this joystick belongs to
                    joy_player_id = None
                    try:
                        iid = getattr(event, 'instance_id', None)
                        if iid is not None:
                            for idx, js in enumerate(self.joysticks):
                                try:
                                    if js.get_instance_id() == iid:
                                        joy_player_id = idx + 1
                                        break
                                except:
                                    continue
                    except:
                        pass
                    # Log joystick button input
                    try:
                        _log_input("JOYBUTTONDOWN", device=f"joy{getattr(event, 'joy', '?')}", code=f"btn{event.button}", value=float(event.button), mapped_action=f"p{joy_player_id} state={self.state}", extra={"button": event.button, "instance_id": getattr(event, 'instance_id', None), "joy_count": len(self.joysticks)})
                    except:
                        pass
                    # Coin: Minus button 8 on Switch, Select/View on Xbox/PS (6,8)
                    if event.button in (8, 6):  # Minus / Select / View = Coin
                        self.insert_coin(joy_player_id)
                    # allow menu navigation with controller
                    _trace_log("JOY_BTN", f"JOYBUTTONDOWN btn={event.button} player_id_hint={joy_player_id} state={self.state} menu_mode={self.menu_mode} iid={getattr(event, 'instance_id', '?')} joy_count={len(self.joysticks)}")
                    if self.state == 'menu':
                        if event.button in (0, 1, 9):  # A/B/Plus
                            _trace_log("JOY_BTN", f"Menu navigation A/B/Plus btn={event.button} -> handle_menu_select selected={self.menu_selected}")
                            self.handle_menu_select()
                    elif self.state in ('gameover', 'stage_clear'):
                        if event.button in (0, 9):  # A / Plus = Continue or Menu
                            if self.gameover_won:
                                _trace_log("JOY_BTN", f"Gameover won RETURN -> init_next_level btn={event.button}")
                                self.init_next_level()
                            else:
                                if self.continue_timer <= 0 or all(p.lives < 0 for p in self.players):
                                    _trace_log("JOY_BTN", f"Gameover lost timer expired or all dead -> menu btn={event.button} timer={self.continue_timer}", level="WARN")
                                    old = self.state
                                    total = sum(p.score for p in self.players)
                                    self.high_score = max(self.high_score, total)
                                    self.state = 'menu'
                                    self.menu_mode = 'main'
                                    _trace_state_change(old, 'menu', f"JOY btn {event.button} gameover timer")
                                else:
                                    if joy_player_id:
                                        _trace_log("JOY_BTN", f"Gameover lost but continue possible -> player_join {joy_player_id}")
                                        self.player_join(joy_player_id)
                        elif event.button in (7,):  # Start for P2 join
                            if joy_player_id:
                                _trace_log("JOY_BTN", f"Gameover P2 join btn 7 player {joy_player_id}")
                                self.player_join(joy_player_id)
                    elif self.state == 'playing':
                        if event.button == 9: # Plus/Options pauses
                            _trace_log("JOY_BTN", f"Playing btn 9 -> paused")
                            old = self.state
                            self.state = 'paused'
                            _trace_state_change(old, 'paused', "JOY Plus pressed")
                        elif event.button == 7: # P2 join mid-game via Start
                            if joy_player_id and (len(self.players) < joy_player_id or not any(p.player_id==joy_player_id for p in self.players)):
                                _trace_log("JOY_BTN", f"Playing btn 7 -> P2 join {joy_player_id}")
                                self.player_join(joy_player_id)
                    elif self.state == 'paused' and event.button in (0, 9):
                        _trace_log("JOY_BTN", f"Paused btn {event.button} -> playing")
                        old = self.state
                        self.state = 'playing'
                        _trace_state_change(old, 'playing', f"JOY resume btn {event.button}")
                except Exception as e:
                    # Don't crash on joystick quirks
                    pass

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                if self.state == 'menu' and event.type == pygame.MOUSEBUTTONDOWN:
                    # Ignore mouse clicks in first 60 frames (avoid accidental trackpad)
                    if getattr(self, 'menu_stuck_timer', 0) > 60:
                        print(f"Mouse click to start menu {self.menu_selected}")
                        self.handle_menu_select()
                    else:
                        print(f"Ignoring early mouse click at frame {self.menu_stuck_timer}")

            if event.type == pygame.JOYHATMOTION:
                try:
                    # Log hat motion
                    try:
                        hx, hy = getattr(event, 'value', (0,0))
                        _log_input("JOYHATMOTION", device=f"joy{getattr(event, 'joy', '?')}", code=f"hat{getattr(event, 'hat', 0)}", value=float(hy*10+hx), mapped_action=f"{hx},{hy}", extra={"value": getattr(event, 'value', None), "state": self.state})
                    except:
                        pass
                    if self.state == 'menu' and self.menu_hat_cooldown == 0:
                        opts = 5 if self.menu_mode=='main' else (len(LEVELS) + 1 if self.menu_mode=='level' else 1)
                        hx, hy = getattr(event, 'value', (0,0))
                        # Ignore if HAT is stuck reporting (0,0) drift - only process non-zero
                        if hy == 0 and hx == 0:
                            pass
                        else:
                            # Main menu: horizontal cards for 1P/2P -> LEFT/RIGHT = toggle 0<->1
                            if self.menu_mode == 'main':
                                if self.menu_selected in (0, 1):
                                    if hx == -1:
                                        self.menu_selected = 1 if self.menu_selected == 0 else 0
                                        self.menu_hat_cooldown = 10
                                        print(f"Menu LEFT via hat -> {self.menu_selected} (1P<->2P)")
                                    elif hx == 1:
                                        self.menu_selected = 1 if self.menu_selected == 0 else 0
                                        self.menu_hat_cooldown = 10
                                        print(f"Menu RIGHT via hat -> {self.menu_selected} (1P<->2P)")
                                # Vertical navigation for all main options
                                if hy == 1:
                                    if self.menu_selected in (0, 1):
                                        self.menu_selected = 4
                                    else:
                                        self.menu_selected = (self.menu_selected - 1) % opts
                                    self.menu_hat_cooldown = 12
                                    print(f"Menu UP via hat -> {self.menu_selected}")
                                elif hy == -1:
                                    if self.menu_selected in (0, 1):
                                        self.menu_selected = 2
                                    else:
                                        self.menu_selected = (self.menu_selected + 1) % opts
                                    self.menu_hat_cooldown = 12
                                    print(f"Menu DOWN via hat -> {self.menu_selected}")
                            else:
                                if hy == 1:
                                    self.menu_selected = (self.menu_selected - 1) % opts
                                    self.menu_hat_cooldown = 12
                                    print(f"Menu UP via hat -> {self.menu_selected}")
                                elif hy == -1:
                                    self.menu_selected = (self.menu_selected + 1) % opts
                                    self.menu_hat_cooldown = 12
                                    print(f"Menu DOWN via hat -> {self.menu_selected}")
                            if self.menu_mode == 'level' and hx != 0:
                                if hx == -1:
                                    self.menu_selected = (self.menu_selected - 1) % (len(LEVELS)+1)
                                else:
                                    self.menu_selected = (self.menu_selected + 1) % (len(LEVELS)+1)
                                self.menu_hat_cooldown = 8
                            # Reset stuck timer on intentional hat move
                            self.menu_stuck_timer = 0
                except Exception as e:
                    print(f"HAT error {e}")
                    pass

            if event.type == pygame.KEYDOWN:
                # Comprehensive input logging for debug
                try:
                    mods = pygame.key.get_mods()
                    key_name = pygame.key.name(event.key)
                    _log_input("KEYDOWN", device="keyboard", code=key_name, value=float(event.key), mapped_action=f"state={self.state}", extra={"mods": mods, "key": event.key, "unicode": getattr(event, 'unicode', '')})
                except:
                    mods = pygame.key.get_mods()
                # Global fullscreen toggle - works on Mac and Win
                # Mac: Fn+F11, Cmd+F, Cmd+Ctrl+F, Option+Enter, Cmd+Enter
                # F11 / F10 for projector / immersive (need Fn on Mac)
                if event.key in (pygame.K_F11, pygame.K_F10):
                    self.toggle_fullscreen()
                # F alone in menu (easy for Mac)
                if event.key == pygame.K_f and self.state != 'playing':
                    self.toggle_fullscreen()
                # Cmd+F / Ctrl+F for Mac/Win fullscreen (common shortcuts)
                if event.key == pygame.K_f and (mods & pygame.KMOD_META or mods & pygame.KMOD_CTRL):
                    self.toggle_fullscreen()
                # Alt+Enter, Option+Enter (Mac), Cmd+Enter
                if event.key == pygame.K_RETURN and (mods & pygame.KMOD_ALT or mods & pygame.KMOD_META):
                    self.toggle_fullscreen()
                # Cmd+Ctrl+F is standard macOS fullscreen
                if event.key == pygame.K_f and (mods & pygame.KMOD_META and mods & pygame.KMOD_CTRL):
                    self.toggle_fullscreen()
                # ESC in fullscreen first exits fullscreen
                if event.key == pygame.K_ESCAPE and self.is_fullscreen:
                    self.toggle_fullscreen()
                    continue  # skip other ESC handling this frame
                # Global coin keys - work in any state (arcade style)
                if event.key in (pygame.K_c, pygame.K_5):
                    # Insert coin: if gameover, continue; if playing with dead, rejoin
                    if event.key == pygame.K_5:
                        print(f"Coin inserted! Total: {self.coins+1} (+{COIN_LIVES} lives)")
                    self.insert_coin()
                if event.key == pygame.K_j:
                    print("Rescanning joysticks (J pressed)...")
                    self.rescan_joysticks()
                if event.key == pygame.K_i:
                    import game.settings as settings_module
                    # Only toggle RIGHT for now since LEFT is correct per user
                    settings_module.JOYCON_R_INVERT_Y = not getattr(settings_module, 'JOYCON_R_INVERT_Y', True)
                    print(f"RIGHT Joy-Con Invert Y toggled: R {settings_module.JOYCON_R_INVERT_Y} (UP/DOWN) - LEFT stays correct")
                if event.key == pygame.K_u:
                    import game.settings as settings_module
                    settings_module.JOYCON_R_INVERT_X = not getattr(settings_module, 'JOYCON_R_INVERT_X', True)
                    print(f"RIGHT Joy-Con Invert X toggled: R {settings_module.JOYCON_R_INVERT_X} (LEFT/RIGHT)")
                if event.key == pygame.K_o:
                    import game.settings as settings_module
                    settings_module.JOYCON_R_SWAP = not getattr(settings_module, 'JOYCON_R_SWAP', True)
                    print(f"RIGHT Joy-Con Swap toggled: R {settings_module.JOYCON_R_SWAP} (UP/DOWN <-> LEFT/RIGHT)")
                if event.key == pygame.K_k:
                    # Cycle D-pad mapping for Joy-Con L if directions wrong
                    import game.settings as settings_module
                    # Rotate mapping 90 degrees: UP->RIGHT->DOWN->LEFT->UP
                    old_map = settings_module.JOYCON_L_DPAD_MAP.copy()
                    # Simple rotation: each dir moves to next
                    rotation = {'UP':'RIGHT','RIGHT':'DOWN','DOWN':'LEFT','LEFT':'UP'}
                    new_map = {}
                    for btn, dir in old_map.items():
                        new_map[btn] = rotation.get(dir, dir)
                    settings_module.JOYCON_L_DPAD_MAP = new_map
                    print(f"Joy-Con L D-pad map rotated: {new_map} - test UP/DOWN/LEFT/RIGHT again")
                if event.key == pygame.K_1:
                    # P1 start/join
                    if self.state in ('gameover', 'stage_clear') and not self.gameover_won:
                        self.player_join(1)
                    elif self.state == 'playing':
                        # If P1 dead, allow rejoin even without extra coin? Our insert_coin already gives lives, so also allow coin+join in one press
                        if len([p for p in self.players if p.player_id==1 and p.lives<0 and not p.alive])>0:
                            self.insert_coin(1)
                        elif len(self.players)==1 and not any(p.player_id==1 for p in self.players):
                            self.player_join(1)
                if event.key == pygame.K_2:
                    if self.state in ('gameover', 'stage_clear') and not self.gameover_won:
                        self.player_join(2)
                    elif self.state == 'playing':
                        self.player_join(2)

                if self.state == 'menu':
                    if self.menu_mode == 'main':
                        # New navigation: 1P/2P cards are horizontal, so LEFT/RIGHT controls them
                        # Top row: [0:1P left, 1:2P right], then 2:LEVEL SELECT, 3:HOWTO, 4:QUIT below
                        if event.key == pygame.K_UP or event.key == pygame.K_w:
                            # If currently on 1P/2P top row, UP goes to QUIT (wrap) via 4, else normal up
                            if self.menu_selected in (0, 1):
                                # From top row, UP goes to QUIT (bottom)
                                self.menu_selected = 4
                            else:
                                self.menu_selected = (self.menu_selected - 1) % 5
                                # If we land on 1, keep it as is, but if up from LEVEL SELECT (2) should go to last top selected?
                                # We'll keep simple modulo, but avoid jumping from 2 to 1 then immediately requiring LEFT/RIGHT
                                # Actually 2-1=1 gives 2P, which is okay
                            print(f"Menu selected {self.menu_selected} via keyboard UP/W")
                            _trace_log("INPUT", f"Menu UP -> {self.menu_selected}", level="INFO")
                            try:
                                _log_input("MENU_NAV", device="keyboard", code="UP", value=float(self.menu_selected), mapped_action=f"selected={self.menu_selected}")
                            except:
                                pass
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                            if self.menu_selected in (0, 1):
                                # From top row, DOWN goes to LEVEL SELECT
                                self.menu_selected = 2
                            else:
                                self.menu_selected = (self.menu_selected + 1) % 5
                            print(f"Menu selected {self.menu_selected} via keyboard DOWN/S")
                            _trace_log("INPUT", f"Menu DOWN -> {self.menu_selected}", level="INFO")
                            try:
                                _log_input("MENU_NAV", device="keyboard", code="DOWN", value=float(self.menu_selected), mapped_action=f"selected={self.menu_selected}")
                            except:
                                pass
                        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            if self.menu_selected in (0, 1):
                                # Toggle between 1P and 2P horizontally
                                self.menu_selected = 1 if self.menu_selected == 0 else 0
                                print(f"Menu selected {self.menu_selected} via LEFT/A (horizontal 1P<->2P)")
                            else:
                                # For lower options, LEFT does nothing or could go to top row preserving col?
                                # We'll allow LEFT to go to 1P if on lower menu for quick access
                                pass
                            _trace_log("INPUT", f"Menu LEFT -> {self.menu_selected}", level="INFO")
                            try:
                                _log_input("MENU_NAV", device="keyboard", code="LEFT", value=float(self.menu_selected), mapped_action=f"selected={self.menu_selected}")
                            except:
                                pass
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            if self.menu_selected in (0, 1):
                                self.menu_selected = 1 if self.menu_selected == 0 else 0
                                print(f"Menu selected {self.menu_selected} via RIGHT/D (horizontal 1P<->2P)")
                            else:
                                # From lower options, RIGHT could jump to 1P/2P? Let's map RIGHT to 2P quick?
                                pass
                            _trace_log("INPUT", f"Menu RIGHT -> {self.menu_selected}", level="INFO")
                            try:
                                _log_input("MENU_NAV", device="keyboard", code="RIGHT", value=float(self.menu_selected), mapped_action=f"selected={self.menu_selected}")
                            except:
                                pass
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                            print(f"Menu SELECT {self.menu_selected} ENTER/SPACE")
                            self.handle_menu_select()
                        elif event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                    elif self.menu_mode == 'level':
                        opts = len(LEVELS) + 1  # 35 + BACK
                        # paging with left/right for 35 stages (7 pages of 5 etc.)
                        if event.key == pygame.K_UP:
                            self.menu_selected = (self.menu_selected - 1) % opts
                        elif event.key == pygame.K_DOWN:
                            self.menu_selected = (self.menu_selected + 1) % opts
                        elif event.key == pygame.K_LEFT:
                            self.menu_selected = (self.menu_selected - 5) % opts
                        elif event.key == pygame.K_RIGHT:
                            self.menu_selected = (self.menu_selected + 5) % opts
                        elif event.key == pygame.K_PAGEUP:
                            self.menu_selected = max(0, self.menu_selected - 10) % opts
                        elif event.key == pygame.K_PAGEDOWN:
                            self.menu_selected = min(opts-1, self.menu_selected + 10) % opts
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            if self.menu_selected == len(LEVELS):
                                self.menu_mode = 'main'
                                self.menu_selected = 0
                            else:
                                self.current_level = self.menu_selected
                                self.num_players = 1
                                self.init_level(self.current_level, self.num_players)
                        elif event.key == pygame.K_ESCAPE:
                            self.menu_mode = 'main'
                            self.menu_selected = 0
                    elif self.menu_mode == 'howto':
                        if event.key == pygame.K_ESCAPE:
                            self.menu_mode = 'main'
                            self.menu_selected = 0
                elif self.state == 'playing':
                    if event.key == pygame.K_p:
                        _trace_log("KEY", f"P pressed -> paused from playing", with_stack=False)
                        old = self.state
                        self.state = 'paused'
                        _trace_state_change(old, 'paused', 'KEY P pressed')
                        if snd_mgr:
                            snd_mgr.play('pause')
                    elif event.key == pygame.K_m:
                        self.muted = not self.muted
                        # Toggle all sounds + Battle City original had mute for BGM too
                        if snd_mgr:
                            snd_mgr.toggle_mute()
                        print(f"{'🔇 MUTED' if self.muted else '🔊 SOUND ON'} - 35 original NES maps with retro SFX")
                        _trace_log("KEY", f"M muted={self.muted} state={self.state}")
                    elif event.key == pygame.K_ESCAPE:
                        _trace_log("KEY", f"ESC pressed in PLAYING -> will go MENU! mods={mods} is_fullscreen={self.is_fullscreen} key={event.key}", with_stack=True, level="WARN")
                        old = self.state
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                        _trace_state_change(old, 'menu', f"KEY ESC in playing mods={mods}")
                        if snd_mgr:
                            snd_mgr.stop_bgm()
                elif self.state == 'paused':
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        _trace_log("KEY", f"ESC/P in PAUSED -> playing key={event.key} mods={mods}")
                        old = self.state
                        self.state = 'playing'
                        _trace_state_change(old, 'playing', f"KEY {event.key} in paused")
                        if snd_mgr:
                            snd_mgr.play('pause')
                elif self.state in ('gameover', 'stage_clear'):
                    if event.key == pygame.K_RETURN:
                        if self.gameover_won:
                            # next level
                            _trace_log("KEY", f"RETURN in stage_clear -> next level")
                            self.init_next_level()
                        else:
                            # back to menu
                            _trace_log("KEY", f"RETURN in gameover lost -> menu", level="WARN")
                            old = self.state
                            self.state = 'menu'
                            self.menu_mode = 'main'
                            self.menu_selected = 0
                            _trace_state_change(old, 'menu', "KEY RETURN in gameover")
                            # update high score
                            total = sum(p.score for p in self.players)
                            self.high_score = max(self.high_score, total)
                    elif event.key == pygame.K_ESCAPE:
                        _trace_log("KEY", f"ESC in gameover/stage_clear -> menu gameover_won={self.gameover_won}", with_stack=True, level="WARN")
                        old = self.state
                        total = sum(p.score for p in self.players)
                        self.high_score = max(self.high_score, total)
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                        _trace_state_change(old, 'menu', "KEY ESC in gameover/stage_clear")

    def handle_menu_select(self):
        # Clear event queue when starting game to prevent queued UP/DOWN from menu going into game and vice versa
        _trace_log("MENU", f"handle_menu_select called menu_selected={self.menu_selected} menu_mode={self.menu_mode} state={self.state}", with_stack=True)
        try:
            pygame.event.clear()
        except:
            pass
        # Reset stuck timers
        self.menu_stuck_timer = 0
        self.joystick_error_count = 0
        
        if self.menu_selected == 0: # 1P
            print("[Menu] Starting 1P game")
            _trace_log("MENU", "Starting 1P game")
            self.num_players = 1
            self.current_level = 0
            self.init_level(self.current_level, 1)
        elif self.menu_selected == 1: # 2P
            print("[Menu] Starting 2P game")
            _trace_log("MENU", "Starting 2P game")
            self.num_players = 2
            self.current_level = 0
            self.init_level(self.current_level, 2)
        elif self.menu_selected == 2: # level select
            _trace_log("MENU", "Going to level select")
            self.menu_mode = 'level'
            self.menu_selected = 0
        elif self.menu_selected == 3: # how to
            _trace_log("MENU", "Going to howto")
            self.menu_mode = 'howto'
        elif self.menu_selected == 4:
            _trace_log("MENU", "Quit selected -> exit", level="WARN")
            print("[Menu] Quit selected")
            pygame.quit()
            sys.exit()

    def update_playing(self, dt):
        import time as _time
        _update_start = _time.time()
        keys = pygame.key.get_pressed()
        # timers
        if self.tilemap:
            self.tilemap.update(dt)
        if self.freeze_timer > 0:
            self.freeze_timer -= 1

        # Authentic NES tank move sound - continuous rolling for 35 maps
        # Play low engine hum if any tank moving (player or enemy)
        any_moving = any(p.alive for p in self.players) or any(e.alive for e in self.enemies)
        if any_moving and 'move_loop' in getattr(snd_mgr, 'sounds', {}):
            # Randomly also play forest rustle when in forest? Original had none, but for 35 maps we want brick break etc already handled
            pass

        # Tank move sound handled via sound_manager move_loop

        # Powerup 8-bit BGM loop for flashing powerup tank (original Battle City flashes)
        pass

        # spawn enemies - with gradual increase
        self.spawn_timer += 1
        self.difficulty_ramp_timer += 1

        # Gradual ramp within level: every 12 seconds (720 frames), increase max on field and decrease spawn interval
        # This makes enemies come more gradually as time goes on
        if self.difficulty_ramp_timer % (12 * FPS) == 0 and self.difficulty_ramp_timer > 0:
            # Increase max enemies on field by 1 up to 8
            if self.max_enemies_on_field < 8:
                self.max_enemies_on_field += 1
                print(f"[Difficulty] Max enemies on field increased to {self.max_enemies_on_field} (ramp)")
            # Decrease spawn interval by 8 frames (~0.13s) down to 0.8*FPS
            if self.dynamic_spawn_interval > int(0.8 * FPS):
                self.dynamic_spawn_interval = max(int(0.8 * FPS), self.dynamic_spawn_interval - 8)
                print(f"[Difficulty] Spawn interval decreased to {self.dynamic_spawn_interval/FPS:.2f}s (ramp)")

        # Also ramp based on kills: every 5 kills, slightly faster spawn
        if self.enemies_killed > 0 and self.enemies_killed % 5 == 0 and self.spawn_timer == 1:
            # Check if we just killed 5th, 10th, etc. - small extra ramp
            if self.dynamic_spawn_interval > int(1.0 * FPS):
                self.dynamic_spawn_interval = max(int(1.0 * FPS), self.dynamic_spawn_interval - 2)

        # Use dynamic interval
        spawn_interval = getattr(self, 'dynamic_spawn_interval', ENEMY_SPAWN_INTERVAL)
        if self.spawn_timer >= spawn_interval:
            self.spawn_enemy()
            self.spawn_timer = 0
        # initial fast spawns - use dynamic max
        max_on_field = getattr(self, 'max_enemies_on_field', MAX_ENEMIES_ON_FIELD)
        if self.enemies_spawned < max_on_field and self.spawn_timer % 30 == 0:
            self.spawn_enemy()

        # players
        all_tanks_for_collision = self.enemies.copy()
        # Smart Joy-Con handling for 2P: if we have 1 combined Joy-Con (L/R) with 6 axes, split it
        # P1 uses left stick (axes 0,1) and left buttons, P2 uses right stick (axes 2,3) and right buttons
        combined_joycon = None
        if len(self.joysticks) == 1:
            try:
                name = self.joysticks[0].get_name().lower()
                if 'l/r' in name or ('joy-con' in name and self.joysticks[0].get_numaxes() >= 4):
                    combined_joycon = self.joysticks[0]
            except:
                pass

        # Check for remote P2 input via LAN
        remote_p2 = None
        if self.network_host:
            try:
                # Auto-join remote P2 if client connected and we have only 1 player
                if self.network_host.is_client_connected() and len(self.players) == 1:
                    # Check if P2 doesn't already exist
                    if not any(p.player_id == 2 for p in self.players):
                        print("[Network] Remote P2 joining via LAN!")
                        # Spawn P2 at its spawn point
                        gx, gy = PLAYER_SPAWN[1]
                        p2 = PlayerTank(2, gx, gy, lives=3)
                        p2.score = 0
                        self.players.append(p2)
                        self.num_players = 2
                        self.particles.add_spawn(p2.rect.centerx, p2.rect.centery)
                        # Ensure P2 has lives
                        if p2.lives < 0:
                            p2.lives = 3
                if len(self.players) >= 2:
                    remote_p2 = self.network_host.get_remote_p2_input()
            except Exception as e:
                # print(f"Network check error: {e}")
                remote_p2 = None

        for i, p in enumerate(self.players):
            if not p.alive:
                continue
            # If this is P2 and remote input is active, use remote input instead of local joystick
            if p.player_id == 2 and remote_p2 and (remote_p2.get("dir") or remote_p2.get("shoot")):
                # Remote P2 input from LAN
                other_tanks = self.enemies + [op for j, op in enumerate(self.players) if j != i]
                r_dir = remote_p2.get("dir")
                r_shoot = remote_p2.get("shoot", False)
                if r_dir:
                    p.direction = r_dir
                    p.try_move(r_dir, self.tilemap, other_tanks)
                if r_shoot:
                    b = p.shoot()
                    if b:
                        if isinstance(b, list):
                            self.bullets.extend(b)
                        else:
                            self.bullets.append(b)
                p.update(self.tilemap, other_tanks)
                continue

            # get joystick for this player - with combined Joy-Con split support
            js = None
            if combined_joycon and len(self.players) == 2:
                # Both players share the combined Joy-Con, but we pass same object and let player.py handle left/right split
                # We pass a tuple indicating player side for split logic
                js = combined_joycon
                # For split, we will have special handling inside player.py via player_id
            else:
                js = self.joysticks[i] if i < len(self.joysticks) else None

            other_tanks = self.enemies + [op for j, op in enumerate(self.players) if j != i]
            # snapshot enemy count before move for crush detection
            enemies_before = len([e for e in self.enemies if e.alive])
            b = p.handle_input(keys, js, self.tilemap, other_tanks, num_players=len(self.players))
            if b:
                if isinstance(b, list):
                    self.bullets.extend(b)
                else:
                    self.bullets.append(b)
            p.update(self.tilemap, other_tanks)
            # giant crush detection - if giant killed enemies by running over
            if getattr(p, 'is_giant', False):
                # check for crushed bricks under player for particles
                gx = int((p.rect.centerx - PLAYFIELD_X) // TILE_SIZE)
                gy = int((p.rect.centery - PLAYFIELD_Y) // TILE_SIZE)
                # brick crush particles handled in tank.py but add extra visual
                if random.random() < 0.3:
                    self.particles.add_crush(p.rect.centerx + random.randint(-8,8), p.rect.centery + random.randint(-8,8))
                # detect crushed enemies
                enemies_now = [e for e in self.enemies if e.alive]
                if len(enemies_now) < enemies_before:
                    self.particles.add_explosion(p.rect.centerx, p.rect.centery, (255,80,80), 15)

        # enemies
        players_list = self.players
        for e in self.enemies:
            if self.freeze_timer > 0:
                # frozen: don't move/shoot, but remain attackable (fix bug where freeze made enemies invincible)
                # Previously set invulnerable_timer=1 which made them unattackable during freeze - removed
                # Update timers manually (since we skip update_ai which would call super().update)
                if e.cooldown > 0:
                    e.cooldown -= 1
                if e.invulnerable_timer > 0:
                    e.invulnerable_timer -= 1
                if e.spawn_protection > 0:
                    e.spawn_protection -= 1
                e.cooldown = max(e.cooldown, 1)  # prevent shooting while frozen
                e.flash_timer += 1
                # Clean own bullets list
                e.bullets = [b for b in e.bullets if b.alive]
                # Still vulnerable - do NOT set invulnerable_timer
                continue
            e.update_ai(self.tilemap, players_list, self.enemies, self.bullets, self.base)

        # bullets update
        for b in self.bullets[:]:
            if not b.alive:
                continue
            all_tanks = self.players + self.enemies
            result = b.update(self.tilemap, all_tanks, self.base)
            if result:
                try:
                    _log_gameplay(f"BULLET_{result.upper()}", level_idx=self.current_level, data={"x": b.x, "y": b.y, "owner": b.owner, "type": getattr(b, 'bullet_type', 'unknown'), "power": b.power})
                except:
                    pass
                if result in ('hit_brick', 'hit_steel'):
                    self.particles.add_hit(b.x, b.y)
                elif result == 'hit_tank':
                    self.particles.add_explosion(b.x, b.y, (255, 150, 0), 12)
                elif result == 'hit_base':
                    self.particles.add_explosion(b.x, b.y, (255, 50, 50), 25)
                elif result == 'out_of_fuel':
                    self.particles.add_explosion(b.x, b.y, (120, 120, 120), 10)
                    self.particles.add_hit(b.x, b.y)
                elif result == 'venom_hit':
                    self.particles.add_venom(b.x, b.y)
                    self.particles.add_explosion(b.x, b.y, (80, 200, 80), 12)

        # === Bullet vs Bullet counter: player can counter enemy bullets ===
        if BULLET_COUNTER_ENABLED:
            # Only check player bullets vs enemy/boss bullets
            player_bullets = [b for b in self.bullets if b.alive and b.owner.startswith('player')]
            enemy_bullets = [b for b in self.bullets if b.alive and (b.owner == 'enemy' or b.owner == 'boss')]
            for pb in player_bullets:
                if not pb.alive:
                    continue
                for eb in enemy_bullets:
                    if not eb.alive:
                        continue
                    # Don't counter venom with normal? Allow but venom is stronger - player needs power>=2 to counter venom
                    if getattr(eb, 'venom', False) and pb.power < 2:
                        continue
                    dist = math.hypot(pb.x - eb.x, pb.y - eb.y)
                    if dist < (BULLET_SIZE + 3):  # direct hit
                        # Both explode
                        pb.alive = False
                        eb.alive = False
                        self.particles.add_explosion((pb.x+eb.x)/2, (pb.y+eb.y)/2, (255, 220, 80), 10)
                        self.particles.add_hit(pb.x, pb.y)
                        # sound
                        try:
                            if snd_mgr:
                                snd_mgr.play_hit_steel()
                        except:
                            pass
                        break  # this player bullet destroyed, go next

        # cleanup dead bullets
        self.bullets = [b for b in self.bullets if b.alive]

        # check player-enemy collision damage? Touch doesn't kill, but bullets do. However spawn protection collisions blocked in movement.

        # powerups - authentic Battle City powerup appear sound when enemy carrier killed (35 maps same)
        for pu in self.powerups[:]:
            pu.update()
            picker = pu.check_pickup(self.players)
            if picker:
                try:
                    _log_gameplay("POWERUP_PICK", level_idx=self.current_level, player_id=getattr(picker, 'player_id', None), data={"type": pu.type, "x": pu.x, "y": pu.y})
                except:
                    pass
                self.apply_powerup(pu.type, picker)
                if snd_mgr:
                    snd_mgr.play_powerup_pick()
                    if pu.type == 'grenade':
                        snd_mgr.play_explosion(big=True)
                self.particles.add_explosion(pu.x, pu.y, (100,255,100), 15)
            if not pu.alive:
                self.powerups.remove(pu)

        # venom particles for affected players
        for p in self.players:
            if p.alive and getattr(p, 'venom_timer', 0) > 0:
                if random.random() < 0.4 + getattr(p, 'venom_level', 0)*0.6:
                    self.particles.add_venom(p.rect.centerx + random.randint(-10,10), p.rect.centery + random.randint(-10,10))

        # particles
        self.particles.update()

        # handle dead enemies -> score, spawn powerup chance, count (with explosion sound)
        for e in self.enemies[:]:
            if not e.alive:
                # score
                killer_id = None
                if self.players:
                    alive_ps = [p for p in self.players if p.alive] or self.players
                    killer = min(alive_ps, key=lambda p: math.hypot(p.x - e.x, p.y - e.y)) if alive_ps else self.players[0]
                    killer.score += e.score_value
                    killer_id = getattr(killer, 'player_id', None)
                self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 25)
                # Authentic NES explosion SFX - varies by enemy type
                if snd_mgr:
                    snd_mgr.play_explosion(big=(e.enemy_type=='armor'))
                try:
                    _log_gameplay("ENEMY_KILL", level_idx=self.current_level, player_id=killer_id, data={"enemy_type": getattr(e, 'enemy_type', 'unknown'), "x": e.x, "y": e.y, "carrier": e.powerup_carrier, "score_value": e.score_value, "killed": self.enemies_killed+1, "total": self.enemies_total})
                except:
                    pass
                # powerup spawn if carrier - play appear jingle (authentic 8-bit)
                if e.powerup_carrier:
                    pu = PowerUp(e.rect.centerx, e.rect.centery)
                    self.powerups.append(pu)
                    if snd_mgr:
                        snd_mgr.play_powerup_appear()
                    try:
                        _log_gameplay("POWERUP_SPAWN", level_idx=self.current_level, data={"type": pu.type, "x": pu.x, "y": pu.y, "from": "enemy_carrier"})
                    except:
                        pass
                self.enemies.remove(e)
                self.enemies_killed += 1

        # handle dead players respawn or game over - fixed bug where boss camping spawn blocked respawn
        # Previously: only respawned if can_spawn True, so if boss near spawn, player stayed dead and couldn't move
        # Now: always respawn, clear area, and give extra protection if blocked - fixes "cannot move after killed by boss"
        all_dead = True
        spawns = MEGA_PLAYER_SPAWN if self.is_mega else PLAYER_SPAWN
        ts = MEGA_TILE_SIZE if self.is_mega else TILE_SIZE
        for p in self.players:
            if p.alive:
                all_dead = False
            else:
                if p.lives >= 0:
                    gx, gy = spawns[p.player_id-1]
                    # Always clear area around spawn to prevent boss camping
                    try:
                        self.tilemap.clear_area(gx-1, gy-1, 4, 4)
                    except:
                        pass
                    # Check if still blocked (for extra protection)
                    can_spawn = True
                    test_rect = pygame.Rect(PLAYFIELD_X+gx*ts, PLAYFIELD_Y+gy*ts, TANK_SIZE, TANK_SIZE)
                    for en in self.enemies:
                        if en.alive and test_rect.colliderect(en.rect):
                            can_spawn = False
                            # Push blocking enemy slightly away to unblock
                            try:
                                # Push enemy away from spawn point
                                dx = en.x - (PLAYFIELD_X+gx*ts+ts*2)
                                dy = en.y - (PLAYFIELD_Y+gy*ts+ts*2)
                                dist = max(1, (dx*dx+dy*dy)**0.5)
                                en.x += dx/dist * 8
                                en.y += dy/dist * 8
                                en.rect.center = (en.x, en.y)
                            except:
                                pass
                    p.respawn(gx, gy)
                    if not can_spawn:
                        # Extra protection if spawned in previously blocked area (e.g., boss near spawn)
                        p.spawn_protection = 300
                        p.invulnerable_timer = 180
                    all_dead = False

        # base/monster hit? New logic: monster base hit releases boss instead of immediate game over
        if not self.base.alive:
            # If monster was just hit and boss not yet released, release boss
            if getattr(self.base, 'monster_released', False) and not self.boss_released:
                self.release_monster_boss()
                # Don't game over yet - boss fight begins
                # Clear base area already done in release
            elif self.boss_released:
                # Boss fight ongoing or finished
                if self.boss_enemy and self.boss_enemy.alive:
                    # Boss still alive - continue fight, don't game over
                    # Decrement boss fight timer
                    if self.boss_fight_timer > 0:
                        self.boss_fight_timer -= 1
                    # If timer expires and boss still alive, game over (monster escaped)
                    # For now, allow unlimited time, just continue
                    pass
                else:
                    # Boss was released and now dead - player defeated boss!
                    # Allow multiple boss releases: each time boss is defeated, respawn base with bonus and reset for next release
                    print("[BOSS] Monster boss defeated! Respawning base with bonus!")
                    # Bonus for defeating boss
                    for p in self.players:
                        if p.alive:
                            p.score += 3000
                    # Respawn base with steel walls as reward
                    self.base.reset()
                    self.tilemap.build_base_walls(TILE_STEEL)
                    # Give base temporary shield
                    try:
                        self.base.shield_timer = 10 * FPS
                    except:
                        pass
                    self.boss_enemy = None
                    self.boss_fight_timer = 0
                    self.boss_released = False  # allow next boss release on next base hit
                    self.monster_boss_defeated = True  # track at least one defeat
                    # Continue game
                    self.particles.add_explosion(self.base.rect.centerx, self.base.rect.centery, (100,255,100), 40)
                    if snd_mgr:
                        snd_mgr.play_powerup_appear()
                        snd_mgr.play_stage_clear()
                    # Don't game over, continue
            else:
                # Original game over logic for non-monster base (fallback)
                if self.state != 'gameover':
                    _trace_log("GAMEOVER", f"Base destroyed fallback -> gameover old_state={self.state} base_alive={self.base.alive} boss_released={self.boss_released}", with_stack=True, level="ERROR")
                    old = self.state
                    self.continue_timer = CONTINUE_TIME
                    if snd_mgr:
                        snd_mgr.play_explosion(big=True)
                        snd_mgr.play_game_over()
                    self._on_game_over()
                    self.state = 'gameover'
                    self.gameover_won = False
                    _trace_state_change(old, 'gameover', "BASE_DESTROYED_FALLBACK")
                else:
                    self.state = 'gameover'
                    self.gameover_won = False
                return

        # check if all players out of lives and dead
        if all_dead and all(p.lives < 0 for p in self.players):
            if self.state != 'gameover':
                _trace_log("GAMEOVER", f"All players dead -> gameover all_dead={all_dead} lives={[p.lives for p in self.players]}", with_stack=True, level="WARN")
                old = self.state
                self.continue_timer = CONTINUE_TIME
                if snd_mgr:
                    snd_mgr.play_game_over()
                self._on_game_over()
                self.state = 'gameover'
                self.gameover_won = False
                _trace_state_change(old, 'gameover', "ALL_PLAYERS_DEAD")
            else:
                self.state = 'gameover'
                self.gameover_won = False
            return

        # win condition - stage clear with authentic NES jingle (35 maps loop)
        if self.enemies_killed >= self.enemies_total and len(self.enemies) == 0:
            _trace_log("STAGE", f"Stage clear! level={self.current_level} killed={self.enemies_killed} total={self.enemies_total}")
            old = self.state
            self.state = 'stage_clear'
            self.gameover_won = True
            _trace_state_change(old, 'stage_clear', f"stage {self.current_level} cleared")
            if snd_mgr:
                snd_mgr.play_stage_clear()
            # Log 35-stage progress
            print(f"[Stage] Stage {self.current_level+1}/35 cleared! Authentic Battle City.")
            for p in self.players:
                if p.alive:
                    p.score += 1000 + (self.current_level+1)*200
            return

    def apply_powerup(self, pu_type, player):
        if pu_type == 'helmet':
            player.apply_powerup('helmet', self)
        elif pu_type == 'clock':
            self.freeze_timer = POWERUP_DURATION['clock']
        elif pu_type == 'shovel':
            player.apply_powerup('shovel', self)
        elif pu_type == 'star':
            player.apply_powerup('star', self)
        elif pu_type == 'tank':
            player.apply_powerup('tank', self)
        elif pu_type == 'grenade':
            # NEW: Bomb does armor damage, only explodes if no armor left (user request)
            # Previously it killed all enemies directly - now it causes BOMB_ARMOR_DAMAGE to armor
            # If armor depleted, enemy explodes
            try:
                bomb_armor_dmg = BOMB_ARMOR_DAMAGE
                bomb_power = BOMB_POWER_DAMAGE
            except NameError:
                bomb_armor_dmg = 100
                bomb_power = 2
            bomb_kills = 0
            bomb_hits = 0
            for e in self.enemies[:]:
                if not e.alive:
                    continue
                bomb_hits += 1
                # Apply armor damage
                if hasattr(e, 'armor'):
                    # Reduce armor
                    old_armor = e.armor
                    e.armor = max(0, e.armor - bomb_armor_dmg)
                    e.armor_flash_timer = 20
                    # Log
                    try:
                        _log_gameplay("BOMB_HIT", level_idx=self.current_level, data={"enemy_type": getattr(e, 'enemy_type', 'unknown'), "old_armor": old_armor, "new_armor": e.armor, "x": e.x, "y": e.y})
                    except:
                        pass
                    # If no armor left, explode
                    if e.armor <= 0:
                        # Check if enemy already had no armor before bomb, or now depleted
                        # If armor was >0 before and now 0, we consider it should explode if health low, or need extra power?
                        # User says: if enemy has no armor left, it can explode
                        # So: if armor <=0, kill enemy
                        e.alive = False
                        self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 25)
                        player.score += e.score_value
                        bomb_kills += 1
                        try:
                            _log_gameplay("BOMB_KILL", level_idx=self.current_level, data={"enemy_type": getattr(e, 'enemy_type', 'unknown'), "score": e.score_value})
                        except:
                            pass
                    else:
                        # Survives with reduced armor - show hit effect but not full explosion
                        self.particles.add_explosion(e.rect.centerx, e.rect.centery, (255, 150, 0), 8)
                        self.particles.add_hit(e.x, e.y)
                else:
                    # No armor attribute - fallback to old health damage logic
                    # If enemy has health > bomb_power, reduce health, else kill
                    if hasattr(e, 'health'):
                        e.health -= bomb_power
                        if e.health <= 0:
                            e.alive = False
                            self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 20)
                            player.score += e.score_value
                            bomb_kills += 1
                        else:
                            self.particles.add_hit(e.x, e.y)
                    else:
                        # No health either - kill
                        e.alive = False
                        self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 20)
                        player.score += e.score_value
                        bomb_kills += 1
            # Log overall bomb usage
            try:
                _trace_log("POWERUP", f"Bomb used by {getattr(player, 'player_id', '?')} hits={bomb_hits} kills={bomb_kills} dmg={bomb_armor_dmg} level={self.current_level}", level="INFO")
                _log_gameplay("BOMB_USE", level_idx=self.current_level, player_id=getattr(player, 'player_id', None), data={"hits": bomb_hits, "kills": bomb_kills, "armor_dmg": bomb_armor_dmg, "power_dmg": bomb_power})
            except:
                pass
            # they will be counted next update as killed (if they died)
        elif pu_type == 'gun':
            player.bullet_power = 2
            player.cooldown = 0
        elif pu_type == 'homing':
            player.apply_powerup('homing', self)
        elif pu_type == 'spread':
            player.apply_powerup('spread', self)
        elif pu_type == 'rapid':
            player.apply_powerup('rapid', self)
        elif pu_type == 'shrink':
            player.apply_powerup('shrink', self)
            self.particles.add_explosion(player.rect.centerx, player.rect.centery, (80, 220, 255), 12)
            try:
                # shrink sound - use powerup appear + pitch?
                if snd_mgr:
                    snd_mgr.play_powerup_appear()
            except:
                pass
        elif pu_type == 'giant':
            player.apply_powerup('giant', self)
            self.particles.add_explosion(player.rect.centerx, player.rect.centery, (255, 80, 80), 18)
            try:
                if snd_mgr:
                    snd_mgr.play_powerup_appear()
            except:
                pass

    def draw(self):
        # Create canvas at original resolution for consistent drawing and easy scaling to fullscreen
        # This fixes "content not zoomed" issue when in fullscreen with (0,0) mode
        canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        if self.state == 'menu':
            self.hud.draw_menu(canvas, self.menu_selected, self.menu_mode)
        elif self.state in ('playing', 'paused', 'gameover', 'stage_clear'):
            # bg
            canvas.fill(COLOR_BG)
            # playfield border
            border_rect = pygame.Rect(PLAYFIELD_X-4, PLAYFIELD_Y-4, PLAYFIELD_W+8, PLAYFIELD_H+8)
            pygame.draw.rect(canvas, (70,70,90), border_rect, border_radius=6)
            # tilemap
            self.tilemap.draw(canvas)
            # base
            self.base.draw(canvas)
            # tanks - pass tilemap for forest hiding (player faintly visible, enemies completely hidden)
            for e in self.enemies:
                e.draw(canvas, tilemap=self.tilemap)
            for p in self.players:
                p.draw(canvas, tilemap=self.tilemap)
            # bullets
            for b in self.bullets:
                b.draw(canvas)
            # powerups
            for pu in self.powerups:
                pu.draw(canvas)
            # overlay tiles (grass) - dense forest that completely hides tanks underneath
            self.tilemap.draw_overlay(canvas)
            # Player forest visibility hint - draw faint silhouette of player tanks that are in forest AFTER overlay
            # So player gets 15-20% visibility while enemies stay fully hidden
            for p in self.players:
                if p.alive and self.tilemap.is_in_forest(p.x, p.y):
                    p.draw_forest_hint(canvas)
            # particles top
            self.particles.draw(canvas)

            # HUD
            self.hud.draw(canvas, self)

            if self.state == 'paused':
                self.hud.draw_pause(canvas)
            elif self.state in ('gameover', 'stage_clear'):
                total_score = sum(p.score for p in self.players)
                self.hud.draw_game_over(canvas, self.gameover_won, total_score, self)

        # Now blit canvas to screen with scaling if fullscreen
        # This ensures content is zoomed to fill fullscreen, not just small in corner
        if self.is_fullscreen:
            # Scale canvas to fullscreen size (e.g., 960x720 -> 1920x1080) - zoomed
            try:
                scaled = pygame.transform.scale(canvas, self.screen.get_size())
                self.screen.blit(scaled, (0, 0))
            except Exception:
                # Fallback: centered blit without scaling if scale fails
                self.screen.fill(COLOR_BG)
                self.screen.blit(canvas, ((self.screen.get_width()-SCREEN_WIDTH)//2, (self.screen.get_height()-SCREEN_HEIGHT)//2))
        else:
            # Windowed: direct blit (no scaling needed, same size)
            self.screen.blit(canvas, (0, 0))

        # Projector: update frame for network projector view (http://host_ip:8080)
        # Use canvas (original res) for consistent quality
        try:
            from .projector import update_frame
            update_frame(canvas)
        except Exception:
            pass

        pygame.display.flip()

    def run(self):
        import traceback
        import time as _time
        crash_count = 0
        last_perf_log = _time.time()
        fps_counter = 0
        # For perf measurement
        _last_update_ms = 0
        _last_draw_ms = 0
        while True:
            try:
                frame_start = _time.time()
                dt = self.clock.tick(FPS)
                # Increment frame in debug logger
                try:
                    if HAS_DEBUG_LOGGER:
                        debug_logger.increment_frame()
                except:
                    pass
                self.handle_events()

                # LAN Remote P2 auto-join from menu - if remote client connected while in menu, auto-start 2P
                if self.state == 'menu' and self.network_host and self.network_host.is_client_connected():
                    # If menu is in main mode and 1P is selected or no game yet, auto-start 2P with original maps
                    if self.menu_mode == 'main':
                        _trace_log("NETWORK", f"Remote P2 detected in menu -> auto-starting 2P! state={self.state} mode={self.menu_mode}", with_stack=True)
                        print("[Network] Remote P2 detected in menu - auto-starting 2P with original NES maps!")
                        self.num_players = 2
                        self.current_level = 0
                        self.init_level(self.current_level, 2)
                        # Reset boss flags for new game
                        self.boss_released = False
                        self.boss_enemy = None

                if self.state == 'playing':
                    try:
                        update_start = _time.time()
                        self.update_playing(dt)
                        # store update ms for perf log in outer scope
                        try:
                            _last_update_ms = (_time.time() - update_start) * 1000
                        except:
                            pass
                    except Exception as e:
                        _trace_log("CRASH", f"update_playing failed: {e} crash_count={crash_count} level={self.current_level} players={[ (p.alive, p.lives, p.x, p.y) for p in self.players]} enemies={len(self.enemies)} bullets={len(self.bullets)}", with_stack=True, level="ERROR")
                        try:
                            _log_crash("Game.update_playing", e, extra={"level": self.current_level, "players": [(p.alive, p.lives) for p in self.players], "enemies": len(self.enemies), "crash_count": crash_count})
                        except:
                            pass
                        print(f"[CRASH GUARD] update_playing failed: {e}")
                        traceback.print_exc()
                        crash_count += 1
                        if crash_count > 10:
                            _trace_log("CRASH", f"Too many crashes ({crash_count}) in update_playing -> forcing MENU! state={self.state}", with_stack=True, level="ERROR")
                            print("Too many crashes, returning to menu")
                            old = self.state
                            self.state = 'menu'
                            self.menu_mode = 'main'
                            _trace_state_change(old, 'menu', f"CRASH_GUARD update_playing {crash_count} crashes")
                            crash_count = 0
                elif self.state == 'gameover' and not self.gameover_won:
                    # Countdown to menu if no coin inserted
                    if self.continue_timer > 0:
                        self.continue_timer -= 1
                        # Also update particles for effect
                        try:
                            self.particles.update()
                        except:
                            pass
                        if self.continue_timer % 60 == 0:
                            _trace_log("GAMEOVER", f"Continue timer countdown {self.continue_timer//FPS}s remaining state={self.state}")
                    else:
                        # Time out -> go to menu
                        _trace_log("GAMEOVER", f"Continue timer expired -> going MENU from gameover timer=0", with_stack=True, level="WARN")
                        old = self.state
                        total = sum(p.score for p in self.players)
                        self.high_score = max(self.high_score, total)
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                        _trace_state_change(old, 'menu', "GAMEOVER timer expired")
                try:
                    draw_start = _time.time()
                    self.draw()
                    _last_draw_ms = (_time.time() - draw_start) * 1000
                except Exception as e:
                    _trace_log("CRASH", f"draw failed: {e} crash_count={crash_count} state={self.state}", with_stack=True, level="ERROR")
                    try:
                        _log_crash("Game.draw", e, extra={"state": self.state, "crash_count": crash_count, "level": self.current_level})
                    except:
                        pass
                    print(f"[CRASH GUARD] draw failed: {e}")
                    traceback.print_exc()
                    crash_count += 1
                    if crash_count > 10:
                        _trace_log("CRASH", f"Too many draw crashes ({crash_count}) -> forcing MENU", with_stack=True, level="ERROR")
                        old = self.state
                        self.state = 'menu'
                        _trace_state_change(old, 'menu', f"CRASH_GUARD draw {crash_count} crashes")
                        crash_count = 0

                # Perf logging every ~0.5 sec
                try:
                    if HAS_DEBUG_LOGGER and _time.time() - last_perf_log > 0.5:
                        fps = self.clock.get_fps()
                        debug_logger.log_perf(fps=fps, dt_ms=dt, update_ms=_last_update_ms, draw_ms=_last_draw_ms,
                                              enemies_count=len(self.enemies), bullets_count=len(self.bullets),
                                              particles_count=len(self.particles.particles) + len(self.particles.explosions),
                                              players_alive=len([p for p in self.players if p.alive]))
                        last_perf_log = _time.time()
                except:
                    pass

            except SystemExit:
                _trace_log("EXIT", "SystemExit raised, exiting", with_stack=True)
                try:
                    if HAS_DEBUG_LOGGER:
                        debug_logger.end_session()
                except:
                    pass
                raise
            except Exception as e:
                _trace_log("CRASH", f"main loop failed: {e} crash_count={crash_count} state={self.state}", with_stack=True, level="ERROR")
                try:
                    _log_crash("Game.run main loop", e, extra={"state": self.state, "crash_count": crash_count})
                except:
                    pass
                print(f"[CRASH GUARD] main loop failed: {e}")
                traceback.print_exc()
                crash_count += 1
                if crash_count > 20:
                    _trace_log("CRASH", f"Too many main loop crashes {crash_count} -> exit", level="ERROR")
                    print("Too many crashes in main loop, exiting")
                    break

    async def run_async(self):
        """Async version for web (Pygbag) - same as run() but with await asyncio.sleep(0) to yield to browser"""
        import asyncio
        import traceback
        import time as _time
        crash_count = 0
        last_perf_log = _time.time()
        print("[Game] Starting async web loop (is_web=True) - controls: WASD+SPACE, Arrows+Enter, Gamepad")
        while True:
            try:
                frame_start = _time.time()
                dt = self.clock.tick(FPS)
                try:
                    if HAS_DEBUG_LOGGER:
                        debug_logger.increment_frame()
                except:
                    pass
                self.handle_events()

                if self.state == 'playing':
                    try:
                        self.update_playing(dt)
                    except Exception as e:
                        print(f"[CRASH GUARD] update_playing failed (async): {e}")
                        traceback.print_exc()
                        crash_count += 1
                        if crash_count > 10:
                            print("Too many crashes, returning to menu")
                            self.state = 'menu'
                            self.menu_mode = 'main'
                            crash_count = 0

                elif self.state == 'gameover' and not self.gameover_won:
                    if self.continue_timer > 0:
                        self.continue_timer -= 1
                        try:
                            self.particles.update()
                        except:
                            pass
                    else:
                        total = sum(p.score for p in self.players)
                        self.high_score = max(self.high_score, total)
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0

                try:
                    self.draw()
                except Exception as e:
                    print(f"[CRASH GUARD] draw failed (async): {e}")
                    traceback.print_exc()
                    crash_count += 1
                    if crash_count > 10:
                        self.state = 'menu'
                        crash_count = 0

                # Yield to browser event loop - crucial for web
                await asyncio.sleep(0)

            except SystemExit:
                raise
            except Exception as e:
                print(f"[CRASH GUARD] async main loop failed: {e}")
                traceback.print_exc()
                crash_count += 1
                if crash_count > 20:
                    print("Too many crashes in async loop, exiting")
                    break
                await asyncio.sleep(0.1)
