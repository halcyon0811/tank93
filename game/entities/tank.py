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
        self.direction = dir_name
        dx, dy = DIRS[dir_name]
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed

        # check ice effect - slippery?
        if self.on_ice:
            new_x = self.x + dx * self.speed * 1.3
            new_y = self.y + dy * self.speed * 1.3

        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # bounds
        if new_rect.left < PLAYFIELD_X or new_rect.right > PLAYFIELD_X + PLAYFIELD_W:
            return False
        if new_rect.top < PLAYFIELD_Y or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H:
            return False

        # tile collision
        tiles = tilemap.get_tiles_in_rect(new_rect)
        for ttype, gx, gy, trect in tiles:
            if new_rect.colliderect(trect):
                return False

        # tank-tank collision
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect):
                # small push?
                return False

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
