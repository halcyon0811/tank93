import pygame
from .tank import Tank
from .bullet import Bullet
from ..settings import *
import game.settings as settings_module  # for live calibration toggles
# New input manager for custom controller mapping (user says direction then hits it)
try:
    from ..input_manager import get_direction_from_joystick, get_buttons_from_joystick, load_mapping
    HAS_CUSTOM_MAPPING = True
except ImportError:
    HAS_CUSTOM_MAPPING = False
    def get_direction_from_joystick(js):
        return None
    def get_buttons_from_joystick(js):
        return {}
    def load_mapping():
        return {"maps":{}}

class PlayerTank(Tank):
    def __init__(self, player_id, grid_x, grid_y, lives=None, is_mega=None):
        color = PLAYER_COLORS[player_id-1] if player_id <= len(PLAYER_COLORS) else PLAYER_COLORS[0]
        super().__init__(grid_x, grid_y, color, is_player=True, is_mega=is_mega)
        self.player_id = player_id
        self.lives = lives if lives is not None else INITIAL_LIVES
        self.score = 0
        self.star_level = 0
        self.helmet_timer = 0
        self.spawn_protection = 120  # initial protection
        self.speed = TANK_SPEED['player']
        self.base_speed = TANK_SPEED['player']
        # New item system: tracking missile and 8-way firing and rapid 3x attack + shrink/giant
        self.homing_timer = 0
        self.spread_timer = 0
        self.rapid_timer = 0
        self.shrink_timer = 0
        self.giant_timer = 0
        self.homing_active = False
        self.spread_active = False
        self.rapid_active = False
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
        # Don't override speed if shrink/giant active - they manage speed themselves via base_speed
        if self.shrink_timer > 0 or self.giant_timer > 0:
            # size effects manage speed
            if self.star_level == 0:
                self.bullet_power = 1
                MAX_BULLETS['player'] = 1
            elif self.star_level == 1:
                self.bullet_power = 1
                MAX_BULLETS['player'] = 2
            elif self.star_level == 2:
                self.bullet_power = 1
            elif self.star_level >= 3:
                self.bullet_power = 2
            return

        if self.star_level == 0:
            self.bullet_power = 1
            self.speed = TANK_SPEED['player']
            self.base_speed = TANK_SPEED['player']
            MAX_BULLETS['player'] = 1
        elif self.star_level == 1:
            self.bullet_power = 1
            self.base_speed = TANK_SPEED['player']
            self.speed = TANK_SPEED['player']
            MAX_BULLETS['player'] = 2
        elif self.star_level == 2:
            self.bullet_power = 1
            self.base_speed = TANK_SPEED['player'] * 1.3
            self.speed = self.base_speed
        elif self.star_level >= 3:
            self.bullet_power = 2
            self.base_speed = TANK_SPEED['player'] * 1.3
            self.speed = self.base_speed

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

        # joystick handling - NEW: custom mapping first (from interactive_mapper.py)
        # User says direction then hits it, we save to controller_mapping.json and use here
        joy_btn_dir_idx = None
        joy_btn_dir = None
        custom_dir_used = False
        if joystick and HAS_CUSTOM_MAPPING:
            try:
                # Try custom mapping from game/assets/controller_mapping.json
                # Handles combined Joy-Con (L/R) split: P1 uses right stick (2,3), P2 left (0,1)
                c_dir = get_direction_from_joystick(joystick, player_id=self.player_id, num_players=num_players)
                if c_dir:
                    dir_pressed = c_dir
                    custom_dir_used = True
                c_btns = get_buttons_from_joystick(joystick, player_id=self.player_id, num_players=num_players)
                if c_btns.get("SHOOT") or c_btns.get("ATTACK"):
                    shoot = True
                # Debug: if mapping file exists, show it once
                # print(f"[CustomMap] P{self.player_id} dir={c_dir} btns={c_btns}")
            except Exception as e:
                # Fallback to old logic if custom fails
                # print(f"Custom mapping error: {e}")
                pass

        # joystick handling - supports Joy-Con, Pro Controller, Xbox, PS - FIXED for 2P sync and cross-rumble
        # Only run old hardcoded logic if custom mapping didn't already provide direction
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

                # deadzone and direction from axes - only if custom mapping didn't already set direction
                if not custom_dir_used:
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
        # For spread and rapid, we need to allow more bullets
        max_b = MAX_BULLETS['player'] if isinstance(MAX_BULLETS['player'], int) else 2
        alive = len([b for b in self.bullets if b.alive])

        if self.spread_active:
            # For spread, need at least 1 slot free, but allow up to max*4
            # If rapid also active, allow even more (max*6) for 3x attack
            limit = max_b * 6 if self.rapid_active else max_b * 4
            if alive >= limit:
                return None
        elif self.rapid_active:
            # Rapid 3x attack: allow 3x bullets on screen
            if alive >= max_b * 3:
                return None
        else:
            if not self.can_shoot():
                return None

        bullets_created = []

        # Normal bullet color - rapid has pinkish tint if active
        base_color = COLOR_YELLOW if self.bullet_power >= 2 else self.color
        if self.rapid_active and not self.homing_active:
            # Make rapid bullets have slight pink tint for visual feedback
            # Mix base color with rapid pink
            base_color = (min(255, base_color[0]+30), base_color[1], min(255, base_color[2]+30)) if isinstance(base_color, tuple) else base_color

        if self.spread_active:
            # Fire 8 directions at once
            for d in EIGHT_DIRS:
                sx, sy = self.get_bullet_spawn_for(d)
                # Homing spread: if homing active too, make each homing but with stagger for perf (avoid 8 A* same frame)
                is_homing = self.homing_active
                col = (255, 140, 0) if is_homing else base_color
                if self.rapid_active and not is_homing:
                    col = (255, 100, 150) if col == self.color else col
                bullet = Bullet(sx, sy, d, f"player{self.player_id}", power=self.bullet_power, color=col, homing=is_homing)
                # stagger replan to avoid 8 A* spike same frame
                if is_homing:
                    import random as _rnd
                    bullet.replan_timer = _rnd.randint(0, 25)
                self.bullets.append(bullet)
                bullets_created.append(bullet)
            # Cooldown: base 25, /3 if rapid active = ~8
            base_cd = 25
            self.cooldown = max(3, base_cd // 3) if self.rapid_active else base_cd
        else:
            sx, sy = self.get_bullet_spawn()
            is_homing = self.homing_active
            col = (255, 140, 0) if is_homing else base_color
            if self.rapid_active and not is_homing:
                # Override with rapid color if not homing
                col = (255, 50, 150)
            bullet = Bullet(sx, sy, self.direction, f"player{self.player_id}", power=self.bullet_power, color=col, homing=is_homing)
            # If rapid, bullet speed *1.2 for extra feel, but NOT for homing (keep tank speed)
            if self.rapid_active and not is_homing:
                bullet.speed *= 1.2
            self.bullets.append(bullet)
            bullets_created.append(bullet)
            base_cd = 15 if self.star_level >= 1 else 20
            self.cooldown = max(3, base_cd // 3) if self.rapid_active else base_cd

        # Better shooting sounds - choose type based on active items
        try:
            from ..sound_manager import sound_manager
            # Determine best shoot sound type for satisfying feedback
            if self.homing_active and self.spread_active:
                shoot_type = 'homing'  # 8 homing missiles - missile sound
            elif self.homing_active:
                shoot_type = 'homing'
            elif self.spread_active and self.rapid_active:
                shoot_type = 'spread'  # rapid spread
            elif self.spread_active:
                shoot_type = 'spread'
            elif self.rapid_active:
                shoot_type = 'rapid'
            elif self.bullet_power >= 2:
                shoot_type = 'power'
            else:
                shoot_type = 'punchy'  # new better normal shoot
            sound_manager.play_shoot(shoot_type)
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

        # update new item timers - permanent until death (timer -1 = infinite)
        # Homing
        if self.homing_timer == -1:
            self.homing_active = True
        elif self.homing_timer > 0:
            self.homing_timer -= 1
            self.homing_active = True
            if self.homing_timer <= 0:
                self.homing_active = False
        else:
            if self.homing_timer != -1:
                self.homing_active = False
        # Spread
        if self.spread_timer == -1:
            self.spread_active = True
        elif self.spread_timer > 0:
            self.spread_timer -= 1
            self.spread_active = True
            if self.spread_timer <= 0:
                self.spread_active = False
        else:
            if self.spread_timer != -1:
                self.spread_active = False
        # Rapid
        if self.rapid_timer == -1:
            self.rapid_active = True
        elif self.rapid_timer > 0:
            self.rapid_timer -= 1
            self.rapid_active = True
            if self.rapid_timer <= 0:
                self.rapid_active = False
        else:
            if self.rapid_timer != -1:
                self.rapid_active = False
        # Shrink - 15s temp
        if self.shrink_timer > 0:
            self.shrink_timer -= 1
            if self.shrink_timer <= 0:
                self.shrink_timer = 0
        # Giant - 15s
        if self.giant_timer > 0:
            self.giant_timer -= 1
            if self.giant_timer <= 0:
                self.giant_timer = 0

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
        self.star_level = 0
        self.homing_timer = 0
        self.spread_timer = 0
        self.rapid_timer = 0
        self.shrink_timer = 0
        self.giant_timer = 0
        self.homing_active = False
        self.spread_active = False
        self.rapid_active = False
        self.is_shrunk = False
        self.is_giant = False
        self.current_scale = 1.0
        self.speed = TANK_SPEED['player']
        self.base_speed = TANK_SPEED['player']
        self.venom_timer = 0
        self.venom_level = 0
        self._update_rect_size()
        self.update_bullet_power()

    def respawn(self, grid_x, grid_y):
        self.set_position(grid_x, grid_y)
        self.alive = True
        self.direction = 'UP'
        self.invulnerable_timer = 0
        self.spawn_protection = 180
        self.helmet_timer = 0
        self.venom_timer = 0
        self.venom_level = 0
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
            # Kept across stages, only lost on death (per user request)
            # Set to permanent until death: timer = -1 means infinite
            self.homing_timer = -1  # permanent until death
            self.homing_active = True
            self.score += 200
        elif type_name == 'spread':
            # 8-direction firing item - kept across stages, lost on death
            self.spread_timer = -1  # permanent until death
            self.spread_active = True
            self.score += 200
        elif type_name == 'rapid':
            self.rapid_timer = -1
            self.rapid_active = True
            self.score += 200
        elif type_name == 'shrink':
            # Half size, double speed for 15s
            self.shrink_timer = POWERUP_DURATION.get('shrink', 15*FPS)
            # cancel giant if active (can't be both)
            self.giant_timer = 0
            self.is_giant = False
            self.score += 150
            self.update_bullet_power()
        elif type_name == 'giant':
            self.giant_timer = GIANT_DURATION
            self.shrink_timer = 0
            self.is_shrunk = False
            self.score += 300
            self.update_bullet_power()
        # grenade, clock handled by game
