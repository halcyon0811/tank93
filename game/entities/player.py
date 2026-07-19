import pygame
from .tank import Tank
from .bullet import Bullet
from ..settings import *
import game.settings as settings_module  # for live calibration toggles

# Debug logging
try:
    from ..logger_integration import safe_log_gameplay, safe_log_event
    HAS_DEBUG = True
except:
    HAS_DEBUG = False
    def safe_log_gameplay(*a, **kw): pass
    def safe_log_event(*a, **kw): pass

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
        # Stacking system: more items = stronger (user request)
        self.total_items_collected = 0
        self.homing_level = 0
        self.spread_level = 0
        self.rapid_level = 0
        self.star_extra_count = 0  # stars beyond max level
        self.bullet_damage_bonus = 0.0  # additive bonus from stacking
        self.speed_bonus = 0.0  # additive speed bonus from stacking
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
        # Stacking: base speed includes speed_bonus from total items collected
        # This makes you stronger the more you get, as requested
        stacking_speed_factor = 1.0 + self.speed_bonus * 0.12 + self.star_extra_count * 0.05
        # Don't override speed completely if shrink/giant active - they manage speed themselves via base_speed
        # But still apply stacking bonus on top
        if self.shrink_timer > 0 or self.giant_timer > 0:
            # size effects manage speed, but include stacking bonus
            if self.star_level == 0:
                self.bullet_power = 1 + int(self.bullet_damage_bonus // 2)  # stacking can increase power even at low star
                MAX_BULLETS['player'] = 1 + self.rapid_level
            elif self.star_level == 1:
                self.bullet_power = 1 + int(self.bullet_damage_bonus // 3)
                MAX_BULLETS['player'] = 2 + self.rapid_level
            elif self.star_level == 2:
                self.bullet_power = 1 + int(self.bullet_damage_bonus // 2)
            elif self.star_level >= 3:
                self.bullet_power = 2 + int(self.bullet_damage_bonus // 2)
            # Apply stacking speed bonus even in shrink/giant (giant overrides but we keep bonus)
            # base_speed already includes some bonus, speed will be set by update_size_state with bonus
            return

        if self.star_level == 0:
            self.bullet_power = 1 + int(self.bullet_damage_bonus // 3)
            self.speed = TANK_SPEED['player'] * stacking_speed_factor
            self.base_speed = TANK_SPEED['player'] * stacking_speed_factor
            MAX_BULLETS['player'] = 1 + self.rapid_level
        elif self.star_level == 1:
            self.bullet_power = 1 + int(self.bullet_damage_bonus // 2)
            self.base_speed = TANK_SPEED['player'] * stacking_speed_factor
            self.speed = self.base_speed
            MAX_BULLETS['player'] = 2 + self.rapid_level
        elif self.star_level == 2:
            self.bullet_power = 1 + int(self.bullet_damage_bonus // 2)
            self.base_speed = TANK_SPEED['player'] * 1.3 * stacking_speed_factor
            self.speed = self.base_speed
        elif self.star_level >= 3:
            self.bullet_power = 2 + int(self.bullet_damage_bonus // 2) + self.star_extra_count // 2
            self.base_speed = TANK_SPEED['player'] * 1.3 * stacking_speed_factor
            self.speed = self.base_speed
            # More bullets with rapid stacking
            if self.rapid_active:
                MAX_BULLETS['player'] = 2 + self.rapid_level + self.star_extra_count // 2

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

        # Determine bullet type with synergy support
        # Synergy: weapon enforcement (bullet_power>=2 / star_level>=3 / gun) + homing = powerful missile
        # Small + giant already handled in update_size_state above
        has_power = self.bullet_power >= 2 or self.star_level >= 3
        has_homing = self.homing_active
        has_spread = self.spread_active
        has_rapid = self.rapid_active

        def get_bullet_type_for_player():
            # Synergy takes precedence
            if has_homing and has_power and has_spread:
                return 'power_homing_spread'  # ultimate: 8 powerful homing missiles
            elif has_homing and has_power:
                return 'power_homing'  # powerful tracking missile
            elif has_homing and has_spread:
                return 'homing'  # 8 homing (not necessarily power)
            elif has_homing:
                return 'homing'
            elif has_spread and has_power and has_rapid:
                return 'power_spread_rapid'
            elif has_spread and has_power:
                return 'power_spread'
            elif has_spread and has_rapid:
                return 'spread'
            elif has_spread:
                return 'spread'
            elif has_rapid and has_power:
                return 'power_rapid'
            elif has_rapid:
                return 'rapid'
            elif has_power:
                return 'power'
            else:
                return 'normal'

        # Power synergy bonuses
        power_synergy = has_power and has_homing
        if power_synergy:
            # Log synergy activation occasionally (not every shot to avoid spam)
            try:
                if not hasattr(self, '_synergy_log_timer'):
                    self._synergy_log_timer = 0
                self._synergy_log_timer += 1
                if self._synergy_log_timer % 60 == 0:
                    from ..logger_integration import safe_log_gameplay
                    safe_log_gameplay("SYNERGY_POWER_HOMING", data={"player_id": self.player_id, "bullet_power": self.bullet_power, "star_level": self.star_level, "homing": has_homing})
            except:
                pass

        if self.spread_active:
            # Fire 8 directions at once - with synergy for power missiles
            for d in EIGHT_DIRS:
                sx, sy = self.get_bullet_spawn_for(d)
                is_homing = self.homing_active
                # Color synergy: power+homing = bright yellow-white powerful missile
                if power_synergy and is_homing:
                    col = (255, 240, 100)  # power homing = bright gold
                elif is_homing:
                    col = (255, 140, 0)  # normal homing orange
                else:
                    if self.rapid_active and not is_homing:
                        col = (255, 100, 150)  # rapid pink (fix: was referencing undefined col)
                    else:
                        col = base_color
                        if has_power:
                            col = (255, 224, 64)  # power = yellow

                b_type = get_bullet_type_for_player()
                # Adjust power for synergy
                bullet_power = self.bullet_power
                if power_synergy:
                    bullet_power = 2  # power homing is always power 2
                    # Even more: if star level 3 + homing + spread, power 2 still but extra effects via type
                if is_homing and has_power:
                    b_type = 'power_homing' if 'power_homing' not in b_type else b_type

                bullet = Bullet(sx, sy, d, f"player{self.player_id}", power=bullet_power, color=col, homing=is_homing, bullet_type=b_type)
                if is_homing:
                    import random as _rnd
                    bullet.replan_timer = _rnd.randint(0, 25)
                    # Stacking: homing_level increases speed and agility
                    level = getattr(self, 'homing_level', 1)
                    if level > 1:
                        bullet.speed *= (1.0 + (level-1)*0.08)  # +8% per extra homing level
                        if hasattr(bullet, 'turn_speed'):
                            bullet.turn_speed *= (1.0 + (level-1)*0.12)
                    if power_synergy:
                        bullet.speed *= 1.3  # powerful missile faster
                        bullet.turn_speed = getattr(bullet, 'turn_speed', 0.068) * (1.2 + (level-1)*0.1)
                        # Power homing also gets damage bonus from bullet_damage_bonus
                        bullet.power = bullet_power + self.bullet_damage_bonus * 0.3
                if self.rapid_active and not is_homing:
                    # Rapid level increases speed
                    r_level = getattr(self, 'rapid_level', 1)
                    bullet.speed *= (1.2 + (r_level-1)*0.15)
                elif self.rapid_active and is_homing:
                    r_level = getattr(self, 'rapid_level', 1)
                    if power_synergy:
                        bullet.speed *= (1.35 + (r_level-1)*0.1)
                    else:
                        bullet.speed *= (1.2 + (r_level-1)*0.08)
                # Apply general damage bonus
                bullet.power = bullet_power + self.bullet_damage_bonus * 0.2
                self.bullets.append(bullet)
                bullets_created.append(bullet)
            base_cd = 25
            # Power synergy and stacking reduces cooldown
            if power_synergy:
                base_cd = max(5, base_cd - 3 - self.homing_level)
            # Rapid level reduces cooldown further
            if self.rapid_active:
                base_cd = max(3, base_cd - self.rapid_level*2)
            self.cooldown = max(2, base_cd // 3) if self.rapid_active else max(3, base_cd)
        else:
            sx, sy = self.get_bullet_spawn()
            is_homing = self.homing_active
            if power_synergy and is_homing:
                col = (255, 240, 100)  # power homing gold
            elif is_homing:
                col = (255, 140, 0)
            else:
                if self.rapid_active and not is_homing:
                    col = (255, 50, 150)
                else:
                    col = base_color
                    if has_power:
                        col = (255, 224, 64)

            b_type = get_bullet_type_for_player()
            bullet_power = self.bullet_power
            if power_synergy:
                bullet_power = 2 + self.star_extra_count // 2

            bullet = Bullet(sx, sy, self.direction, f"player{self.player_id}", power=bullet_power, color=col, homing=is_homing, bullet_type=b_type)
            if is_homing:
                level = getattr(self, 'homing_level', 1)
                if power_synergy:
                    bullet.speed *= (1.3 + (level-1)*0.08)
                    if hasattr(bullet, 'turn_speed'):
                        bullet.turn_speed *= (1.2 + (level-1)*0.12)
                else:
                    if level > 1:
                        bullet.speed *= (1.0 + (level-1)*0.08)
                        if hasattr(bullet, 'turn_speed'):
                            bullet.turn_speed *= (1.0 + (level-1)*0.12)
            if self.rapid_active and not is_homing:
                r_level = getattr(self, 'rapid_level', 1)
                bullet.speed *= (1.2 + (r_level-1)*0.15)
            elif self.rapid_active and is_homing:
                r_level = getattr(self, 'rapid_level', 1)
                if has_power:
                    bullet.speed *= (1.35 + (r_level-1)*0.1)
                else:
                    bullet.speed *= (1.2 + (r_level-1)*0.08)
            # General damage bonus from stacking
            bullet.power = bullet_power + self.bullet_damage_bonus * 0.25
            self.bullets.append(bullet)
            bullets_created.append(bullet)
            base_cd = 15 if self.star_level >= 1 else 20
            if power_synergy:
                base_cd = max(4, base_cd - 2)
            self.cooldown = max(3, base_cd // 3) if self.rapid_active else base_cd

        # Better shooting sounds - choose type based on synergy
        try:
            from ..sound_manager import sound_manager
            if has_homing and has_power and has_spread:
                shoot_type = 'power'  # ultimate - power sound
            elif has_homing and has_power:
                shoot_type = 'power'  # powerful missile uses power sound for impact
            elif has_homing and has_spread:
                shoot_type = 'homing'
            elif has_homing:
                shoot_type = 'homing'
            elif has_spread and has_rapid:
                shoot_type = 'spread'
            elif has_spread:
                shoot_type = 'spread'
            elif has_rapid:
                shoot_type = 'rapid'
            elif has_power:
                shoot_type = 'power'
            else:
                shoot_type = 'punchy'
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
        # Shrink/Giant timers are handled by parent Tank.update_size_state() - do NOT duplicate here
        # Previously this duplicated decrement caused double-speed timer and left is_giant=True with timer=0 -> cannot crush walls
        # Parent handles shrink_timer and giant_timer correctly with scale and is_giant flag

        # clean bullets
        self.bullets = [b for b in self.bullets if b.alive]

    def take_damage(self, power=1, bullet_type='normal'):
        if self.helmet_timer > 0 or self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        # Use armor system from base Tank
        if not super().take_damage(power, bullet_type):
            # Armor absorbed
            return False
        # Armor depleted, die
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
        # Reset stacking counters on death
        self.total_items_collected = 0
        self.homing_level = 0
        self.spread_level = 0
        self.rapid_level = 0
        self.star_extra_count = 0
        self.bullet_damage_bonus = 0.0
        self.speed_bonus = 0.0
        self.venom_timer = 0
        self.venom_level = 0
        self.armor = ARMOR_INITIAL_PLAYER
        self.max_armor = ARMOR_INITIAL_PLAYER
        self.armor_flash_timer = 0
        self._update_rect_size()
        self.update_bullet_power()
        try:
            from ..logger_integration import safe_log_gameplay
            safe_log_gameplay("PLAYER_DIE_RESET_STACK", data={"player_id": self.player_id, "lives_left": self.lives})
        except:
            pass

    def respawn(self, grid_x, grid_y):
        self.set_position(grid_x, grid_y)
        self.alive = True
        self.direction = 'UP'
        self.invulnerable_timer = 0
        self.spawn_protection = 180
        self.helmet_timer = 0
        self.venom_timer = 0
        self.venom_level = 0
        # Restore armor on respawn
        self.armor = ARMOR_INITIAL_PLAYER + self.star_level * ARMOR_UPGRADE_STAR
        self.max_armor = max(self.max_armor, self.armor)
        self.armor_flash_timer = 0
        # keep items? For balance, reset on respawn (or keep? we reset per classic)
        # We keep homing/spread if still has timer? For now keep them until timer expires
        # self.homing_timer and spread remain as is

    def apply_powerup(self, type_name, game=None):
        # Stacking: every item makes you stronger
        self.total_items_collected += 1
        # Base stacking bonuses: + speed and damage per item
        self.speed_bonus += 0.12  # each item +0.12 speed
        self.bullet_damage_bonus += 0.15  # each item +0.15 damage
        # Log stacking
        try:
            from ..logger_integration import safe_log_gameplay
            safe_log_gameplay("POWERUP_STACK", data={"type": type_name, "player_id": self.player_id, "total_items": self.total_items_collected, "speed_bonus": self.speed_bonus, "damage_bonus": self.bullet_damage_bonus, "x": getattr(self, 'x', 0), "y": getattr(self, 'y', 0)})
        except:
            pass

        if type_name == 'helmet':
            self.helmet_timer = POWERUP_DURATION.get('helmet', 10 * FPS)
            self.invulnerable_timer = POWERUP_DURATION.get('helmet', 10 * FPS)
            self.add_armor(30)
            # Stacking: extra helmet extends duration and adds more armor per stack
            self.add_armor(10 + self.total_items_collected * 2)
        elif type_name == 'star':
            if self.star_level < STAR_LEVELS-1:
                self.star_level += 1
            else:
                # Beyond max: extra count for stacking
                self.star_extra_count += 1
                # Each extra star beyond max gives more speed and damage and armor
                self.speed_bonus += 0.20
                self.bullet_damage_bonus += 0.30
                self.add_armor(20 + self.star_extra_count * 5)
                print(f"[STACKING] Chad/Lida star beyond max: extra_count={self.star_extra_count} speed_bonus={self.speed_bonus:.2f} dmg_bonus={self.bullet_damage_bonus:.2f}")
            self.update_bullet_power()
            self.add_armor(ARMOR_UPGRADE_STAR)
            self.max_armor = min(ARMOR_MAX_PLAYER, self.max_armor + 15)
        elif type_name == 'tank':
            self.lives += 1
            self.score += 500
            self.add_armor(ARMOR_UPGRADE_TANK)
            # Stacking: extra life item also gives speed and damage
            self.speed_bonus += 0.05
            self.bullet_damage_bonus += 0.05
        elif type_name == 'gun':
            self.bullet_power = 2
            self.add_armor(ARMOR_UPGRADE_GUN)
            # Gun now also gives stacking bonus for weapon enforcement synergy
            self.bullet_damage_bonus += 0.25
            self.speed_bonus += 0.05
        elif type_name == 'shovel':
            if game:
                game.tilemap.activate_shovel()
            self.add_armor(20)
            self.bullet_damage_bonus += 0.05
        elif type_name == 'homing':
            # Stacking for homing: each extra homing increases level, turn speed, range, damage
            if self.homing_active:
                self.homing_level += 1
                self.bullet_damage_bonus += 0.25
                self.speed_bonus += 0.08
                print(f"[STACKING] Homing level up to {self.homing_level}: faster turn, more range, damage")
                try:
                    from ..logger_integration import safe_log_gameplay
                    safe_log_gameplay("HOMING_LEVEL_UP", data={"player_id": self.player_id, "level": self.homing_level, "total_items": self.total_items_collected})
                except:
                    pass
            else:
                self.homing_level = 1
            self.homing_timer = -1
            self.homing_active = True
            self.score += 200
            self.add_armor(20)
        elif type_name == 'spread':
            if self.spread_active:
                self.spread_level += 1
                self.bullet_damage_bonus += 0.20
                self.speed_bonus += 0.05
                print(f"[STACKING] Spread level up to {self.spread_level}: more bullets or damage")
            else:
                self.spread_level = 1
            self.spread_timer = -1
            self.spread_active = True
            self.score += 200
            self.add_armor(20)
        elif type_name == 'rapid':
            if self.rapid_active:
                self.rapid_level += 1
                self.bullet_damage_bonus += 0.15
                self.speed_bonus += 0.10
                print(f"[STACKING] Rapid level up to {self.rapid_level}: faster shooting, more bullets")
            else:
                self.rapid_level = 1
            self.rapid_timer = -1
            self.rapid_active = True
            self.score += 200
            self.add_armor(15)
        elif type_name == 'shrink':
            # Synergy: allow coexistence with giant (small+giant = normal size, fast, crush)
            # Previously cleared giant, now keeps it for synergy
            self.shrink_timer = POWERUP_DURATION.get('shrink', 15*FPS)
            # Check if giant already active - synergy!
            if self.giant_timer > 0:
                # Both active: synergy to normal size, fast, crush
                self.is_shrunk = True
                self.is_giant = True
                self.current_scale = 1.0  # synergy normal size
                self.speed = self.base_speed * SHRINK_SPEED_MULT
                print(f"[SYNERGY] Shrink + Giant active! Normal size, fast speed, crush bricks")
                try:
                    from ..logger_integration import safe_log_gameplay
                    safe_log_gameplay("SYNERGY_ACTIVATE", data={"type": "small+giant", "player_id": self.player_id, "shrink": self.shrink_timer, "giant": self.giant_timer})
                except:
                    pass
            else:
                # Instant activation for shrink solo
                self.is_shrunk = True
                self.current_scale = SHRINK_SCALE
                self.speed = self.base_speed * SHRINK_SPEED_MULT
            self._update_rect_size()
            self.score += 150
            self.add_armor(10)
            self.update_bullet_power()
        elif type_name == 'giant':
            # Synergy: allow coexistence with shrink
            self.giant_timer = GIANT_DURATION
            if self.shrink_timer > 0:
                # Both active: synergy
                self.is_shrunk = True
                self.is_giant = True
                self.current_scale = 1.0  # normal size
                self.speed = self.base_speed * SHRINK_SPEED_MULT
                print(f"[SYNERGY] Giant + Shrink active! Normal size, fast speed, crush bricks")
                try:
                    from ..logger_integration import safe_log_gameplay
                    safe_log_gameplay("SYNERGY_ACTIVATE", data={"type": "small+giant", "player_id": self.player_id, "shrink": self.shrink_timer, "giant": self.giant_timer})
                except:
                    pass
            else:
                # Instant activation for giant solo - fix 1-frame delay
                self.is_giant = True
                self.current_scale = GIANT_SCALE
                self.speed = self.base_speed * 2.0
            self._update_rect_size()
            self.score += 300
            self.add_armor(40)
            self.update_bullet_power()
            # Log giant activation
            try:
                from ..logger_integration import safe_log_gameplay
                safe_log_gameplay("POWERUP_GIANT_ACTIVATE", data={"player_id": self.player_id, "timer": self.giant_timer, "x": getattr(self, 'x', 0), "y": getattr(self, 'y', 0)})
            except:
                pass
        # grenade, clock handled by game
        elif type_name == 'armor':
            # New armor powerup if added
            self.add_armor(100)
            self.score += 200
