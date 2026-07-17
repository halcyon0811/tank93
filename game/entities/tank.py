import pygame
import random
from ..settings import *

class Tank:
    def __init__(self, grid_x, grid_y, color, is_player=False):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * TILE_SIZE + TILE_SIZE//2
        self.y = PLAYFIELD_Y + grid_y * TILE_SIZE + TILE_SIZE//2
        # target for smooth movement snapped to tile?
        self.rect = pygame.Rect(0,0,TANK_SIZE-4, TANK_SIZE-4)
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

        self.invulnerable_timer = 0
        self.spawn_protection = 0
        self.on_ice = False

        # animation
        self.move_timer = 0
        self.track_offset = 0

    def set_position(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * TILE_SIZE + TILE_SIZE//2
        self.y = PLAYFIELD_Y + grid_y * TILE_SIZE + TILE_SIZE//2
        self.rect.center = (self.x, self.y)

    def get_bullet_spawn(self):
        cx, cy = self.rect.center
        offset = TANK_SIZE//2 + 4
        if self.direction == 'UP':
            return cx, cy - offset
        if self.direction == 'DOWN':
            return cx, cy + offset
        if self.direction == 'LEFT':
            return cx - offset, cy
        if self.direction == 'RIGHT':
            return cx + offset, cy
        return cx, cy

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

        # Ice effect - authentic: higher speed + slight slide
        speed_mult = 1.35 if self.on_ice else 1.0
        new_x = snap_x + dx * self.speed * speed_mult
        new_y = snap_y + dy * self.speed * speed_mult

        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # bounds - authentic: tanks cannot go outside playfield, allow 4px tolerance for smooth edge movement
        # Original NES allows tank to go slightly outside when spawning
        if new_rect.left < PLAYFIELD_X - 6 or new_rect.right > PLAYFIELD_X + PLAYFIELD_W + 6:
            return False
        if new_rect.top < PLAYFIELD_Y - 6 or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + 6:
            return False

        # tile collision - authentic checks 2 front corners with small tolerance (2px) like original
        # Shrink new_rect slightly for more forgiving collision (original allows 2px overlap)
        check_rect = new_rect.inflate(-4, -4)
        tiles = tilemap.get_tiles_in_rect(check_rect)
        for ttype, gx, gy, trect in tiles:
            if check_rect.colliderect(trect):
                # Try to nudge slightly if turning and close to wall
                if is_turn and (abs(snap_x - self.x) > 0.1 or abs(snap_y - self.y) > 0.1):
                    new_rect2 = self.rect.copy()
                    new_rect2.center = (self.x + dx * self.speed * speed_mult, self.y + dy * self.speed * speed_mult)
                    check_rect2 = new_rect2.inflate(-4, -4)
                    blocked2 = False
                    tiles2 = tilemap.get_tiles_in_rect(check_rect2)
                    for _, _, _, tr2 in tiles2:
                        if check_rect2.colliderect(tr2):
                            blocked2 = True
                            break
                    if not blocked2:
                        snap_x, snap_y = self.x, self.y
                        new_x = self.x + dx * self.speed * speed_mult
                        new_y = self.y + dy * self.speed * speed_mult
                        new_rect = new_rect2
                        check_rect = check_rect2
                    else:
                        return False
                else:
                    return False

        # tank-tank collision - authentic: tanks block each other, no overlap
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            # Slight shrink for more forgiving feel (original has 2px gap)
            if new_rect.colliderect(other.rect.inflate(-2, -2)):
                return False

        # Move successful - apply snap if any
        self.x = new_x
        self.y = new_y
        self.rect.center = (self.x, self.y)
        self.move_timer += 1
        self.track_offset = (self.track_offset + self.speed) % 8
        return True

    def update(self, tilemap, other_tanks):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.spawn_protection > 0:
            self.spawn_protection -= 1

        # check ice under
        gx = int((self.rect.centerx - PLAYFIELD_X) // TILE_SIZE)
        gy = int((self.rect.centery - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            self.on_ice = tilemap.tiles[gy][gx] == TILE_ICE
        else:
            self.on_ice = False

    def take_damage(self, power=1):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        # armor logic in subclass
        return True

    def die(self):
        self.alive = False

    def draw(self, screen):
        if not self.alive:
            return
        # flicker if invulnerable
        if self.invulnerable_timer > 0 and (self.invulnerable_timer // 4) % 2 == 0:
            # draw shield circle instead of flicker hide
            pygame.draw.circle(screen, (80, 180, 255), self.rect.center, TANK_SIZE//2+6, 2)

        cx, cy = self.rect.center
        size = TANK_SIZE - 6

        # shadow
        pygame.draw.rect(screen, (0,0,0, 100), (cx - size//2 +2, cy - size//2 +4, size, size), border_radius=3)

        # tracks
        track_color = (40,40,40)
        pygame.draw.rect(screen, track_color, (cx - size//2 -2, cy - size//2, 6, size), border_radius=2)
        pygame.draw.rect(screen, track_color, (cx + size//2 -4, cy - size//2, 6, size), border_radius=2)
        # track animation dots
        if self.move_timer % 4 == 0:
            pygame.draw.rect(screen, (80,80,80), (cx - size//2, cy - size//2 + int(self.track_offset) % size, 2, 4))
            pygame.draw.rect(screen, (80,80,80), (cx + size//2 -2, cy - size//2 + (int(self.track_offset)+4) % size, 2, 4))

        # body
        body_rect = pygame.Rect(0,0,size-8, size-6)
        body_rect.center = (cx, cy)
        pygame.draw.rect(screen, self.color, body_rect, border_radius=4)
        pygame.draw.rect(screen, (0,0,0), body_rect, 2, border_radius=4)
        # highlight
        pygame.draw.rect(screen, (255,255,255, 120), (body_rect.x+2, body_rect.y+2, body_rect.w-4, 4), border_radius=2)

        # turret/cannon
        cannon_len = 14
        cannon_w = 5
        if self.direction == 'UP':
            pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy - size//2 -2, cannon_w, cannon_len))
            pygame.draw.circle(screen, (20,20,20), (cx, cy), 6)
        elif self.direction == 'DOWN':
            pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy + size//2 - cannon_len +2, cannon_w, cannon_len))
            pygame.draw.circle(screen, (20,20,20), (cx, cy), 6)
        elif self.direction == 'LEFT':
            pygame.draw.rect(screen, (30,30,30), (cx - size//2 -2, cy - cannon_w//2, cannon_len, cannon_w))
            pygame.draw.circle(screen, (20,20,20), (cx, cy), 6)
        elif self.direction == 'RIGHT':
            pygame.draw.rect(screen, (30,30,30), (cx + size//2 - cannon_len +2, cy - cannon_w//2, cannon_len, cannon_w))
            pygame.draw.circle(screen, (20,20,20), (cx, cy), 6)

        # player indicator
        if self.is_player:
            pid = getattr(self, 'player_id', 1)
            # small crown
            font = pygame.font.Font(None, 16)
            txt = font.render(f"P{pid}", True, COLOR_WHITE)
            screen.blit(txt, (cx-6, cy - size//2 -14))

        # flash for high power gun
        if self.bullet_power >= 2:
            pygame.draw.circle(screen, COLOR_YELLOW, (cx, cy), 3)
