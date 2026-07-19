import pygame
import random
import pathlib
import math
from ..settings import *

# Debug logging
try:
    from ..debug_logger import debug_logger
    from ..logger_integration import safe_log_gameplay, safe_log_event
    HAS_DEBUG = True
except ImportError:
    HAS_DEBUG = False
    def safe_log_gameplay(*a, **kw): pass
    def safe_log_event(*a, **kw): pass

# Try to load authentic NES sprite sheet
try:
    from ..assets.sprites import get_tank_sprite_scaled
    HAS_AUTHENTIC_SPRITES = True
except Exception:
    HAS_AUTHENTIC_SPRITES = False
    def get_tank_sprite_scaled(*a, **k):
        return None

class Tank:
    def __init__(self, grid_x, grid_y, color, is_player=False, is_mega=None):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.is_mega = is_mega if is_mega is not None else MEGA_ENABLED
        self.tile_size = MEGA_TILE_SIZE if self.is_mega else TILE_SIZE
        self.x = PLAYFIELD_X + grid_x * self.tile_size + self.tile_size//2
        self.y = PLAYFIELD_Y + grid_y * self.tile_size + self.tile_size//2
        # Use full TANK_SIZE for collision to avoid visual overlapping with bricks
        self.base_size = TANK_SIZE
        self.current_scale = 1.0
        self.rect = pygame.Rect(0,0,self.base_size, self.base_size)
        self.rect.center = (self.x, self.y)

        self.color = color
        self.is_player = is_player
        self.alive = True
        self.direction = 'UP'
        self.next_direction = None

        self.bullets = []
        self.cooldown = 0
        self.bullet_power = 1
        self.speed = TANK_SPEED['player'] if is_player else TANK_SPEED['enemy']
        self.base_speed = self.speed

        self.invulnerable_timer = 0
        self.spawn_protection = 0
        self.on_ice = False

        # Armor system
        if is_player:
            self.armor = ARMOR_INITIAL_PLAYER
            self.max_armor = ARMOR_INITIAL_PLAYER
        else:
            # enemy armor set later in subclass, fallback
            self.armor = ARMOR_INITIAL_ENEMY.get('basic', 50)
            self.max_armor = self.armor
        self.armor_flash_timer = 0  # for visual hit feedback

        # size effects
        self.shrink_timer = 0
        self.giant_timer = 0
        self.is_shrunk = False
        self.is_giant = False

        # venom
        self.venom_timer = 0
        self.venom_level = 0

        # animation
        self.move_timer = 0
        self.track_offset = 0
        # Stuck detection for player edge bug
        self.stuck_timer = 0
        self.last_pos = (self.x, self.y)

    def update_size_state(self):
        # Handle shrink/giant timers with synergy: small+giant = normal size, fast speed, crush bricks
        # This implements user request: small + giant can have normal size tank but run over bricks and speed like small one
        if self.shrink_timer > 0 and self.giant_timer > 0:
            # Synergy: both active
            self.shrink_timer -= 1
            self.giant_timer -= 1
            self.is_shrunk = True
            self.is_giant = True
            self.current_scale = 1.0  # normal size
            self.speed = self.base_speed * SHRINK_SPEED_MULT  # fast like small
            # Handle expiry
            if self.shrink_timer == 0:
                self.is_shrunk = False
                # If giant still active, go to giant only
                if self.giant_timer > 0:
                    self.current_scale = GIANT_SCALE
                    self.speed = self.base_speed  # giant solo speed base
                else:
                    self.current_scale = 1.0
                    self.speed = self.base_speed
                self._update_rect_size()
            if self.giant_timer == 0:
                self.is_giant = False
                # If shrink still active, go to shrink only
                if self.shrink_timer > 0:
                    self.current_scale = SHRINK_SCALE
                    self.speed = self.base_speed * SHRINK_SPEED_MULT
                else:
                    self.current_scale = 1.0
                    self.speed = self.base_speed
                self._update_rect_size()
            # Log synergy
            try:
                if self.shrink_timer % 60 == 0 or self.giant_timer % 60 == 0:
                    from .logger_integration import safe_log_gameplay
                    safe_log_gameplay("SYNERGY_SMALL_GIANT", data={"shrink": self.shrink_timer, "giant": self.giant_timer, "scale": self.current_scale, "speed": self.speed})
            except:
                pass
        elif self.shrink_timer > 0:
            self.shrink_timer -= 1
            self.is_shrunk = True
            self.current_scale = SHRINK_SCALE
            self.speed = self.base_speed * SHRINK_SPEED_MULT
            if self.shrink_timer == 0:
                self.is_shrunk = False
                self.current_scale = 1.0 if not self.is_giant else GIANT_SCALE
                self.speed = self.base_speed * (2.0 if self.is_giant else 1.0)
                self._update_rect_size()
        elif self.giant_timer > 0:
            self.giant_timer -= 1
            self.is_giant = True
            self.current_scale = GIANT_SCALE
            if self.giant_timer == 0:
                self.is_giant = False
                self.current_scale = SHRINK_SCALE if self.is_shrunk else 1.0
                # speed back to normal or shrunk
                if self.is_shrunk:
                    self.speed = self.base_speed * SHRINK_SPEED_MULT
                else:
                    self.speed = self.base_speed
                self._update_rect_size()
        # update rect size based on scale
        self._update_rect_size()

    def _update_rect_size(self):
        sz = int(self.base_size * self.current_scale)
        # prevent too tiny
        sz = max(12, sz)
        self.rect = pygame.Rect(0,0,sz,sz)
        self.rect.center = (self.x, self.y)

    def set_position(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * self.tile_size + self.tile_size//2
        self.y = PLAYFIELD_Y + grid_y * self.tile_size + self.tile_size//2
        self.rect.center = (self.x, self.y)

    def get_bullet_spawn(self):
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        offset = int((TANK_SIZE//2 + 4) * scale)
        dx, dy = DIRS.get(self.direction, (0, -1))
        return cx + dx * offset, cy + dy * offset

    def get_bullet_spawn_for(self, dir_name):
        """Get spawn position for arbitrary direction (for 8-way firing)"""
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        offset = int((TANK_SIZE//2 + 4) * scale)
        dx, dy = DIRS.get(dir_name, (0, -1))
        # Normalize diagonal
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        return cx + dx * offset, cy + dy * offset

    def can_shoot(self):
        if self.cooldown > 0:
            return False
        max_b = MAX_BULLETS['player'] if self.is_player else MAX_BULLETS['enemy']
        # count alive bullets
        alive = len([b for b in self.bullets if b.alive])
        return alive < max_b

    def try_move(self, dir_name, tilemap, other_tanks):
        if not self.alive:
            return False

        # Authentic turning: try to snap to grid when turning (original NES 8-pixel alignment)
        # Store previous direction to detect turn
        prev_dir = self.direction
        is_turn = prev_dir != dir_name and prev_dir is not None

        # Determine snap attempt for turning
        snap_x = self.x
        snap_y = self.y
        if is_turn:
            # When turning from vertical to horizontal, snap Y to nearest half-tile
            # When turning from horizontal to vertical, snap X
            # Half-tile = TILE_SIZE//2 = 12 px, center offset = TILE_SIZE//2
            # Formula: nearest = PLAYFIELD + round((pos - PLAYFIELD - TILE_SIZE//2)/ (TILE_SIZE//2)) * (TILE_SIZE//2) + TILE_SIZE//2
            half = TILE_SIZE // 2
            if prev_dir in ('UP','DOWN') and dir_name in ('LEFT','RIGHT'):
                # Snap Y
                rel_y = self.y - PLAYFIELD_Y - TILE_SIZE//2
                # nearest half-tile
                snapped_rel = round(rel_y / half) * half
                snap_y = PLAYFIELD_Y + snapped_rel + TILE_SIZE//2
                # Only snap if close enough (within 8 px) to avoid jumping
                if abs(snap_y - self.y) > 8:
                    snap_y = self.y  # too far, don't snap
            elif prev_dir in ('LEFT','RIGHT') and dir_name in ('UP','DOWN'):
                rel_x = self.x - PLAYFIELD_X - TILE_SIZE//2
                snapped_rel = round(rel_x / half) * half
                snap_x = PLAYFIELD_X + snapped_rel + TILE_SIZE//2
                if abs(snap_x - self.x) > 8:
                    snap_x = self.x

        self.direction = dir_name
        dx, dy = DIRS[dir_name]
        # Normalize diagonal speed so diagonal not faster than cardinal
        if dx != 0 and dy != 0:
            # Diagonal: normalize to 0.707
            dx *= 0.7071
            dy *= 0.7071

        # Ice effect - authentic: higher speed + slight slide
        speed_mult = 1.35 if self.on_ice else 1.0
        new_x = snap_x + dx * self.speed * speed_mult
        new_y = snap_y + dy * self.speed * speed_mult

        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # bounds - FIXED edge stuck bug (user reports tank stuck attached to edge)
        # Previous fix with tolerance helped but still allowed tank to drift outside then get permanently blocked
        # New robust fix:
        # 1) Always clamp current position if already outside (prevent permanent stuck)
        # 2) For movement, check if new position would go further outside than current - only block that axis
        # 3) Allow sliding: if moving diagonally and X blocked but Y not, allow Y movement (slide along edge)
        # 4) Clamp new position to playfield bounds + small tolerance
        edge_tolerance = 14
        # If current position already outside tolerance, pull back in immediately (auto-correct)
        if self.rect.left < PLAYFIELD_X - edge_tolerance*2 or self.rect.right > PLAYFIELD_X + PLAYFIELD_W + edge_tolerance*2 or \
           self.rect.top < PLAYFIELD_Y - edge_tolerance*2 or self.rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + edge_tolerance*2:
            # Emergency clamp
            cx = max(PLAYFIELD_X + TANK_SIZE//2, min(PLAYFIELD_X + PLAYFIELD_W - TANK_SIZE//2, self.x))
            cy = max(PLAYFIELD_Y + TANK_SIZE//2, min(PLAYFIELD_Y + PLAYFIELD_H - TANK_SIZE//2, self.y))
            if abs(cx - self.x) > 1 or abs(cy - self.y) > 1:
                try:
                    from .logger_integration import safe_log_gameplay
                    safe_log_gameplay("EDGE_AUTO_CLAMP", data={"old_x": self.x, "old_y": self.y, "new_x": cx, "new_y": cy})
                except:
                    pass
            self.x = cx
            self.y = cy
            self.rect.center = (self.x, self.y)
            new_x = cx + dx * self.speed * speed_mult
            new_y = cy + dy * self.speed * speed_mult
            new_rect = self.rect.copy()
            new_rect.center = (new_x, new_y)

        # Check X bounds
        x_blocked = False
        if new_rect.left < PLAYFIELD_X - edge_tolerance:
            # Moving left further outside? Block only if dx<0
            if dx < 0:
                x_blocked = True
            else:
                # Clamp to edge, allow Y movement
                new_x = max(new_x, PLAYFIELD_X + new_rect.width//2 - edge_tolerance)
        if new_rect.right > PLAYFIELD_X + PLAYFIELD_W + edge_tolerance:
            if dx > 0:
                x_blocked = True
            else:
                new_x = min(new_x, PLAYFIELD_X + PLAYFIELD_W - new_rect.width//2 + edge_tolerance)

        # Check Y bounds
        y_blocked = False
        if new_rect.top < PLAYFIELD_Y - edge_tolerance:
            if dy < 0:
                y_blocked = True
            else:
                new_y = max(new_y, PLAYFIELD_Y + new_rect.height//2 - edge_tolerance)
        if new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + edge_tolerance:
            if dy > 0:
                y_blocked = True
            else:
                new_y = min(new_y, PLAYFIELD_Y + PLAYFIELD_H - new_rect.height//2 + edge_tolerance)

        # If both axes blocked, fully blocked
        if x_blocked and y_blocked:
            # For diagonal, allow sliding on one axis if possible
            # Try X only and Y only separately
            test_rect_x = self.rect.copy()
            test_rect_x.center = (new_x, self.y)
            test_rect_y = self.rect.copy()
            test_rect_y.center = (self.x, new_y)
            # Re-check with tile collision for slide?
            # For edge only, if both blocked, return False
            self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
            self._log_stuck_if_needed(dir_name)
            return False
        elif x_blocked:
            # X blocked but Y may still move (slide along vertical edge)
            if dy != 0:
                new_x = self.x  # keep X, only move Y
            else:
                self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
                self._log_stuck_if_needed(dir_name)
                return False
        elif y_blocked:
            if dx != 0:
                new_y = self.y  # keep Y, only move X (slide along horizontal edge)
            else:
                self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
                self._log_stuck_if_needed(dir_name)
                return False

        # Rebuild rect after potential clamping/sliding adjustment
        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # tile collision - FIXED: tank 32px vs brick tile 24px
        # Previously used full 32 rect for tile collision -> destroying 1 brick (24px) not enough for 32px tank to pass
        # User reported: destroyed brick area smaller than tank width, cannot pass through
        # Fix: use smaller collision rect for tile checks (24x24 = TANK_SIZE-8) so single destroyed brick = passable
        # For tank-tank collision, keep full rect to prevent overlapping tanks
        # Visual gap: user reports 24px gap still too small for 32px tank to pass (one-time destroyable brick)
        # Fix: use smaller collision rect 20x20 (inflate -12) for normal tanks, giving 4px clearance in 24px gap
        # Previously 24x24 required perfect centering, now 20x20 allows ±2px tolerance, feels better
        # Giant/boss keep full rect for crush detection
        is_giant = getattr(self, 'is_giant', False) and getattr(self, 'giant_timer', 0) > 0
        is_boss = getattr(self, 'is_boss', False)
        can_crush_brick = is_giant or is_boss
        is_shrunk = getattr(self, 'is_shrunk', False) and getattr(self, 'shrink_timer', 0) > 0

        if can_crush_brick:
            tile_check_rect = new_rect.copy()  # full 32 for crush detection
        elif is_shrunk:
            tile_check_rect = new_rect.inflate(-16, -16)  # shrink: 32*0.5=16 visual, but collision 16 -> 32-16=16, even smaller for easy passage
        else:
            # Normal tank: 20x20 collision (was 24x24) - allows passing through single destroyed brick (24px gap) with 4px clearance
            # TANK_SIZE 32, TILE 24, collision 20 = 6px visual overlap each side when squeezing, acceptable
            tile_check_rect = new_rect.inflate(-12, -12)  # 32->20

        tiles = tilemap.get_tiles_in_rect(tile_check_rect)
        crushed_bricks = []
        for ttype, gx, gy, trect in tiles:
            if tile_check_rect.colliderect(trect):
                if can_crush_brick:
                    # Giant and boss can crush brick, boss can also crush steel for escape (user request)
                    if ttype == TILE_BRICK:
                        crushed_bricks.append((gx, gy))
                        continue
                    elif ttype == TILE_STEEL and is_boss:
                        # Boss can crush steel walls to escape once surrounding wall partially destroyed
                        # Takes more effort, but allowed
                        crushed_bricks.append((gx, gy))
                        continue
                if is_turn and (abs(snap_x - self.x) > 0.1 or abs(snap_y - self.y) > 0.1):
                    # Try without snap (original position + movement only) to allow turning near walls without clipping
                    new_rect2 = self.rect.copy()
                    new_rect2.center = (self.x + dx * self.speed * speed_mult, self.y + dy * self.speed * speed_mult)
                    if can_crush_brick:
                        tile_check_rect2 = new_rect2.copy()
                    elif is_shrunk:
                        tile_check_rect2 = new_rect2.inflate(-16, -16)
                    else:
                        tile_check_rect2 = new_rect2.inflate(-12, -12)  # 20x20 for normal (was 24x24)
                    tiles2 = tilemap.get_tiles_in_rect(tile_check_rect2)
                    blocked2 = False
                    for t2, gx2, gy2, tr2b in tiles2:
                        if not tile_check_rect2.colliderect(tr2b):
                            continue
                        if t2 == TILE_BRICK and can_crush_brick:
                            continue
                        blocked2 = True
                        break
                    if not blocked2:
                        snap_x, snap_y = self.x, self.y
                        new_x = self.x + dx * self.speed * speed_mult
                        new_y = self.y + dy * self.speed * speed_mult
                        new_rect = new_rect2
                        tile_check_rect = tile_check_rect2
                        tiles = tiles2
                        # collect crushed bricks for new_rect2
                        for t2, gx2, gy2, _ in tiles2:
                            if t2 == TILE_BRICK and can_crush_brick and tile_check_rect2.colliderect(_):
                                if (gx2, gy2) not in crushed_bricks:
                                    crushed_bricks.append((gx2, gy2))
                    else:
                        self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
                        self._log_stuck_if_needed(dir_name)
                        return False
                else:
                    # Try sliding through 1-tile gap: if moving vertically, nudge X slightly to find gap; if horizontal, nudge Y
                    # This helps passing through destroyed brick channel even if not perfectly centered (user report)
                    slid = False
                    if not can_crush_brick:
                        for offset in (4, -4, 8, -8, 12, -12):
                            test_x = new_x
                            test_y = new_y
                            if dy != 0:  # vertical movement, try X slide
                                test_x = new_x + offset
                            else:  # horizontal, try Y slide
                                test_y = new_y + offset
                            test_rect = self.rect.copy()
                            test_rect.center = (test_x, test_y)
                            if is_shrunk:
                                test_check = test_rect.inflate(-16, -16)
                            else:
                                test_check = test_rect.inflate(-12, -12)
                            # Check tiles for this offset
                            blocked = False
                            for ttype2, gx2, gy2, trect2 in tilemap.get_tiles_in_rect(test_check):
                                if test_check.colliderect(trect2):
                                    if ttype2 == TILE_BRICK and can_crush_brick:
                                        continue
                                    blocked = True
                                    break
                            if not blocked:
                                # Found slide path
                                new_x = test_x
                                new_y = test_y
                                new_rect.center = (new_x, new_y)
                                tile_check_rect = test_check
                                slid = True
                                try:
                                    from .logger_integration import safe_log_gameplay
                                    safe_log_gameplay("SLIDE_THROUGH_GAP", data={"x": self.x, "y": self.y, "dir": dir_name, "offset": offset})
                                except:
                                    pass
                                break
                    if not slid:
                        self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
                        self._log_stuck_if_needed(dir_name)
                        return False

        for gx, gy in crushed_bricks:
            try:
                tilemap.destroy_tile(gx, gy, 2, dir_name)
            except:
                try:
                    tilemap.destroy_tile(gx, gy, 2)
                except:
                    pass
            # Log brick crush by giant/boss
            try:
                from .logger_integration import safe_log_gameplay
                safe_log_gameplay("BRICK_CRUSH", data={"x": gx, "y": gy, "by": "giant" if is_giant else "boss" if is_boss else "unknown", "dir": dir_name})
            except:
                pass

        # tank-tank collision - strict full rects to prevent any visual overlap, giant/boss can run over enemies
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect):
                # If self is player giant and other is enemy, crush it
                if is_giant and self.is_player and not other.is_player:
                    # Crush enemy
                    try:
                        other.die()
                        # score?
                        if hasattr(self, 'score'):
                            self.score += getattr(other, 'score_value', 100)
                    except:
                        other.alive = False
                    continue  # don't block, ran over
                # Boss monster can crush enemy tanks too (free-for-all)
                if is_boss and not getattr(other, 'is_player', False) and not getattr(other, 'is_boss', False):
                    # Boss crushes normal enemy tanks
                    try:
                        other.die()
                        from .logger_integration import safe_log_gameplay
                        safe_log_gameplay("BOSS_CRUSH_ENEMY", data={"boss_x": self.x, "boss_y": self.y, "enemy_type": getattr(other, 'enemy_type', 'unknown')})
                    except:
                        other.alive = False
                    continue
                # Shrink can go through smaller gaps? No, still block
                self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
                self._log_stuck_if_needed(dir_name)
                return False

        # Move successful - apply snap if any
        self.x = new_x
        self.y = new_y
        self.rect.center = (self.x, self.y)
        self.move_timer += 1
        self.track_offset = (self.track_offset + self.speed) % 8
        # Update stuck tracking
        dist = math.hypot(self.x - self.last_pos[0], self.y - self.last_pos[1]) if hasattr(self, 'last_pos') else 999
        if dist < 0.5:
            self.stuck_timer = getattr(self, 'stuck_timer', 0) + 1
        else:
            self.stuck_timer = 0
        self.last_pos = (self.x, self.y)
        return True

    def _log_stuck_if_needed(self, dir_name):
        # Log if stuck for long at edge
        if getattr(self, 'stuck_timer', 0) > 30:
            try:
                from .logger_integration import safe_log_gameplay
                # Only log every 60 frames to avoid spam
                if self.stuck_timer % 60 == 0:
                    safe_log_gameplay("PLAYER_STUCK" if self.is_player else "ENEMY_STUCK", data={"x": self.x, "y": self.y, "dir": dir_name, "stuck_timer": self.stuck_timer, "is_player": self.is_player, "player_id": getattr(self, 'player_id', None), "rect": (self.rect.left, self.rect.top, self.rect.right, self.rect.bottom)})
            except:
                pass
        # Emergency auto-unstuck for player at edge: more aggressive after fix for reported stuck-to-edge bug
        # Previously 90 frames, now 60 frames, push 16px instead of 8, and also clamp to safe zone
        if self.is_player:
            st = getattr(self, 'stuck_timer', 0)
            if st > 45:  # earlier detection (was 90)
                try:
                    # Check if near edge
                    near_edge = (self.rect.left < PLAYFIELD_X + 5 or self.rect.right > PLAYFIELD_X + PLAYFIELD_W - 5 or
                                 self.rect.top < PLAYFIELD_Y + 5 or self.rect.bottom > PLAYFIELD_Y + PLAYFIELD_H - 5)
                    push = 16 if near_edge else 8
                    center_x = PLAYFIELD_X + PLAYFIELD_W // 2
                    center_y = PLAYFIELD_Y + PLAYFIELD_H // 2
                    dx = center_x - self.x
                    dy = center_y - self.y
                    dist = max(1, (dx*dx+dy*dy)**0.5)
                    self.x += (dx/dist) * push
                    self.y += (dy/dist) * push
                    # Hard clamp to ensure inside playfield
                    self.x = max(PLAYFIELD_X + TANK_SIZE//2 + 2, min(PLAYFIELD_X + PLAYFIELD_W - TANK_SIZE//2 - 2, self.x))
                    self.y = max(PLAYFIELD_Y + TANK_SIZE//2 + 2, min(PLAYFIELD_Y + PLAYFIELD_H - TANK_SIZE//2 - 2, self.y))
                    self.rect.center = (self.x, self.y)
                    self.stuck_timer = 0
                    from .logger_integration import safe_log_gameplay
                    safe_log_gameplay("PLAYER_AUTO_UNSTUCK", data={"x": self.x, "y": self.y, "push": push, "near_edge": near_edge, "stuck_timer": st})
                except Exception as e:
                    try:
                        from .logger_integration import safe_log_gameplay
                        safe_log_gameplay("UNSTUCK_FAIL", data={"error": str(e)})
                    except:
                        pass
                    self.stuck_timer = 0

    def update(self, tilemap, other_tanks):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.spawn_protection > 0:
            self.spawn_protection -= 1
        if self.armor_flash_timer > 0:
            self.armor_flash_timer -= 1

        # size effects
        self.update_size_state()

        # venom dissolve over 10s
        if getattr(self, 'venom_timer', 0) > 0:
            self.venom_timer -= 1
            self.venom_level = 1.0 - (self.venom_timer / VENOM_DISSOLVE_TIME)
            if self.venom_timer <= 0:
                # destroyed by venom
                self.alive = False
                self.venom_level = 1.0

        # check ice under
        try:
            gx = int((self.rect.centerx - PLAYFIELD_X) // TILE_SIZE)
            gy = int((self.rect.centery - PLAYFIELD_Y) // TILE_SIZE)
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H and tilemap is not None:
                self.on_ice = tilemap.tiles[gy][gx] == TILE_ICE
            else:
                self.on_ice = False
        except:
            self.on_ice = False

    def take_damage(self, power=1, bullet_type='normal'):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        
        # Armor protection - absorbs damage first
        if hasattr(self, 'armor') and self.armor > 0:
            # Armor absorbs bullet, with flash feedback
            damage_to_armor = power * 25  # each bullet does 25 armor damage base
            # Different bullet types do different armor damage
            # Synergy bullets (power_homing etc) do much more damage
            if bullet_type in ('power_homing', 'power_homing_spread', 'power_spread', 'power_rapid', 'power_spread_rapid'):
                damage_to_armor *= 2.5  # powerful missile synergy = much more armor damage
            elif bullet_type == 'power' or power >= 2:
                damage_to_armor *= 1.5
            elif bullet_type == 'homing':
                damage_to_armor *= 0.8  # homing weaker vs armor (3-4 hits for bricks, less armor damage)
            elif bullet_type == 'rapid':
                damage_to_armor *= 0.6
            elif bullet_type == 'venom':
                damage_to_armor *= 0.5
                # venom bypasses partial armor
                if self.armor > 0:
                    self.armor = max(0, self.armor - damage_to_armor * 0.5)
                    self.armor_flash_timer = 10
                    # Still take partial health damage from venom
                    return True
            
            self.armor = max(0, self.armor - damage_to_armor)
            self.armor_flash_timer = 8
            
            # If armor still has value, it protects - no health damage
            if self.armor > 0:
                # Armor reduced but protects from death
                return False
            else:
                # Armor just broke, but this bullet is absorbed by armor breaking
                self.armor = 0
                return False  # armor sacrifice saves this hit
        
        # No armor left, take real damage
        return True

    def add_armor(self, amount):
        """Add armor via upgrade, capped at max"""
        if not hasattr(self, 'armor'):
            self.armor = 0
        if not hasattr(self, 'max_armor'):
            self.max_armor = ARMOR_MAX_PLAYER if self.is_player else 200
        self.armor = min(self.max_armor, self.armor + amount)
        self.armor_flash_timer = 15
        # Increase max_armor if upgrading beyond current max (for player progression)
        if self.is_player and self.armor >= self.max_armor:
            self.max_armor = min(ARMOR_MAX_PLAYER, self.max_armor + amount // 2)

    def get_armor_percent(self):
        if not hasattr(self, 'max_armor') or self.max_armor == 0:
            return 0
        return max(0, min(1, self.armor / self.max_armor))

    def die(self):
        was_alive = self.alive
        self.alive = False
        if HAS_DEBUG and was_alive:
            try:
                safe_log_gameplay("TANK_DIE", level_idx=-1, player_id=getattr(self, 'player_id', None),
                                  data={"is_player": self.is_player, "x": getattr(self, 'x', 0), "y": getattr(self, 'y', 0),
                                        "grid_x": getattr(self, 'grid_x', -1), "grid_y": getattr(self, 'grid_y', -1),
                                        "armor": getattr(self, 'armor', 0)})
            except:
                pass

    def draw(self, screen, tilemap=None):
        if not self.alive:
            return
        
        # Forest hiding check - if in forest, mostly hide tank
        in_forest = False
        if tilemap and hasattr(tilemap, 'is_in_forest'):
            in_forest = tilemap.is_in_forest(self.x, self.y)
        elif tilemap:
            # fallback check
            gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
            gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                if tilemap.tiles[gy][gx] == TILE_GRASS:
                    in_forest = True
        
        # For enemy tanks in forest: completely hidden
        if in_forest and not self.is_player:
            # Enemy completely hidden in forest - don't draw at all
            return
        
        # For player in forest: show subtle hint (15% visibility)
        forest_alpha = 1.0
        is_player_in_forest = False
        if in_forest and self.is_player:
            is_player_in_forest = True
            forest_alpha = 0.18  # 18% visibility for own tank in forest

        # Venom dissolve visual
        venom_t = getattr(self, 'venom_timer', 0)
        venom_lv = getattr(self, 'venom_level', 0)
        if venom_t > 0 and hasattr(self, 'venom_timer'):
            diss = venom_lv
            if int(pygame.time.get_ticks()/100) % 2 == 0 or diss > 0.5:
                pass

        # If authentic NES sprites available, use them for true retro look matching downloaded_maps
        # This matches General-Sprites.png ripped from NES ROM (yellow player, green P2, silver enemy, red power)
        shield_flicker = self.invulnerable_timer > 0 and (self.invulnerable_timer // 4) % 2 == 0
        if shield_flicker:
            # draw shield (NES had blinking shield)
            pygame.draw.circle(screen, (200,200,200), self.rect.center, TANK_SIZE//2+6, 2)

        # Determine which sprite color to use based on downloaded_maps + original NES sheet
        # P1 = yellow, P2 = green, Enemy basic = silver (gray), fast = gray but faster, power = red, armor = red/purple (we use red)
        # Star levels: for player, increasing power shows bigger gun – we will map level to sprite row
        sprite_color = None
        sprite_level = 0

        # Check for powerup carrier flashing (original NES flashes red/silver) – we already flash red in subclass but here handle base
        is_powerup_flash = getattr(self, 'powerup_carrier', False) and getattr(self, 'flash_timer', 0) % 16 < 8 and hasattr(self, 'flash_timer') and ((self.flash_timer // 8) % 2 == 0) if hasattr(self, 'flash_timer') else False

        if self.is_player:
            # P1 yellow, P2 green
            pid = getattr(self, 'player_id', 1)
            if pid == 1:
                sprite_color = 'yellow'
            else:
                sprite_color = 'green'
            # star level mapping: 0 basic (small gun), 1 fast? Actually armor level shows bigger? Use star_level as level index
            sprite_level = getattr(self, 'star_level', 0)  # 0-3
        else:
            # enemy
            etype = getattr(self, 'enemy_type', 'basic')
            if etype == 'basic':
                sprite_color = 'silver'
                sprite_level = 0
            elif etype == 'fast':
                sprite_color = 'silver'  # same but faster – in NES fast is same gray but we could offset?
                sprite_level = 1
            elif etype == 'power':
                sprite_color = 'red'
                sprite_level = 0
            elif etype == 'armor':
                sprite_color = 'red'
                # armor health 4 -> 1 etc. map to row for visual damage? Use health-1 inverse? Let's use 4-health as level for armor stages
                hp = getattr(self, 'health', 1)
                sprite_level = max(0, 4 - hp)  # 0 = full, 3 = damaged but in NES armor uses same sprite with flashing colors
            else:
                sprite_color = 'silver'

            # flashing red for powerup carrier (like original)
            if getattr(self, 'powerup_carrier', False):
                # original flashes red/silver every 8 frames
                if (getattr(self, 'flash_timer', 0) // 8) % 2 == 0:
                    sprite_color = 'red'

        # Try authentic sprite - now with verified DIR_OFFSETS UP,RIGHT,DOWN,LEFT *2 frames
        if HAS_AUTHENTIC_SPRITES and sprite_color:
            try:
                # Anim frame based on movement (tread animation) - NES toggles every ~8 frames
                anim = 0
                if hasattr(self, 'move_timer') and self.move_timer:
                    # use move_timer // 6 for faster tread like NES (2 frames)
                    anim = (self.move_timer // 6) % 2

                # For authentic retro tanks we also want to mirror powerup flashing like original (red/silver flashing)
                # Already handled color flashing above

                # Get sprite scaled to current size (shrink/giant) - draw slightly smaller than collision rect for visual gap
                scale = getattr(self, 'current_scale', 1.0)
                draw_size = int((TANK_SIZE - 2) * scale)  # 2px smaller than collision rect = 1px gap around
                from ..assets.sprites import get_cached_tank
                spr = get_cached_tank(sprite_color, self.direction, anim, sprite_level, draw_size)
                if spr is None:
                    from ..assets.sprites import get_tank_sprite_scaled as _g
                    spr = _g(sprite_color, self.direction, anim_frame=anim, level=sprite_level, size=draw_size)
                if spr is not None:
                    if shield_flicker and self.invulnerable_timer % 8 < 4:
                        pass
                    else:
                        # Apply venom dissolve alpha
                        venom_t = getattr(self, 'venom_timer', 0)
                        venom_lv = getattr(self, 'venom_level', 0)
                        draw_spr = spr
                        if venom_t > 0:
                            try:
                                tinted = spr.copy()
                                overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
                                alpha = int(120 * min(1.0, venom_lv*1.5 + 0.2))
                                overlay.fill((40, 200, 40, alpha))
                                tinted.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
                                if venom_lv > 0.5:
                                    fade_alpha = int(255 * (1.0 - (venom_lv-0.5)*2))
                                    tinted.set_alpha(max(30, fade_alpha))
                                draw_spr = tinted
                            except:
                                draw_spr = spr
                        
                        # Apply forest hiding alpha - player slightly visible, enemy invisible (already returned above)
                        if is_player_in_forest:
                            try:
                                forest_spr = draw_spr.copy()
                                forest_spr.set_alpha(int(255 * forest_alpha * 0.8))
                                draw_spr = forest_spr
                                # Add subtle leaf rustle indicator
                                if random.random() < 0.1:
                                    rx = self.rect.centerx + random.randint(-4,4)
                                    ry = self.rect.centery + random.randint(-4,4)
                                    pygame.draw.circle(screen, (80,160,30), (rx, ry), 1)
                            except:
                                pass
                        
                        rect = draw_spr.get_rect(center=self.rect.center)
                        screen.blit(draw_spr, rect)

                        if self.is_player:
                            pid = getattr(self, 'player_id', 1)
                            # Use Chad/Lida names instead of P1/P2
                            try:
                                from ..settings import PLAYER_NAMES, get_player_display_name
                                display_name = get_player_display_name(pid)
                            except:
                                display_name = PLAYER_NAMES[pid-1] if 'PLAYER_NAMES' in globals() and 0 <= pid-1 < 2 else (f"Chad" if pid==1 else f"Lida")
                            font = pygame.font.Font(None, 14)
                            # show size effect
                            extra = ""
                            if getattr(self, 'is_giant', False):
                                extra = " GIANT"
                            elif getattr(self, 'is_shrunk', False):
                                extra = " MINI"
                            if venom_t > 0:
                                extra += f" VENOM {venom_t//FPS}s"
                            label = f"{display_name}{extra}"
                            txt = font.render(label, True, COLOR_WHITE if pid==1 else (100,255,100))
                            txt_bg = pygame.Surface((txt.get_width()+4, txt.get_height()+2))
                            txt_bg.fill((0,0,0))
                            # Fix overlap: name higher above armor bar
                            screen.blit(txt_bg, (self.rect.centerx - txt.get_width()//2 -2, self.rect.top - 28))
                            screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.top - 28))

                        # Armor bar for all tanks with armor (player and enemies)
                        if hasattr(self, 'armor') and hasattr(self, 'max_armor') and self.max_armor > 0 and self.armor > 0:
                            bar_w = 24 if self.is_player else 20
                            bar_h = 5 if self.is_player else 4
                            cx = self.rect.centerx
                            # Fix overlap: armor bar just above tank, name is higher at -28, so armor at -12
                            cy = self.rect.top - 12 if self.is_player else self.rect.bottom + 3
                            # Flash white when armor just hit
                            if getattr(self, 'armor_flash_timer', 0) > 0 and self.armor_flash_timer % 4 < 2:
                                bar_col = (255, 255, 255)
                            else:
                                # Color based on armor percent: green -> yellow -> red -> blue for high
                                armor_pct = self.armor / self.max_armor
                                if armor_pct > 0.6:
                                    bar_col = (100, 200, 255)  # blue-ish for high armor
                                elif armor_pct > 0.3:
                                    bar_col = (255, 220, 80)  # yellow for medium
                                else:
                                    bar_col = (255, 100, 100)  # red for low
                            pygame.draw.rect(screen, (0,0,0), (cx-bar_w//2-1, cy-1, bar_w+2, bar_h+2))
                            pygame.draw.rect(screen, (40,40,50), (cx-bar_w//2, cy, bar_w, bar_h))
                            pygame.draw.rect(screen, bar_col, (cx-bar_w//2, cy, int(bar_w * max(0, self.armor/self.max_armor)), bar_h))
                            # Small armor icon
                            if self.is_player:
                                font = pygame.font.Font(None, 12)
                                txt = font.render(f"{int(self.armor)}", True, COLOR_WHITE)
                                screen.blit(txt, (cx + bar_w//2 + 2, cy-2))
                        
                        if getattr(self, 'enemy_type', '') == 'armor' and getattr(self, 'health',1) > 1 and not self.is_player:
                            bar_w = 20
                            bar_h = 4
                            cx = self.rect.centerx
                            cy = self.rect.bottom + 10  # offset below armor bar
                            pygame.draw.rect(screen, (0,0,0), (cx-bar_w//2-1, cy-1, bar_w+2, bar_h+2))
                            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
                            frac = self.health / 4.0
                            col = (int(255*(1-frac)), int(255*frac), 0)
                            pygame.draw.rect(screen, col, (cx-bar_w//2, cy, int(bar_w*frac), bar_h))

                        # Giant aura / shrink sparkles
                        if getattr(self, 'is_giant', False):
                            pygame.draw.rect(screen, (255, 80, 80), self.rect, 2, border_radius=4)
                        if getattr(self, 'is_shrunk', False):
                            for _ in range(2):
                                sx = self.rect.centerx + random.randint(-6,6)
                                sy = self.rect.centery + random.randint(-6,6)
                                pygame.draw.circle(screen, (150, 220, 255), (sx, sy), 1)
                        if venom_t > 0:
                            for i in range(int(3 + venom_lv*4)):
                                sx = self.rect.centerx + random.randint(-8,8)
                                sy = self.rect.bottom - 4 + int(venom_lv*6) + i*3
                                pygame.draw.circle(screen, (60, 200, 60), (sx, sy), max(1, int(3-venom_lv*2)))

                    return
            except Exception as e:
                # fallback to procedural if sprite fails
                # print(f"Sprite draw error {e}")
                pass

        # ---- Fallback procedural retro (if sheet missing) ----
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        size = int((TANK_SIZE - 8) * scale)  # 8px smaller for visual gap

        # Modern simplified fallback that resembles NES yellow/gray etc.
        body_rect = pygame.Rect(0,0,size-4, size-4)
        body_rect.center = (cx, cy)
        pygame.draw.rect(screen, self.color, body_rect)
        pygame.draw.rect(screen, COLOR_BLACK, body_rect, 2)
        # turret - now supports 8 directions
        import math
        cannon_len = 12
        cannon_w = 4
        # Use DIR_ANGLE for cannon direction
        angle_map = DIR_ANGLE if 'DIR_ANGLE' in globals() else {}
        if self.direction in angle_map:
            ang_deg = angle_map[self.direction]
            ang_rad = math.radians(ang_deg - 90)  # UP is -90 deg in math coords? Actually 0 deg UP means pointing up (negative Y)
            # For UP (0 deg), direction vector is (0,-1)
            # Convert: angle 0 = UP, 90=RIGHT, etc. So vector = (sin(angle), -cos(angle))
            vx = math.sin(math.radians(ang_deg))
            vy = -math.cos(math.radians(ang_deg))
            # draw line for cannon
            x2 = cx + vx * (size//2 + 2)
            y2 = cy + vy * (size//2 + 2)
            pygame.draw.line(screen, (30,30,30), (cx, cy), (x2, y2), cannon_w)
        else:
            # fallback cardinal check
            if self.direction == 'UP':
                pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy - size//2, cannon_w, cannon_len))
            elif self.direction == 'DOWN':
                pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy + size//2 - cannon_len, cannon_w, cannon_len))
            elif self.direction == 'LEFT':
                pygame.draw.rect(screen, (30,30,30), (cx - size//2, cy - cannon_w//2, cannon_len, cannon_w))
            elif self.direction == 'RIGHT':
                pygame.draw.rect(screen, (30,30,30), (cx + size//2 - cannon_len, cy - cannon_w//2, cannon_len, cannon_w))
            else:
                # diagonal fallback: draw line using DIRS
                dx, dy = DIRS.get(self.direction, (0,-1))
                x2 = cx + dx * (size//2 + 4)
                y2 = cy + dy * (size//2 + 4)
                pygame.draw.line(screen, (30,30,30), (cx, cy), (x2, y2), cannon_w)

        # turret center
        pygame.draw.circle(screen, (20,20,20), (cx, cy), 4)

        # Armor bar fallback
        if hasattr(self, 'armor') and hasattr(self, 'max_armor') and self.max_armor > 0 and self.armor > 0:
            bar_w = 24
            bar_h = 4
            bx = cx
            by = cy - size//2 - 10
            pygame.draw.rect(screen, (0,0,0), (bx-bar_w//2-1, by-1, bar_w+2, bar_h+2))
            pygame.draw.rect(screen, (40,40,50), (bx-bar_w//2, by, bar_w, bar_h))
            pct = max(0, self.armor / self.max_armor)
            col = (100,200,255) if pct > 0.6 else (255,220,80) if pct > 0.3 else (255,100,100)
            if getattr(self, 'armor_flash_timer', 0) % 4 < 2 and getattr(self, 'armor_flash_timer', 0) > 0:
                col = (255,255,255)
            pygame.draw.rect(screen, col, (bx-bar_w//2, by, int(bar_w*pct), bar_h))

    def draw_forest_hint(self, screen):
        """Draw faint silhouette when player is inside forest for visibility hint"""
        if not self.alive or not self.is_player:
            return
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        size = int((TANK_SIZE - 8) * scale * 0.8)
        # Faint outline + tracks hint
        s = pygame.Surface((size+8, size+8), pygame.SRCALPHA)
        s.fill((0,0,0,0))
        # Draw very faint tank shape
        pygame.draw.rect(s, (*self.color[:3], 60), (4, 4, size, size), border_radius=3)
        # Tracks hint
        pygame.draw.rect(s, (40,40,40, 50), (2, 4, 4, size), border_radius=1)
        pygame.draw.rect(s, (40,40,40, 50), (size+2, 4, 4, size), border_radius=1)
        # Cannon faint
        import math
        ang = DIR_ANGLE.get(self.direction, 0)
        vx = math.sin(math.radians(ang))
        vy = -math.cos(math.radians(ang))
        x2 = size//2 + 4 + vx * (size//2)
        y2 = size//2 + 4 + vy * (size//2)
        pygame.draw.line(s, (30,30,30, 70), (size//2+4, size//2+4), (x2, y2), 2)
        screen.blit(s, (cx - (size+8)//2, cy - (size+8)//2))
        
        # Rustle particles - small leaf movement hint
        if random.random() < 0.15:
            rx = cx + random.randint(-8,8)
            ry = cy + random.randint(-8,8)
            pygame.draw.circle(screen, (90, 180, 50, 120), (rx, ry), 1)
