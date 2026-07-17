import pygame
from .tank import Tank
from .bullet import Bullet
from ..settings import *
import game.settings as settings_module  # for live calibration toggles

class PlayerTank(Tank):
    def __init__(self, player_id, grid_x, grid_y, lives=None):
        color = PLAYER_COLORS[player_id-1] if player_id <= len(PLAYER_COLORS) else PLAYER_COLORS[0]
        super().__init__(grid_x, grid_y, color, is_player=True)
        self.player_id = player_id
        self.lives = lives if lives is not None else INITIAL_LIVES
        self.score = 0
        self.star_level = 0
        self.helmet_timer = 0
        self.spawn_protection = 120  # initial protection
        self.speed = TANK_SPEED['player']
        # New item system: tracking missile and 8-way firing
        self.homing_timer = 0    # tracking missile active
        self.spread_timer = 0    # 8-direction active
        self.homing_active = False
        self.spread_active = False
        self.update_bullet_power()

    def add_lives(self, n=COIN_LIVES):
        """Arcade: each coin gives 10 lives"""
        if self.lives < 0:
            self.lives = n
        else:
            self.lives = min(MAX_LIVES, self.lives + n)
        return self.lives

    def add_coin_lives(self):
        return self.add_lives(COIN_LIVES)

    def can_rejoin(self):
        return not self.alive and self.lives < 0

    def update_bullet_power(self):
        if self.star_level == 0:
            self.bullet_power = 1
            self.speed = TANK_SPEED['player']
            MAX_BULLETS['player'] = 1  # actually keep 2 but low level slower
        elif self.star_level == 1:
            self.bullet_power = 1
            MAX_BULLETS['player'] = 2
        elif self.star_level == 2:
            self.bullet_power = 1
            self.speed = TANK_SPEED['player'] * 1.3
        elif self.star_level >= 3:
            self.bullet_power = 2  # can break steel
            self.speed = TANK_SPEED['player'] * 1.3

    def handle_input(self, keys, joystick=None, tilemap=None, other_tanks=None, num_players=1):
        if not self.alive:
            return None
        moved = False
        dir_pressed = None
        shoot = False

        # FIX for cross-control: left controller affects right via OS keyboard mapping
        # If joystick present for this player in 2P mode, ignore keyboard to prevent cross via arrow/WASD emulation
        # In 1P mode, allow both for convenience
        use_keyboard = True
        if num_players == 2 and joystick is not None:
            # In 2P with joystick, ignore keyboard to prevent left Joy-Con generating arrow keys affecting P2 etc
            # Only use keyboard if joystick is idle and no buttons pressed (to allow fallback)
            # Check if joystick has any significant input
            has_joy_input = False
            try:
                if joystick.get_numaxes() >= 2:
                    if abs(joystick.get_axis(0)) > 0.25 or abs(joystick.get_axis(1)) > 0.25:
                        has_joy_input = True
                if joystick.get_numbuttons() > 0:
                    for b in range(min(joystick.get_numbuttons(), 12)):
                        if joystick.get_button(b):
                            has_joy_input = True
                            break
            except:
                pass
            # If joystick has input, ignore keyboard for this player to prevent cross
            if has_joy_input:
                use_keyboard = False
            else:
                # Even if idle, in 2P mode with 2 joysticks, ignore keyboard to prevent cross via OS mapping
                # Only allow keyboard if player has NO joystick
                # Actually, if we have 2 joysticks (L and R), both players have joystick, so both should ignore keyboard
                # This prevents left Joy-Con generating arrow keys that would move P2
                if len([j for j in [joystick] if j is not None]) > 0:
                    # Player has joystick assigned, ignore keyboard for movement to avoid cross
                    # Keep shoot from keyboard as backup? No, also ignore shoot keyboard to avoid cross
                    use_keyboard = False

        if use_keyboard:
            # 8-direction support: check vertical and horizontal separately
            if num_players == 1:
                up = keys[pygame.K_w] or keys[pygame.K_UP]
                down = keys[pygame.K_s] or keys[pygame.K_DOWN]
                left = keys[pygame.K_a] or keys[pygame.K_LEFT]
                right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
                if up and left:
                    dir_pressed = 'UP_LEFT'
                elif up and right:
                    dir_pressed = 'UP_RIGHT'
                elif down and left:
                    dir_pressed = 'DOWN_LEFT'
                elif down and right:
                    dir_pressed = 'DOWN_RIGHT'
                elif up:
                    dir_pressed = 'UP'
                elif down:
                    dir_pressed = 'DOWN'
                elif left:
                    dir_pressed = 'LEFT'
                elif right:
                    dir_pressed = 'RIGHT'
            else:
                if self.player_id == 1:
                    up = keys[pygame.K_w]
                    down = keys[pygame.K_s]
                    left = keys[pygame.K_a]
                    right = keys[pygame.K_d]
                else:
                    up = keys[pygame.K_UP]
                    down = keys[pygame.K_DOWN]
                    left = keys[pygame.K_LEFT]
                    right = keys[pygame.K_RIGHT]
                if up and left:
                    dir_pressed = 'UP_LEFT'
                elif up and right:
                    dir_pressed = 'UP_RIGHT'
                elif down and left:
                    dir_pressed = 'DOWN_LEFT'
                elif down and right:
                    dir_pressed = 'DOWN_RIGHT'
                elif up:
                    dir_pressed = 'UP'
                elif down:
                    dir_pressed = 'DOWN'
                elif left:
                    dir_pressed = 'LEFT'
                elif right:
                    dir_pressed = 'RIGHT'

            # shoot from keyboard only if using keyboard
            if self.player_id == 1:
                shoot = keys[pygame.K_SPACE] or keys[pygame.K_LCTRL] or keys[pygame.K_f]
            else:
                shoot = keys[pygame.K_RETURN] or keys[pygame.K_RCTRL] or keys[pygame.K_m]

        # joystick handling - supports Joy-Con, Pro Controller, Xbox, PS - FIXED for 2P sync and cross-rumble
        joy_btn_dir_idx = None
        joy_btn_dir = None
        if joystick:
            try:
                name = joystick.get_name().lower()
                is_joycon = 'joy-con' in name or 'joycon' in name
                is_joycon_l = 'joy-con (l)' in name and 'l/r' not in name
                is_joycon_r = 'joy-con (r)' in name and 'l/r' not in name
                is_combined = 'l/r' in name  # Nintendo Switch Joy-Con (L/R) combined as Pro controller with 6 axes
                num_axes = joystick.get_numaxes()
                ax = ay = 0

                # === Combined Joy-Con (L/R) split for 2P: TRY SWAPPED to fix left affects right ===
                # User reports left controller affects right, suggests left stick might be axes 2,3 not 0,1
                if is_combined and num_players == 2:
                    if self.player_id == 1:
                        # P1 uses right stick axes 2,3 (try swapped) - if left affects right, left is actually 2,3
                        if num_axes >= 4:
                            ax = joystick.get_axis(2)
                            ay = joystick.get_axis(3)
                            # Fallback to 0,1 if no movement
                            if abs(ax) < 0.3 and abs(ay) < 0.3:
                                ax = joystick.get_axis(0)
                                ay = joystick.get_axis(1)
                        else:
                            ax = joystick.get_axis(0)
                            ay = joystick.get_axis(1)
                    else:
                        # P2 uses left stick axes 0,1
                        if num_axes >= 2:
                            ax = joystick.get_axis(0)
                            ay = joystick.get_axis(1)
                            if abs(ax) < 0.3 and abs(ay) < 0.3 and num_axes >= 4:
                                ax = joystick.get_axis(2)
                                ay = joystick.get_axis(3)
                        else:
                            ax = joystick.get_axis(0)
                            ay = joystick.get_axis(1)
                else:
                    # Normal single joystick per player
                    if num_axes >= 2:
                        ax = joystick.get_axis(0)
                        ay = joystick.get_axis(1)
                        # Right stick fallback if left idle and not combined mode
                        if not is_combined and abs(ax) < 0.3 and abs(ay) < 0.3 and num_axes >= 4:
                            ax2 = joystick.get_axis(2)
                            ay2 = joystick.get_axis(3)
                            if abs(ax2) > 0.3 or abs(ay2) > 0.3:
                                ax, ay = ax2, ay2

                # D-pad hat (Pro Controller, Xbox)
                if joystick.get_numhats() > 0:
                    try:
                        hx, hy = joystick.get_hat(0)
                        if hx != 0 or hy != 0:
                            ax = hx
                            ay = -hy
                    except:
                        pass

                # Apply calibration per Joy-Con side - FIXED for both left and right
                try:
                    if is_combined and num_players == 2:
                        # Combined Joy-Con (L/R) as Pro controller with 6 axes: split for 2P
                        if self.player_id == 1:
                            # P1 left side: same as left Joy-Con fix (SWAP+INV_Y)
                            if getattr(settings_module, 'JOYCON_L_SWAP', settings_module.JOYCON_SWAP_AXES):
                                ax, ay = ay, ax
                            if getattr(settings_module, 'JOYCON_L_INVERT_X', settings_module.JOYCON_INVERT_X):
                                ax = -ax
                            if getattr(settings_module, 'JOYCON_L_INVERT_Y', settings_module.JOYCON_INVERT_Y):
                                ay = -ay
                        else:
                            # P2 right side: both axes inverted (LEFT->RIGHT, UP->DOWN as user reported)
                            if getattr(settings_module, 'JOYCON_R_SWAP', False):
                                ax, ay = ay, ax
                            if getattr(settings_module, 'JOYCON_R_INVERT_X', True):
                                ax = -ax
                            if getattr(settings_module, 'JOYCON_R_INVERT_Y', True):
                                ay = -ay
                    elif is_joycon_l:
                        if getattr(settings_module, 'JOYCON_L_SWAP', settings_module.JOYCON_SWAP_AXES):
                            ax, ay = ay, ax
                        if getattr(settings_module, 'JOYCON_L_INVERT_X', settings_module.JOYCON_INVERT_X):
                            ax = -ax
                        if getattr(settings_module, 'JOYCON_L_INVERT_Y', settings_module.JOYCON_INVERT_Y):
                            ay = -ay
                    elif is_joycon_r:
                        if getattr(settings_module, 'JOYCON_R_SWAP', False):
                            ax, ay = ay, ax
                        if getattr(settings_module, 'JOYCON_R_INVERT_X', True):
                            ax = -ax
                        if getattr(settings_module, 'JOYCON_R_INVERT_Y', True):
                            ay = -ay
                    else:
                        if settings_module.JOYCON_SWAP_AXES:
                            ax, ay = ay, ax
                        if settings_module.JOYCON_INVERT_X:
                            ax = -ax
                        if settings_module.JOYCON_INVERT_Y:
                            ay = -ay
                except:
                    pass

                # Joy-Con specific: D-pad / face buttons as direction when stick idle
                # macOS SDL mapping for Joy-Con (L): btn 0=Down,1=Right,2=Up,3=Left (D-pad)
                # Joy-Con (R) has no D-pad, but we can still use face buttons as dirs for testing
                if abs(ax) < 0.4 and abs(ay) < 0.4:
                    try:
                        nb = joystick.get_numbuttons()
                        # Accurate mapping for Joy-Con L on macOS pygame/SDL
                        # Based on SDL gamecontrollerdb: Joy-Con L: dpup=2, dpdown=0, dpleft=3, dpright=1
                        # Joy-Con R: uses stick, but also allow Y(0)/X(1)/B(2)/A(3) as directions for debugging
                        jc_checks = []
                        # Use calibrated maps - FIXED for attack: Right Joy-Con face buttons should be SHOOT, not movement
                        l_map = settings_module.JOYCON_L_DPAD_MAP
                        # === Combined Joy-Con (L/R) split mapping - FIXED ===
                        if is_combined and num_players == 2:
                            if self.player_id == 1:
                                # P1 left side: D-pad only for movement (not face buttons which are shoot)
                                jc_checks = [
                                    (12, 'UP'), (13, 'DOWN'), (14, 'LEFT'), (15, 'RIGHT'),
                                ]
                                for btn, dir in l_map.items():
                                    jc_checks.append((btn, dir))
                            else:
                                # P2 right side: NO D-pad/face as movement, stick only (fixes attack)
                                jc_checks = []
                        elif is_joycon_l:
                            # Left: D-pad only movement
                            jc_checks = []
                            for btn, dir in l_map.items():
                                jc_checks.append((btn, dir))
                            jc_checks.extend([(12, 'UP'), (13, 'DOWN'), (14, 'LEFT'), (15, 'RIGHT')])
                        elif is_joycon_r:
                            # Right: stick only movement, face buttons are SHOOT (fixes attack not working)
                            jc_checks = []
                        elif is_joycon:
                            jc_checks = []
                            for btn, dir in l_map.items():
                                jc_checks.append((btn, dir))
                            jc_checks.extend([(12, 'UP'), (13, 'DOWN'), (14, 'LEFT'), (15, 'RIGHT')])
                        else:
                            jc_checks = [
                                (11, 'UP'), (12, 'DOWN'), (13, 'LEFT'), (14, 'RIGHT'),
                            ]

                        for b_idx, d in jc_checks:
                            if b_idx < nb and joystick.get_button(b_idx):
                                if dir_pressed is None:
                                    joy_btn_dir = d
                                    joy_btn_dir_idx = b_idx
                                    break
                        # Also if not Joy-Con, check generic D-pad buttons high indices
                        if joy_btn_dir is None and not is_joycon:
                            for b_idx in range(min(nb, 20)):
                                # skip action buttons 0-3 for generic to avoid conflict
                                if b_idx in (0,1,2,3):
                                    continue
                                if joystick.get_button(b_idx):
                                    # Heuristic: if button 11-14 are D-pad
                                    if b_idx == 11:
                                        joy_btn_dir = 'UP'
                                        joy_btn_dir_idx = b_idx
                                        break
                                    elif b_idx == 12:
                                        joy_btn_dir = 'DOWN'
                                        joy_btn_dir_idx = b_idx
                                        break
                                    elif b_idx == 13:
                                        joy_btn_dir = 'LEFT'
                                        joy_btn_dir_idx = b_idx
                                        break
                                    elif b_idx == 14:
                                        joy_btn_dir = 'RIGHT'
                                        joy_btn_dir_idx = b_idx
                                        break
                    except Exception:
                        pass

                # deadzone and direction from axes
                if abs(ax) < 0.32:
                    ax = 0
                if abs(ay) < 0.32:
                    ay = 0
                if ay < -0.5:
                    dir_pressed = 'UP'
                elif ay > 0.5:
                    dir_pressed = 'DOWN'
                elif ax < -0.5:
                    dir_pressed = 'LEFT'
                elif ax > 0.5:
                    dir_pressed = 'RIGHT'
                elif joy_btn_dir:
                    dir_pressed = joy_btn_dir

            except Exception as e:
                # Don't crash, just ignore joystick error for this frame
                # print(f"Joystick handling error: {e}")
                pass

            # Shooting: fixed for 2P sync and cross-rumble bugs
            try:
                nb = joystick.get_numbuttons()
                shoot_buttons = set()
                # For attack fix: make shooting very permissive for Joy-Con
                # P1 left side: allow ANY button except D-pad movement to shoot, to ensure attack works
                # P2 right side: same
                # For combined, allow any button for both players (but still split rumble)
                for b_idx in range(min(nb, 30)):
                    try:
                        if joystick.get_button(b_idx):
                            # Skip only the exact D-pad button used for movement if it's the only button (to avoid move=shoot)
                            # But if another button also pressed, allow shoot
                            if b_idx == joy_btn_dir_idx:
                                # If this is the movement button and it's the ONLY button pressed, don't shoot (movement only)
                                # We will handle this by checking len of all pressed buttons later
                                # For now, add it but mark as movement
                                pass
                            # For all Joy-Con, any button press counts as potential shoot (fix attack not working)
                            shoot_buttons.add(b_idx)
                    except:
                        continue

                # Remove the movement button from shoot set if it's the ONLY button (so moving alone doesn't shoot)
                # If there are other buttons pressed along with movement, keep them for shooting
                if joy_btn_dir_idx is not None and joy_btn_dir_idx in shoot_buttons and len(shoot_buttons) == 1:
                    # Only movement button pressed, no shoot
                    shoot_buttons.clear()

                if shoot_buttons:
                    shoot = True
                    # Rumble disabled per user request - check ENABLE_RUMBLE
                    try:
                        if getattr(settings_module, 'ENABLE_RUMBLE', False):
                            if is_combined and num_players == 2:
                                if self.player_id == 1:
                                    joystick.rumble(0.8, 0.0, 80)
                                else:
                                    joystick.rumble(0.0, 0.8, 80)
                            elif 'joy-con' in joystick.get_name().lower() and hasattr(joystick, 'rumble'):
                                joystick.rumble(0.3, 0.7, 80)
                    except:
                        pass

                # Triggers as axes (Xbox, PS) also shoot - but split for 2P combined
                try:
                    if joystick.get_numaxes() >= 6:
                        # Combined: axis 4 = left trigger, 5 = right trigger
                        if is_combined and num_players == 2:
                            if self.player_id == 1 and joystick.get_axis(4) > 0.5:
                                shoot = True
                            elif self.player_id == 2 and joystick.get_axis(5) > 0.5:
                                shoot = True
                        else:
                            if joystick.get_axis(4) > 0.5 or joystick.get_axis(5) > 0.5:
                                shoot = True
                    elif joystick.get_numaxes() >= 5:
                        if joystick.get_axis(4) > 0.5:
                            shoot = True
                except:
                    pass
            except:
                pass
        else:
            if 'shoot' not in locals():
                shoot = False

        # Authentic ice sliding: if on ice and no input, keep sliding in current direction
        if not dir_pressed and self.on_ice:
            # Continue sliding with same direction, but allow easier turning (original ice has inertia)
            dir_pressed = self.direction

        if dir_pressed:
            # Always face movement/aim direction, even if blocked (fixes bug where moving back still facing forward)
            self.direction = dir_pressed
            moved = self.try_move(dir_pressed, tilemap, other_tanks)

        if shoot:
            result = self.shoot()
            if result:
                return result
        return None

    def get_bullet_spawn_for(self, dir_name):
        """Get spawn position for arbitrary direction (for 8-way firing)"""
        cx, cy = self.rect.center
        offset = TANK_SIZE//2 + 4
        dx, dy = DIRS.get(dir_name, (0, -1))
        # Normalize diagonal
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        return cx + dx * offset, cy + dy * offset

    def shoot(self):
        # Check if we can shoot at all (considers max bullets)
        # For spread, we need to allow up to 8 bullets, so we check more loosely
        if self.spread_active:
            # For spread, need at least 1 slot free
            alive = len([b for b in self.bullets if b.alive])
            max_b = MAX_BULLETS['player'] if isinstance(MAX_BULLETS['player'], int) else 2
            # Allow spread even if near limit, but cap total at max*4 to avoid spam
            if alive >= max_b * 4:
                return None
        else:
            if not self.can_shoot():
                return None

        bullets_created = []

        # Normal bullet color
        base_color = COLOR_YELLOW if self.bullet_power >= 2 else self.color

        if self.spread_active:
            # Fire 8 directions at once
            for d in EIGHT_DIRS:
                sx, sy = self.get_bullet_spawn_for(d)
                # Homing spread: if homing active too, make each homing
                is_homing = self.homing_active
                col = (255, 140, 0) if is_homing else base_color
                bullet = Bullet(sx, sy, d, f"player{self.player_id}", power=self.bullet_power, color=col, homing=is_homing)
                self.bullets.append(bullet)
                bullets_created.append(bullet)
            self.cooldown = 25  # slightly longer for spread
        else:
            sx, sy = self.get_bullet_spawn()
            is_homing = self.homing_active
            col = (255, 140, 0) if is_homing else base_color
            bullet = Bullet(sx, sy, self.direction, f"player{self.player_id}", power=self.bullet_power, color=col, homing=is_homing)
            self.bullets.append(bullet)
            bullets_created.append(bullet)
            self.cooldown = 15 if self.star_level >= 1 else 20

        # Classic Battle City shoot SFX
        try:
            from ..sound_manager import sound_manager
            sound_manager.play_shoot()
        except:
            pass

        # Return single or list for game to handle
        if len(bullets_created) == 1:
            return bullets_created[0]
        return bullets_created

    def update(self, tilemap, other_tanks):
        super().update(tilemap, other_tanks)
        if self.helmet_timer > 0:
            self.helmet_timer -= 1
            if self.helmet_timer <= 0:
                self.invulnerable_timer = 0

        # update new item timers
        if self.homing_timer > 0:
            self.homing_timer -= 1
            self.homing_active = True
            if self.homing_timer <= 0:
                self.homing_active = False
        else:
            self.homing_active = False

        if self.spread_timer > 0:
            self.spread_timer -= 1
            self.spread_active = True
            if self.spread_timer <= 0:
                self.spread_active = False
        else:
            self.spread_active = False

        # clean bullets
        self.bullets = [b for b in self.bullets if b.alive]

    def take_damage(self, power=1):
        if self.helmet_timer > 0 or self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        # die
        self.die()
        return True

    def die(self):
        super().die()
        self.lives -= 1
        # reset star level but keep? Classic loses all power
        self.star_level = 0
        self.homing_timer = 0
        self.spread_timer = 0
        self.homing_active = False
        self.spread_active = False
        self.update_bullet_power()

    def respawn(self, grid_x, grid_y):
        self.set_position(grid_x, grid_y)
        self.alive = True
        self.direction = 'UP'
        self.invulnerable_timer = 0
        self.spawn_protection = 180
        self.helmet_timer = 0
        # keep items? For balance, reset on respawn (or keep? we reset per classic)
        # We keep homing/spread if still has timer? For now keep them until timer expires
        # self.homing_timer and spread remain as is

    def apply_powerup(self, type_name, game=None):
        if type_name == 'helmet':
            self.helmet_timer = POWERUP_DURATION.get('helmet', 10 * FPS)
            self.invulnerable_timer = POWERUP_DURATION.get('helmet', 10 * FPS)
        elif type_name == 'star':
            self.star_level = min(self.star_level + 1, STAR_LEVELS-1)
            self.update_bullet_power()
        elif type_name == 'tank':
            self.lives += 1
            self.score += 500
        elif type_name == 'gun':
            self.bullet_power = 2
            # temporary? make 2x power for star level
        elif type_name == 'shovel':
            if game:
                game.tilemap.activate_shovel()
        elif type_name == 'homing':
            # Tracking missile item: tank can fire tracking missile to attack nearest enemy
            # Active for duration
            self.homing_timer = POWERUP_DURATION.get('homing', 15 * FPS)
            self.homing_active = True
            self.score += 200
        elif type_name == 'spread':
            # 8-direction firing item
            self.spread_timer = POWERUP_DURATION.get('spread', 12 * FPS)
            self.spread_active = True
            self.score += 200
        # grenade, clock handled by game
