import pygame
import math
from ..settings import *

class Bullet:
    def __init__(self, x, y, direction, owner, power=1, color=None, homing=False):
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
        # homing missile support
        self.homing = homing
        self.target = None
        self.vx, self.vy = DIRS.get(direction, (0, -1))
        # Normalize diagonal
        if self.vx != 0 and self.vy != 0:
            norm = math.hypot(self.vx, self.vy)
            self.vx /= norm
            self.vy /= norm
        self.turn_speed = 0.18 if homing else 0
        if homing:
            self.speed = BULLET_SPEED * 1.15
            # make homing more visible
            if color is None or color == COLOR_WHITE:
                self.color = (255, 140, 0)  # orange missile
            self.trail_max = 10
        else:
            self.trail_max = 6

    def _find_nearest_target(self, tanks):
        """Find nearest enemy for homing missile"""
        if not self.homing:
            return None
        candidates = []
        if self.owner.startswith('player'):
            # target nearest enemy
            for t in tanks:
                if t.alive and not t.is_player:
                    candidates.append(t)
        else:
            # enemy homing (if ever) targets player
            for t in tanks:
                if t.alive and t.is_player:
                    candidates.append(t)
        if not candidates:
            return None
        # find closest by distance
        nearest = min(candidates, key=lambda tank: math.hypot(tank.x - self.x, tank.y - self.y))
        return nearest

    def _update_homing(self, tanks):
        if not self.homing:
            return
        # Acquire target if none or dead
        if self.target is None or not getattr(self.target, 'alive', False):
            self.target = self._find_nearest_target(tanks)
        if self.target is None:
            return
        # Compute direction to target
        tx, ty = self.target.x, self.target.y
        # Add slight prediction? Simple straight
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        dx /= dist
        dy /= dist
        # Steer towards target (lerp)
        self.vx = self.vx * (1 - self.turn_speed) + dx * self.turn_speed
        self.vy = self.vy * (1 - self.turn_speed) + dy * self.turn_speed
        # Renormalize
        norm = math.hypot(self.vx, self.vy)
        if norm > 0:
            self.vx /= norm
            self.vy /= norm
        # Update dir string for brick destruction based on dominant direction
        # Choose closest 8-dir
        best = None
        best_dot = -2
        for dname, (ddx, ddy) in DIRS.items():
            # normalize ddx,ddy
            ndx, ndy = ddx, ddy
            if ndx != 0 and ndy != 0:
                nlen = math.hypot(ndx, ndy)
                ndx /= nlen
                ndy /= nlen
            dot = self.vx * ndx + self.vy * ndy
            if dot > best_dot:
                best_dot = dot
                best = dname
        if best:
            self.dir = best

    def update(self, tilemap, tanks, base):
        if not self.alive:
            return None

        # homing steering
        if self.homing:
            self._update_homing(tanks)

        # move - use vx,vy for homing, else use DIRS[dir]
        if self.homing:
            self.x += self.vx * self.speed
            self.y += self.vy * self.speed
        else:
            dx, dy = DIRS.get(self.dir, (0, -1))
            # Normalize diagonal for consistent speed if not homing
            if dx != 0 and dy != 0:
                norm = math.hypot(dx, dy)
                dx /= norm
                dy /= norm
            self.x += dx * self.speed
            self.y += dy * self.speed
        self.rect.center = (self.x, self.y)

        # trail - longer for homing missile
        self.trail.append((self.x, self.y))
        max_t = getattr(self, 'trail_max', 6)
        if len(self.trail) > max_t:
            self.trail.pop(0)

        # bounds
        if (self.x < PLAYFIELD_X or self.x > PLAYFIELD_X + PLAYFIELD_W or
            self.y < PLAYFIELD_Y or self.y > PLAYFIELD_Y + PLAYFIELD_H):
            self.alive = False
            return 'out'

        # tile collision - authentic NES sounds + direction-aware brick destruction (35 maps)
        # Remote had direction-aware: destroy_tile(gx, gy, power, dir) -> our tilemap supports both signatures
        gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
        gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            tt = tilemap.tiles[gy][gx]
            if tt == TILE_BRICK:
                # Try direction-aware first (origin), fallback to old signature
                destroyed = False
                try:
                    destroyed = tilemap.destroy_tile(gx, gy, self.power, self.dir)
                except TypeError:
                    destroyed = tilemap.destroy_tile(gx, gy, self.power)
                self.alive = False
                try:
                    from ..sound_manager import sound_manager
                    if destroyed:
                        sound_manager.play_brick_break()
                    else:
                        sound_manager.play_hit_brick()
                    sound_manager.brick_break_count += 1
                except:
                    pass
                return 'hit_brick'
            elif tt == TILE_STEEL:
                destroyed = False
                if self.power >= 2:
                    try:
                        destroyed = tilemap.destroy_tile(gx, gy, self.power, self.dir)
                    except TypeError:
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
            # water, grass, ice pass through

        # base collision
        if base and base.alive:
            if base.rect.collidepoint(self.x, self.y):
                base.take_damage()
                self.alive = False
                try:
                    from ..sound_manager import sound_manager
                    sound_manager.play_explosion(big=True)
                except:
                    pass
                return 'hit_base'

        # tank collision + explosion SFX (authentic NES - 35 maps same SFX across all stages)
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
                    self.alive = False
                    try:
                        from ..sound_manager import sound_manager
                        sound_manager.play_hit_brick()
                    except:
                        pass
                    return 'blocked'
                self.alive = False
                try:
                    from ..sound_manager import sound_manager
                    if not tank.alive:
                        sound_manager.play_explosion(big=(getattr(tank, 'enemy_type','')=='armor'))
                except:
                    pass
                return 'hit_tank'

        return None

    def draw(self, screen):
        if not self.alive:
            return
        # trail - homing has orange flame trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / len(self.trail) if self.trail else 0
            size = int((BULLET_SIZE+2) * alpha)
            if size > 0:
                if self.homing:
                    # orange flame fading
                    r = int(255 * alpha + 100 * (1-alpha))
                    g = int(140 * alpha + 50 * (1-alpha))
                    b = 0
                    pygame.draw.circle(screen, (r, g, b), (int(tx), int(ty)), size//2 + 1)
                else:
                    pygame.draw.circle(screen, (100, 100, 100), (int(tx), int(ty)), size//2)
        # bullet body
        if self.homing:
            # missile shape: elongated with direction
            # draw as small rocket with flame
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), BULLET_SIZE//2 + 3)
            pygame.draw.circle(screen, (255, 220, 0), (int(self.x), int(self.y)), BULLET_SIZE//2 + 1)
            # direction indicator line
            if hasattr(self, 'vx'):
                lx = int(self.x - self.vx * 8)
                ly = int(self.y - self.vy * 8)
                pygame.draw.line(screen, (255, 80, 0), (int(self.x), int(self.y)), (lx, ly), 2)
        else:
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
            pygame.draw.rect(screen, (230, 230, 230), self.rect)
            pygame.draw.rect(screen, (180, 180, 180), self.rect, 3)
            cx = self.rect.centerx
            cy = self.rect.centery
            pygame.draw.polygon(screen, (50, 50, 50), [
                (cx-12, cy-4), (cx-4, cy-8), (cx-2, cy), (cx-8, cy+6)
            ])
            pygame.draw.polygon(screen, (50, 50, 50), [
                (cx+12, cy-4), (cx+4, cy-8), (cx+2, cy), (cx+8, cy+6)
            ])
            pygame.draw.circle(screen, (255, 220, 0), (cx, cy-2), 6)
            pygame.draw.circle(screen, COLOR_BLACK, (cx+2, cy-4), 2)
            pygame.draw.rect(screen, (200, 50, 50), (cx-10, cy+8, 20, 4))
        else:
            pygame.draw.rect(screen, (60, 20, 20), self.rect)
            t = pygame.time.get_ticks()
            flame_h = 10 + (t % 500) // 100 * 2
            pygame.draw.polygon(screen, (255, 100, 0), [
                (self.rect.centerx, self.rect.top - flame_h),
                (self.rect.left+5, self.rect.top+5),
                (self.rect.right-5, self.rect.top+5),
            ])
