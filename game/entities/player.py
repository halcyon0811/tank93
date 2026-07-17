import pygame
from .tank import Tank
from .bullet import Bullet
from ..settings import *

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

    def handle_input(self, keys, joystick=None, tilemap=None, other_tanks=None):
        if not self.alive:
            return None
        moved = False
        dir_pressed = None
        # Both players can use WASD or arrows (more forgiving) - classic + modern
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dir_pressed = 'UP'
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dir_pressed = 'DOWN'
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dir_pressed = 'LEFT'
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dir_pressed = 'RIGHT'
        # shoot: allow multiple keys
        if self.player_id == 1:
            shoot = keys[pygame.K_SPACE] or keys[pygame.K_LCTRL] or keys[pygame.K_LSHIFT] or keys[pygame.K_z]
        else:
            shoot = keys[pygame.K_RETURN] or keys[pygame.K_RCTRL] or keys[pygame.K_RSHIFT] or keys[pygame.K_m] or keys[pygame.K_SPACE]

        # joystick handling - supports Joy-Con, Pro Controller, Xbox, PS
        if joystick:
            try:
                name = joystick.get_name().lower()
                is_joycon = 'joy-con' in name or 'joycon' in name
                ax = ay = 0
                if joystick.get_numaxes() >= 2:
                    ax = joystick.get_axis(0)
                    ay = joystick.get_axis(1)
                    # right stick fallback
                    if abs(ax) < 0.3 and abs(ay) < 0.3 and joystick.get_numaxes() >= 4:
                        ax = joystick.get_axis(2)
                        ay = joystick.get_axis(3)
                    # Joy-Con horizontal mode compensation (sideways = 90deg rotate)
                    # If Joy-Con held sideways, swap axes: up becomes left etc.
                    # Detect if stick is sideways by checking name? For now keep normal vertical.
                # D-pad hat (Pro Controller, Xbox)
                if joystick.get_numhats() > 0:
                    hx, hy = joystick.get_hat(0)
                    if hx != 0 or hy != 0:
                        ax = hx
                        ay = -hy

                # Joy-Con specific: D-pad is buttons, not hat on macOS pygame
                # Common Mac mapping: Joy-Con L has 16-20 buttons, D-pad as buttons 0,1,2,3 or 10-13
                # We try to detect D-pad via buttons if no axis movement
                joy_btn_dir = None
                if is_joycon and abs(ax) < 0.4 and abs(ay) < 0.4:
                    try:
                        # Try typical Joy-Con button mapping on macOS
                        # Left Joy-Con vertical: up/down/left/right often buttons 0-3
                        # Right Joy-Con: similar
                        # We'll check multiple possible indices
                        nb = joystick.get_numbuttons()
                        # Map attempt: buttons 0=up,1=down,2=left,3=right or similar
                        # Also check high indices for D-pad
                        checks = [
                            (0, 'UP'), (1, 'DOWN'), (2, 'LEFT'), (3, 'RIGHT'),
                            (10, 'UP'), (11, 'DOWN'), (12, 'LEFT'), (13, 'RIGHT'),
                            (14, 'UP'), (15, 'DOWN'), (16, 'LEFT'), (17, 'RIGHT'),
                        ]
                        for b_idx, d in checks:
                            if b_idx < nb and joystick.get_button(b_idx):
                                # Need to distinguish shoot vs move: if multiple buttons, prioritize direction
                                # If button is held and it's likely D-pad, set direction
                                # But also keep shoot ability
                                if dir_pressed is None: # only set if not already set by stick
                                    joy_btn_dir = d
                                    break
                    except:
                        pass

                # deadzone
                if abs(ax) < 0.35:
                    ax = 0
                if abs(ay) < 0.35:
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
                pass

            # buttons: any button shoots
            try:
                for btn_idx in range(min(joystick.get_numbuttons(), 20)):
                    if joystick.get_button(btn_idx):
                        # For Joy-Con, if we used that button for movement, don't also shoot unless it's action button
                        # But for simplicity, allow any to shoot - you can move and shoot at same time with different buttons
                        # Check if this button was already used as D-pad direction to avoid double
                        is_dir_btn = False
                        if 'joy_btn_dir' in locals() and joy_btn_dir and btn_idx < 4:
                            # maybe it's D-pad, skip shoot for that exact button to avoid shoot while moving only
                            is_dir_btn = False # allow anyway, more fun
                        if not is_dir_btn:
                            shoot = True
                            # Rumble on shoot for Joy-Con (HD Rumble)
                            try:
                                if joystick.get_name().lower().count('joy-con') and hasattr(joystick, 'rumble'):
                                    joystick.rumble(0.3, 0.7, 100)
                            except:
                                pass
                            break
                # Triggers as axes (Xbox) also shoot
                try:
                    if joystick.get_numaxes() >= 5:
                        # triggers often axis 4,5 >0.5
                        if joystick.get_axis(4) > 0.5 or joystick.get_axis(5) > 0.5:
                            shoot = True
                except:
                    pass
            except:
                pass
        else:
            if 'shoot' not in locals():
                shoot = False

        if dir_pressed:
            moved = self.try_move(dir_pressed, tilemap, other_tanks)

        if shoot:
            b = self.shoot()
            if b:
                return b
        return None

    def shoot(self):
        if not self.can_shoot():
            return None
        sx, sy = self.get_bullet_spawn()
        color = COLOR_YELLOW if self.bullet_power >= 2 else self.color
        bullet = Bullet(sx, sy, self.direction, f"player{self.player_id}", power=self.bullet_power, color=color)
        self.bullets.append(bullet)
        self.cooldown = 15 if self.star_level >=1 else 20
        # Classic Battle City shoot SFX (8-bit pew) + screen shake for power
        try:
            from ..sound_manager import sound_manager
            sound_manager.play_shoot()
        except:
            pass
        return bullet

    def update(self, tilemap, other_tanks):
        super().update(tilemap, other_tanks)
        if self.helmet_timer > 0:
            self.helmet_timer -= 1
            if self.helmet_timer <= 0:
                self.invulnerable_timer = 0
        else:
            # if no helmet, invuln only from spawn protection
            pass

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
        self.update_bullet_power()

    def respawn(self, grid_x, grid_y):
        self.set_position(grid_x, grid_y)
        self.alive = True
        self.direction = 'UP'
        self.invulnerable_timer = 0
        self.spawn_protection = 180
        self.helmet_timer = 0

    def apply_powerup(self, type_name, game=None):
        if type_name == 'helmet':
            self.helmet_timer = POWERUP_DURATION['helmet']
            self.invulnerable_timer = POWERUP_DURATION['helmet']
        elif type_name == 'star':
            self.star_level = min(self.star_level + 1, STAR_LEVELS-1)
            self.update_bullet_power()
        elif type_name == 'tank':
            self.lives += 1
            self.score += 500
        elif type_name == 'gun':
            self.bullet_power = 2
            # temporary?
        elif type_name == 'shovel':
            if game:
                game.tilemap.activate_shovel()
        # grenade, clock handled by game
