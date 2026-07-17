import pygame
import math
from ..settings import *

class Bullet:
    def __init__(self, x, y, direction, owner, power=1, color=None):
        self.x = x
        self.y = y
        self.dir = direction
        self.owner = owner  # 'player1', 'player2', 'enemy'
        self.power = power
        self.color = color or COLOR_WHITE
        self.speed = BULLET_SPEED
        if power >= 2:
            self.speed = BULLET_SPEED * 1.3

        self.alive = True
        self.rect = pygame.Rect(x - BULLET_SIZE//2, y - BULLET_SIZE//2, BULLET_SIZE, BULLET_SIZE)

        # trail
        self.trail = []

    def update(self, tilemap, tanks, base):
        if not self.alive:
            return None

        # move
        dx, dy = DIRS[self.dir]
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.rect.center = (self.x, self.y)

        # trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)

        # bounds
        if (self.x < PLAYFIELD_X or self.x > PLAYFIELD_X + PLAYFIELD_W or
            self.y < PLAYFIELD_Y or self.y > PLAYFIELD_Y + PLAYFIELD_H):
            self.alive = False
            return 'out'

        # tile collision - authentic NES sounds: brick break crack, steel clang, forest cut (no sound), etc.
        gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
        gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            tt = tilemap.tiles[gy][gx]
            if tt == TILE_BRICK:
                destroyed = tilemap.destroy_tile(gx, gy, self.power)
                self.alive = False
                # SFX: brick break vs hit
                try:
                    from ..sound_manager import sound_manager
                    if destroyed:
                        sound_manager.play_brick_break()
                    else:
                        sound_manager.play_hit_brick()
                    # Update tile type score: Battle City brick break count kept? Our maps count bricks across 35 stages
                    sound_manager.brick_break_count += 1
                except:
                    pass
                return 'hit_brick'
            elif tt == TILE_STEEL:
                destroyed = False
                if self.power >= 2:
                    destroyed = tilemap.destroy_tile(gx, gy, self.power)
                self.alive = False
                try:
                    from ..sound_manager import sound_manager
                    sound_manager.play_hit_steel()
                    if destroyed:
                        sound_manager.play_brick_break()
                except:
                    pass
                return 'hit_steel'

        # base collision
        if base and base.alive:
            if base.rect.collidepoint(self.x, self.y):
                base.take_damage()
                self.alive = False
                return 'hit_base'

        # tank collision + explosion SFX (authentic NES)
        for tank in tanks:
            if not tank.alive or tank.invulnerable_timer > 0:
                continue
            if self.owner.startswith('player') and tank.is_player:
                if getattr(tank, 'player_id', None) and self.owner == f"player{tank.player_id}":
                    continue
                if tank.is_player:
                    continue
            if self.owner == 'enemy' and not tank.is_player:
                continue

            if tank.rect.collidepoint(self.x, self.y):
                if not tank.take_damage(self.power):
                    # blocked by armor/helmet - play hit sound
                    self.alive = False
                    try:
                        from ..sound_manager import sound_manager
                        sound_manager.play_hit_brick()  # blocked = same as hit
                    except:
                        pass
                    return 'blocked'
                self.alive = False
                # Play explosion for tank hit
                try:
                    from ..sound_manager import sound_manager
                    # If armor tank that flashes (original had 4 hits), play hit not full explosion? But tank will be dead only when health 0, particle handles
                    if not tank.alive:
                        sound_manager.play_explosion(big=(getattr(tank, 'enemy_type','')=='armor'))
                except:
                    pass
                return 'hit_tank'

        return None

    def draw(self, screen):
        if not self.alive:
            return
        # trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / len(self.trail)
            size = int(BULLET_SIZE * alpha)
            if size > 0:
                pygame.draw.circle(screen, (100, 100, 100), (int(tx), int(ty)), size//2)
        # bullet body
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), BULLET_SIZE//2 + 2)
        pygame.draw.circle(screen, COLOR_WHITE, (int(self.x), int(self.y)), BULLET_SIZE//2)
        if self.power >= 2:
            pygame.draw.circle(screen, COLOR_YELLOW, (int(self.x), int(self.y)), BULLET_SIZE//2 -1)

# Base/Eagle class also here for convenience
class Base:
    def __init__(self):
        bx, by = BASE_POS
        self.grid_x = bx
        self.grid_y = by
        self.x = PLAYFIELD_X + bx * TILE_SIZE
        self.y = PLAYFIELD_Y + by * TILE_SIZE
        self.alive = True
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE*2, TILE_SIZE*2)
        self.destroyed_timer = 0

    def take_damage(self):
        self.alive = False
        self.destroyed_timer = pygame.time.get_ticks()

    def reset(self):
        self.alive = True
        self.destroyed_timer = 0

    def draw(self, screen):
        if self.alive:
            # modernized eagle/base
            # main body
            pygame.draw.rect(screen, (230, 230, 230), self.rect)
            pygame.draw.rect(screen, (180, 180, 180), self.rect, 3)
            # eagle emblem simplified
            cx = self.rect.centerx
            cy = self.rect.centery
            # wings
            pygame.draw.polygon(screen, (50, 50, 50), [
                (cx-12, cy-4), (cx-4, cy-8), (cx-2, cy), (cx-8, cy+6)
            ])
            pygame.draw.polygon(screen, (50, 50, 50), [
                (cx+12, cy-4), (cx+4, cy-8), (cx+2, cy), (cx+8, cy+6)
            ])
            # head
            pygame.draw.circle(screen, (255, 220, 0), (cx, cy-2), 6)
            pygame.draw.circle(screen, COLOR_BLACK, (cx+2, cy-4), 2)
            # flag colors
            pygame.draw.rect(screen, (200, 50, 50), (cx-10, cy+8, 20, 4))
        else:
            # destroyed - burning
            pygame.draw.rect(screen, (60, 20, 20), self.rect)
            # flicker flame
            t = pygame.time.get_ticks()
            flame_h = 10 + (t % 500) // 100 * 2
            pygame.draw.polygon(screen, (255, 100, 0), [
                (self.rect.centerx, self.rect.top - flame_h),
                (self.rect.left+5, self.rect.top+5),
                (self.rect.right-5, self.rect.top+5),
            ])
