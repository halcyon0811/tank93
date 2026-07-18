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

# Base/Monster class - now a monster to protect, when hit releases boss
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
        # Monster specific
        self.is_monster = True
        self.monster_released = False
        self.release_animation_timer = 0
        self.monster_type = 'cage_monster'  # cute monster in cage

    def take_damage(self):
        if not self.alive:
            return False
        self.alive = False
        self.monster_released = True
        self.destroyed_timer = pygame.time.get_ticks()
        self.release_animation_timer = pygame.time.get_ticks()
        return True  # indicates boss should be spawned

    def reset(self):
        self.alive = True
        self.monster_released = False
        self.destroyed_timer = 0
        self.release_animation_timer = 0

    def draw(self, screen):
        if self.alive:
            # Draw monster in cage - to protect
            # Cage background - dark with bars
            pygame.draw.rect(screen, (30, 20, 10), self.rect)  # cage dark brown
            pygame.draw.rect(screen, (80, 60, 30), self.rect, 4)  # cage border
            # Bars - vertical
            for i in range(3):
                bx = self.rect.left + 8 + i*14
                pygame.draw.rect(screen, (120, 90, 40), (bx, self.rect.top+2, 4, self.rect.height-4))
            # Horizontal bars
            pygame.draw.rect(screen, (120, 90, 40), (self.rect.left, self.rect.top+14, self.rect.width, 3))
            pygame.draw.rect(screen, (120, 90, 40), (self.rect.left, self.rect.bottom-16, self.rect.width, 3))

            # Monster inside - cute blob
            cx = self.rect.centerx
            cy = self.rect.centery + 2
            t = pygame.time.get_ticks()
            bob = int(2 * pygame.math.Vector2(0,1).rotate(t//200).y) if False else (t//200)%4 -2  # small bob
            # Monster body - round, color changing slightly
            monster_color = (100, 200, 80)  # green monster
            # Body shadow
            pygame.draw.ellipse(screen, (60, 120, 40), (cx-16, cy-8+bob, 32, 26))
            # Main body
            pygame.draw.ellipse(screen, monster_color, (cx-14, cy-10+bob, 28, 22))
            # Eyes - big cute
            eye_y = cy - 4 + bob
            # White eyes
            pygame.draw.circle(screen, (255,255,255), (cx-6, eye_y), 5)
            pygame.draw.circle(screen, (255,255,255), (cx+6, eye_y), 5)
            # Pupils - look around slightly
            px_offset = int(2 * (t % 2000) / 2000) -1
            # Simple tracking - pupils follow time
            pupil_x = int((t//300) % 3) -1
            pygame.draw.circle(screen, (0,0,0), (cx-6+pupil_x, eye_y), 2)
            pygame.draw.circle(screen, (0,0,0), (cx+6+pupil_x, eye_y), 2)
            # Mouth - small
            pygame.draw.arc(screen, (0,0,0), (cx-6, eye_y+2, 12, 8), 0, 3.14, 2)
            # Small horns
            pygame.draw.polygon(screen, (200, 50, 50), [(cx-12, cy-10+bob), (cx-10, cy-18+bob), (cx-6, cy-10+bob)])
            pygame.draw.polygon(screen, (200, 50, 50), [(cx+6, cy-10+bob), (cx+10, cy-18+bob), (cx+12, cy-10+bob)])
            # Label "PROTECT ME!"
            font = pygame.font.Font(None, 14)
            txt = font.render("PROTECT", True, (255,255,100))
            screen.blit(txt, (cx-18, self.rect.top-16))
        else:
            # Monster released - broken cage, maybe particle hint
            # Broken cage background
            pygame.draw.rect(screen, (40, 20, 10), self.rect)
            # Broken bars - diagonal
            t = pygame.time.get_ticks()
            # Flicker to show release
            if (t // 100) % 2 == 0:
                pygame.draw.rect(screen, (80, 40, 20), self.rect, 2)
            # Draw broken bars scattered
            for i in range(3):
                bx = self.rect.left + 6 + i*16
                # broken - tilted
                pygame.draw.line(screen, (120, 90, 40), (bx, self.rect.top+2), (bx+4, self.rect.bottom-2), 3)
            # Release effect - "!" and smoke
            cx = self.rect.centerx
            cy = self.rect.centery
            # Smoke puff where monster was
            elapsed = t - self.release_animation_timer
            if elapsed < 1000:
                # Expanding smoke
                radius = int(elapsed / 50)
                alpha = max(0, 200 - elapsed//5)
                # Simulate smoke with circles
                for j in range(3):
                    sx = cx + (j-1)*8
                    sy = cy - radius//2
                    pygame.draw.circle(screen, (100,100,100), (sx, sy), max(2, radius//3))
                # Text "RELEASED!"
                font = pygame.font.Font(None, 20)
                txt = font.render("RELEASED!", True, (255,50,50))
                screen.blit(txt, (cx-30, self.rect.top-20 - radius//2))
            else:
                # Empty cage with broken sign
                font = pygame.font.Font(None, 16)
                txt = font.render("EMPTY", True, (150,150,150))
                screen.blit(txt, (cx-16, cy-4))
