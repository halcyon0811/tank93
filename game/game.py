"""Main Game class - handles states, spawner, collisions"""
import pygame
import random
import math
import sys
from .settings import *
from .tilemap import TileMap, LEVELS
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
    def __init__(self):
        # Fix macOS IMK crash "error messaging the mach port for IMKCFRunLoopWakeUpReliable"
        # and libpng iCCP warning - set env before init
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
            # Sort L/R for consistent 2P assignment fix
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

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank 93 Enhanced - Battle City Tribute")
        self.clock = pygame.time.Clock()
        self.hud = HUD()

        self.state = 'menu'  # menu, playing, paused, gameover, stage_clear
        self.menu_selected = 0
        self.menu_mode = 'main'  # main, level, howto
        self.num_players = 1
        self.current_level = 0
        self.high_score = 0

        # gameplay vars inited later
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

        # Arcade Coin System
        self.coins = 0  # total coins inserted
        self.coins_total = 0  # for stats
        self.continue_timer = 0  # countdown when gameover
        self.credits = {1: 0, 2: 0}  # per player credits, each coin gives COIN_LIVES

    def _get_enemy_queue_for_level(self, level_idx):
        """Return authentic enemy queue if available, else generate fallback."""
        lvl = level_idx % len(LEVELS)
        if ENEMY_QUEUES_ORIGINAL and lvl < len(ENEMY_QUEUES_ORIGINAL):
            return list(ENEMY_QUEUES_ORIGINAL[lvl])  # copy
        # fallback: random weighted
        return None

    def _get_enemies_total_for_level(self, level_idx):
        lvl = level_idx % len(LEVELS)
        if ENEMY_QUEUES_ORIGINAL and lvl < len(ENEMY_QUEUES_ORIGINAL):
            return len(ENEMY_QUEUES_ORIGINAL[lvl])
        return ENEMIES_PER_LEVEL + lvl * 2

    def init_level(self, level_idx, num_players=1):
        self.current_level = level_idx % len(LEVELS)
        level_data = LEVELS[self.current_level]
        self.tilemap = TileMap(level_data)
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

        # players
        for i in range(num_players):
            gx, gy = PLAYER_SPAWN[i]
            p = PlayerTank(i+1, gx, gy)
            self.players.append(p)

        self.enemies_total = self._get_enemies_total_for_level(self.current_level)
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        # Monster boss system
        self.boss_enemy = None
        self.boss_released = False
        self.boss_fight_timer = 0
        self.monster_boss_defeated = False
        self.state = 'playing'
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
        self.current_level = (self.current_level + 1) % len(LEVELS)
        level_data = LEVELS[self.current_level]
        self.tilemap = TileMap(level_data)
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
        # Monster boss system - reset per level
        self.boss_enemy = None
        self.boss_released = False
        self.boss_fight_timer = 0
        self.monster_boss_defeated = False
        # respawn players at start with protections - preserve items across stages
        new_players = []
        for i, old_p in enumerate(prev_players):
            gx, gy = PLAYER_SPAWN[i]
            p = PlayerTank(old_p.player_id, gx, gy)
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
        if len(self.enemies) >= MAX_ENEMIES_ON_FIELD:
            return
        # find spawn point that is not blocked - improved to prevent enemy stuck bug
        # Previous logic only checked exact spawn rect overlap, but after first enemy moves slightly (36px),
        # second could spawn too close and cause stuck when they overlap exactly.
        # Now we check distance > TANK_SIZE*1.8 to ensure separation and avoid deadlock where
        # two enemies occupy same spot and block each other's movement forever.
        tries = 0
        while tries < 30:
            sx, sy = random.choice(ENEMY_SPAWNS)
            # check if occupied - more robust
            blocked = False
            spawn_cx = PLAYFIELD_X + sx * TILE_SIZE + TILE_SIZE//2
            spawn_cy = PLAYFIELD_Y + sy * TILE_SIZE + TILE_SIZE//2
            test_rect = pygame.Rect(PLAYFIELD_X + sx*TILE_SIZE, PLAYFIELD_Y + sy*TILE_SIZE, TANK_SIZE, TANK_SIZE)
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
                enemy = EnemyTank(sx, sy, etype)
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
                break
            tries+=1

    def release_monster_boss(self):
        """Called when monster base is hit - releases monster as enemy boss tank"""
        if self.boss_released:
            return  # already released
        print("[BOSS] Monster released! Spawning boss tank!")
        self.boss_released = True
        self.boss_fight_timer = 15 * FPS  # 15 seconds to kill boss before game over? Or just track
        # Spawn boss at base position
        bx, by = BASE_POS
        # Clear area around base for boss spawn
        self.tilemap.clear_area(bx-1, by-1, 4, 4)
        from .entities.enemy import EnemyTank
        boss = EnemyTank(bx, by, 'monster_boss')
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
            except:
                pass
        except Exception as e:
            print(f"Rescan failed: {e}")

    def handle_events(self):
        try:
            events = pygame.event.get()
        except SystemError as e:
            # Pygame can throw SystemError: KeyError inside event.get() when a virtual joystick is broken
            # Workaround: log and try to recover without disabling all joysticks permanently
            print(f"Joystick event error (recovering): {e}")
            try:
                pygame.event.clear()
                events = pygame.event.get()
            except:
                events = []
                # As last resort, block only motion events which are spammy, keep button events for Joy-Con
                try:
                    pygame.event.set_blocked(pygame.JOYAXISMOTION)
                    pygame.event.set_blocked(pygame.JOYBALLMOTION)
                except:
                    pass
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
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
                    # Coin: Minus button 8 on Switch, Select/View on Xbox/PS (6,8)
                    if event.button in (8, 6):  # Minus / Select / View = Coin
                        self.insert_coin(joy_player_id)
                    # allow menu navigation with controller
                    if self.state == 'menu':
                        if event.button in (0, 1, 9):  # A/B/Plus
                            self.handle_menu_select()
                    elif self.state in ('gameover', 'stage_clear'):
                        if event.button in (0, 9):  # A / Plus = Continue or Menu
                            if self.gameover_won:
                                self.init_next_level()
                            else:
                                if self.continue_timer <= 0 or all(p.lives < 0 for p in self.players):
                                    total = sum(p.score for p in self.players)
                                    self.high_score = max(self.high_score, total)
                                    self.state = 'menu'
                                    self.menu_mode = 'main'
                                else:
                                    if joy_player_id:
                                        self.player_join(joy_player_id)
                        elif event.button in (7,):  # Start for P2 join
                            if joy_player_id:
                                self.player_join(joy_player_id)
                    elif self.state == 'playing':
                        if event.button == 9: # Plus/Options pauses
                            self.state = 'paused'
                        elif event.button == 7: # P2 join mid-game via Start
                            if joy_player_id and (len(self.players) < joy_player_id or not any(p.player_id==joy_player_id for p in self.players)):
                                self.player_join(joy_player_id)
                    elif self.state == 'paused' and event.button in (0, 9):
                        self.state = 'playing'
                except Exception as e:
                    # Don't crash on joystick quirks
                    pass

            if event.type == pygame.JOYHATMOTION:
                try:
                    if self.state == 'menu':
                        opts = 5 if self.menu_mode=='main' else (len(LEVELS) + 1 if self.menu_mode=='level' else 1)
                        hx, hy = getattr(event, 'value', (0,0))
                        if hy == 1:
                            self.menu_selected = (self.menu_selected - 1) % opts
                        elif hy == -1:
                            self.menu_selected = (self.menu_selected + 1) % opts
                except:
                    pass

            if event.type == pygame.KEYDOWN:
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
                        if event.key == pygame.K_UP:
                            self.menu_selected = (self.menu_selected - 1) % 5
                        elif event.key == pygame.K_DOWN:
                            self.menu_selected = (self.menu_selected + 1) % 5
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
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
                        self.state = 'paused'
                        if snd_mgr:
                            snd_mgr.play('pause')
                    elif event.key == pygame.K_m:
                        self.muted = not self.muted
                        # Toggle all sounds + Battle City original had mute for BGM too
                        if snd_mgr:
                            snd_mgr.toggle_mute()
                        print(f"{'🔇 MUTED' if self.muted else '🔊 SOUND ON'} - 35 original NES maps with retro SFX")
                    elif event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                        if snd_mgr:
                            snd_mgr.stop_bgm()
                elif self.state == 'paused':
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        self.state = 'playing'
                        if snd_mgr:
                            snd_mgr.play('pause')
                elif self.state in ('gameover', 'stage_clear'):
                    if event.key == pygame.K_RETURN:
                        if self.gameover_won:
                            # next level
                            self.init_next_level()
                        else:
                            # back to menu
                            self.state = 'menu'
                            self.menu_mode = 'main'
                            self.menu_selected = 0
                            # update high score
                            total = sum(p.score for p in self.players)
                            self.high_score = max(self.high_score, total)
                    elif event.key == pygame.K_ESCAPE:
                        total = sum(p.score for p in self.players)
                        self.high_score = max(self.high_score, total)
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0

    def handle_menu_select(self):
        if self.menu_selected == 0: # 1P
            self.num_players = 1
            self.current_level = 0
            self.init_level(self.current_level, 1)
        elif self.menu_selected == 1: # 2P
            self.num_players = 2
            self.current_level = 0
            self.init_level(self.current_level, 2)
        elif self.menu_selected == 2: # level select
            self.menu_mode = 'level'
            self.menu_selected = 0
        elif self.menu_selected == 3: # how to
            self.menu_mode = 'howto'
        elif self.menu_selected == 4:
            pygame.quit()
            sys.exit()

    def update_playing(self, dt):
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

        # spawn enemies
        self.spawn_timer += 1
        if self.spawn_timer >= ENEMY_SPAWN_INTERVAL:
            self.spawn_enemy()
            self.spawn_timer = 0
        # initial fast spawns
        if self.enemies_spawned < MAX_ENEMIES_ON_FIELD and self.spawn_timer % 30 == 0:
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

        for i, p in enumerate(self.players):
            if not p.alive:
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
            b = p.handle_input(keys, js, self.tilemap, other_tanks, num_players=len(self.players))
            if b:
                if isinstance(b, list):
                    self.bullets.extend(b)
                else:
                    self.bullets.append(b)
                # add to player's bullets already done in shoot()
            p.update(self.tilemap, other_tanks)

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
            # all tanks
            all_tanks = self.players + self.enemies
            result = b.update(self.tilemap, all_tanks, self.base)
            if result:
                if result in ('hit_brick', 'hit_steel'):
                    self.particles.add_hit(b.x, b.y)
                elif result == 'hit_tank':
                    # find tank at position
                    # explosion already handled via tank death? Add particles
                    self.particles.add_explosion(b.x, b.y, (255, 150, 0), 12)
                elif result == 'hit_base':
                    self.particles.add_explosion(b.x, b.y, (255, 50, 50), 25)

        # cleanup dead bullets
        self.bullets = [b for b in self.bullets if b.alive]

        # check player-enemy collision damage? Touch doesn't kill, but bullets do. However spawn protection collisions blocked in movement.

        # powerups - authentic Battle City powerup appear sound when enemy carrier killed (35 maps same)
        for pu in self.powerups[:]:
            pu.update()
            picker = pu.check_pickup(self.players)
            if picker:
                self.apply_powerup(pu.type, picker)
                if snd_mgr:
                    snd_mgr.play_powerup_pick()
                    if pu.type == 'grenade':
                        snd_mgr.play_explosion(big=True)
                self.particles.add_explosion(pu.x, pu.y, (100,255,100), 15)
            if not pu.alive:
                self.powerups.remove(pu)

        # particles
        self.particles.update()

        # handle dead enemies -> score, spawn powerup chance, count (with explosion sound)
        for e in self.enemies[:]:
            if not e.alive:
                # score
                if self.players:
                    alive_ps = [p for p in self.players if p.alive] or self.players
                    killer = min(alive_ps, key=lambda p: math.hypot(p.x - e.x, p.y - e.y)) if alive_ps else self.players[0]
                    killer.score += e.score_value
                self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 25)
                # Authentic NES explosion SFX - varies by enemy type
                if snd_mgr:
                    snd_mgr.play_explosion(big=(e.enemy_type=='armor'))
                # powerup spawn if carrier - play appear jingle (authentic 8-bit)
                if e.powerup_carrier:
                    pu = PowerUp(e.rect.centerx, e.rect.centery)
                    self.powerups.append(pu)
                    if snd_mgr:
                        snd_mgr.play_powerup_appear()
                self.enemies.remove(e)
                self.enemies_killed += 1

        # handle dead players respawn or game over
        all_dead = True
        for p in self.players:
            if p.alive:
                all_dead = False
            else:
                # if lives remaining, respawn timer?
                if p.lives >= 0:  # allow with lives =0 to respawn? Our die subtracts, so if lives >=0 still has lives left? Actually init 3 lives, after die lives goes 2 etc. If lives <0 then truly game over
                    if p.lives >= 0:
                        # check spawn point free
                        gx, gy = PLAYER_SPAWN[p.player_id-1]
                        # check collision at spawn
                        can_spawn = True
                        test_rect = pygame.Rect(PLAYFIELD_X+gx*TILE_SIZE, PLAYFIELD_Y+gy*TILE_SIZE, TANK_SIZE, TANK_SIZE)
                        for en in self.enemies:
                            if en.alive and test_rect.colliderect(en.rect):
                                can_spawn = False
                        if can_spawn:
                            p.respawn(gx, gy)
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
                    self.continue_timer = CONTINUE_TIME
                    if snd_mgr:
                        snd_mgr.play_explosion(big=True)
                        snd_mgr.play_game_over()
                    self._on_game_over()
                self.state = 'gameover'
                self.gameover_won = False
                return

        # check if all players out of lives and dead
        if all_dead and all(p.lives < 0 for p in self.players):
            if self.state != 'gameover':
                self.continue_timer = CONTINUE_TIME
                if snd_mgr:
                    snd_mgr.play_game_over()
                self._on_game_over()
            self.state = 'gameover'
            self.gameover_won = False
            return

        # win condition - stage clear with authentic NES jingle (35 maps loop)
        if self.enemies_killed >= self.enemies_total and len(self.enemies) == 0:
            self.state = 'stage_clear'
            self.gameover_won = True
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
            # kill all enemies on screen
            for e in self.enemies[:]:
                if e.alive:
                    e.alive = False
                    self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 20)
                    player.score += e.score_value
            # they will be counted next update as killed
        elif pu_type == 'gun':
            player.bullet_power = 2
            player.cooldown = 0
        elif pu_type == 'homing':
            player.apply_powerup('homing', self)
        elif pu_type == 'spread':
            player.apply_powerup('spread', self)
        elif pu_type == 'rapid':
            player.apply_powerup('rapid', self)

    def draw(self):
        if self.state == 'menu':
            self.hud.draw_menu(self.screen, self.menu_selected, self.menu_mode)
        elif self.state in ('playing', 'paused', 'gameover', 'stage_clear'):
            # bg
            self.screen.fill(COLOR_BG)
            # playfield border
            border_rect = pygame.Rect(PLAYFIELD_X-4, PLAYFIELD_Y-4, PLAYFIELD_W+8, PLAYFIELD_H+8)
            pygame.draw.rect(self.screen, (70,70,90), border_rect, border_radius=6)
            # tilemap
            self.tilemap.draw(self.screen)
            # base
            self.base.draw(self.screen)
            # tanks
            for e in self.enemies:
                e.draw(self.screen)
            for p in self.players:
                p.draw(self.screen)
            # bullets
            for b in self.bullets:
                b.draw(self.screen)
            # powerups
            for pu in self.powerups:
                pu.draw(self.screen)
            # overlay tiles (grass)
            self.tilemap.draw_overlay(self.screen)
            # particles top
            self.particles.draw(self.screen)

            # HUD
            self.hud.draw(self.screen, self)

            if self.state == 'paused':
                self.hud.draw_pause(self.screen)
            elif self.state in ('gameover', 'stage_clear'):
                total_score = sum(p.score for p in self.players)
                self.hud.draw_game_over(self.screen, self.gameover_won, total_score, self)

        pygame.display.flip()

    def run(self):
        import traceback
        crash_count = 0
        while True:
            try:
                dt = self.clock.tick(FPS)
                self.handle_events()
                if self.state == 'playing':
                    try:
                        self.update_playing(dt)
                    except Exception as e:
                        print(f"[CRASH GUARD] update_playing failed: {e}")
                        traceback.print_exc()
                        crash_count += 1
                        if crash_count > 10:
                            print("Too many crashes, returning to menu")
                            self.state = 'menu'
                            self.menu_mode = 'main'
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
                    else:
                        # Time out -> go to menu
                        total = sum(p.score for p in self.players)
                        self.high_score = max(self.high_score, total)
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                try:
                    self.draw()
                except Exception as e:
                    print(f"[CRASH GUARD] draw failed: {e}")
                    traceback.print_exc()
                    crash_count += 1
                    if crash_count > 10:
                        self.state = 'menu'
                        crash_count = 0
            except SystemExit:
                raise
            except Exception as e:
                print(f"[CRASH GUARD] main loop failed: {e}")
                traceback.print_exc()
                crash_count += 1
                if crash_count > 20:
                    print("Too many crashes in main loop, exiting")
                    break
