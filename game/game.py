"""Main Game class - handles states, spawner, collisions"""
import pygame
import random
import math
import sys
from .settings import *
from .tilemap import TileMap, LEVELS
from .entities.bullet import Bullet, Base
from .entities.player import PlayerTank
from .entities.enemy import EnemyTank
from .entities.powerup import PowerUp
from .entities.particles import ParticleSystem
from .ui.hud import HUD

class Game:
    def __init__(self):
        pygame.init()
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

        # players
        for i in range(num_players):
            gx, gy = PLAYER_SPAWN[i]
            p = PlayerTank(i+1, gx, gy)
            # if second player continues, keep score? For new level we keep previous player objects? Let's recreate fresh but preserve score/lives from before if continuing
            # For simplicity fresh, but if we are continuing from previous level, we need to carry over
            # This method is for fresh start, carrying handled in next_level
            self.players.append(p)

        self.enemies_total = ENEMIES_PER_LEVEL + self.current_level * 2
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        self.state = 'playing'

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
        self.enemies_total = ENEMIES_PER_LEVEL + self.current_level * 2
        self.enemies_killed = 0
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.freeze_timer = 0
        # respawn players at start with protections
        new_players = []
        for i, old_p in enumerate(prev_players):
            gx, gy = PLAYER_SPAWN[i]
            p = PlayerTank(old_p.player_id, gx, gy)
            p.score = old_p.score
            p.lives = old_p.lives
            p.star_level = old_p.star_level
            p.update_bullet_power()
            new_players.append(p)
        self.players = new_players
        self.state = 'playing'

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
        # find spawn point that is not blocked
        tries = 0
        while tries < 10:
            sx, sy = random.choice(ENEMY_SPAWNS)
            # check if occupied
            blocked = False
            test_rect = pygame.Rect(PLAYFIELD_X + sx*TILE_SIZE, PLAYFIELD_Y + sy*TILE_SIZE, TANK_SIZE, TANK_SIZE)
            for e in self.enemies:
                if e.alive and test_rect.colliderect(e.rect):
                    blocked = True
            for p in self.players:
                if p.alive and test_rect.colliderect(p.rect):
                    blocked = True
            # also tile blocking?
            # tiles at spawn should be empty in levels, but check
            if not blocked:
                # random enemy type weighted
                weights = ['basic']*50 + ['fast']*20 + ['power']*20 + ['armor']*10
                etype = random.choice(weights)
                enemy = EnemyTank(sx, sy, etype)
                self.enemies.append(enemy)
                self.enemies_spawned += 1
                self.particles.add_spawn(enemy.rect.centerx, enemy.rect.centery)
                break
            tries+=1

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
                        hx, hy = getattr(event, 'value', (0,0))
                        if hy == 1:
                            self.menu_selected = (self.menu_selected - 1) % (5 if self.menu_mode=='main' else 6)
                        elif hy == -1:
                            self.menu_selected = (self.menu_selected + 1) % (5 if self.menu_mode=='main' else 6)
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
                        opts = 6
                        if event.key == pygame.K_UP:
                            self.menu_selected = (self.menu_selected - 1) % opts
                        elif event.key == pygame.K_DOWN:
                            self.menu_selected = (self.menu_selected + 1) % opts
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            if self.menu_selected == 5:
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
                    elif event.key == pygame.K_m:
                        self.muted = not self.muted
                    elif event.key == pygame.K_ESCAPE:
                        self.state = 'menu'
                        self.menu_mode = 'main'
                        self.menu_selected = 0
                elif self.state == 'paused':
                    if event.key == pygame.K_p or event.key == pygame.K_ESCAPE:
                        self.state = 'playing'
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
                self.bullets.append(b)
                # add to player's bullets already done
            p.update(self.tilemap, other_tanks)

        # enemies
        players_list = self.players
        for e in self.enemies:
            if self.freeze_timer > 0:
                # frozen, don't move but still update timers
                e.invulnerable_timer = max(e.invulnerable_timer, 1)
                e.cooldown = max(e.cooldown, 1)
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

        # powerups
        for pu in self.powerups[:]:
            pu.update()
            picker = pu.check_pickup(self.players)
            if picker:
                self.apply_powerup(pu.type, picker)
                self.particles.add_explosion(pu.x, pu.y, (100,255,100), 15)
            if not pu.alive:
                self.powerups.remove(pu)

        # particles
        self.particles.update()

        # handle dead enemies -> score, spawn powerup chance, count
        for e in self.enemies[:]:
            if not e.alive:
                # score goes to nearest player? Give to all? We'll give to nearest alive player
                killer = None
                # find closest player, or give to player who shot? For simplicity, give to player with highest score or nearest
                # Check bullet owner last? Our bullet system doesn't track killer after death. So give to closest.
                if self.players:
                    alive_ps = [p for p in self.players if p.alive] or self.players
                    killer = min(alive_ps, key=lambda p: math.hypot(p.x - e.x, p.y - e.y)) if alive_ps else self.players[0]
                    killer.score += e.score_value
                self.particles.add_explosion(e.rect.centerx, e.rect.centery, e.color, 25)
                # powerup spawn if carrier
                if e.powerup_carrier:
                    # spawn powerup at its death pos
                    # find empty spot nearby
                    pu = PowerUp(e.rect.centerx, e.rect.centery)
                    self.powerups.append(pu)
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

        # base destroyed?
        if not self.base.alive:
            if self.state != 'gameover':
                self.continue_timer = CONTINUE_TIME
            self.state = 'gameover'
            self.gameover_won = False
            return

        # check if all players out of lives and dead
        if all_dead and all(p.lives < 0 for p in self.players):
            if self.state != 'gameover':
                self.continue_timer = CONTINUE_TIME
            self.state = 'gameover'
            self.gameover_won = False
            return

        # win condition
        if self.enemies_killed >= self.enemies_total and len(self.enemies) == 0:
            self.state = 'stage_clear'
            self.gameover_won = True
            # bonus
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
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events()
            if self.state == 'playing':
                self.update_playing(dt)
            elif self.state == 'gameover' and not self.gameover_won:
                # Countdown to menu if no coin inserted
                if self.continue_timer > 0:
                    self.continue_timer -= 1
                    # Also update particles for effect
                    self.particles.update()
                else:
                    # Time out -> go to menu
                    total = sum(p.score for p in self.players)
                    self.high_score = max(self.high_score, total)
                    self.state = 'menu'
                    self.menu_mode = 'main'
                    self.menu_selected = 0
            self.draw()
