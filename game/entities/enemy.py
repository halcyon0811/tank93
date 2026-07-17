import pygame
import random
import math
import heapq
from .tank import Tank
from .bullet import Bullet
from ..settings import *

def a_star_big_tile(tilemap, start_bx, start_by, target_bx, target_by, ignore_brick_cost=False):
    """A* on 13x13 big tile grid for authentic but smart base rush."""
    def is_blocked_big(bx, by):
        if not (0 <= bx < 13 and 0 <= by < 13):
            return True, 999
        brick_count = 0
        for dy in range(2):
            for dx in range(2):
                sx = bx*2 + dx
                sy = by*2 + dy
                if 0 <= sx < GRID_W and 0 <= sy < GRID_H:
                    t = tilemap.tiles[sy][sx]
                    if t == TILE_STEEL:
                        return True, 999
                    if t == TILE_BRICK:
                        brick_count += 1
        cost = 1 + brick_count * 1.5
        water_count = 0
        for dy in range(2):
            for dx in range(2):
                sx = bx*2 + dx
                sy = by*2 + dy
                if 0 <= sx < GRID_W and 0 <= sy < GRID_H:
                    if tilemap.tiles[sy][sx] == TILE_WATER:
                        water_count += 1
        if water_count >= 2:
            return True, 999
        return False, cost

    open_set = []
    heapq.heappush(open_set, (0, 0, start_bx, start_by, None))
    came_from = {}
    g_score = {(start_bx, start_by): 0}
    closed = set()
    max_nodes = 200
    nodes_expanded = 0

    while open_set and nodes_expanded < max_nodes:
        f, g, bx, by, parent = heapq.heappop(open_set)
        if (bx, by) in closed:
            continue
        came_from[(bx, by)] = parent
        closed.add((bx, by))
        nodes_expanded += 1

        if bx == target_bx and by == target_by:
            path = []
            cur = (bx, by)
            while cur is not None:
                path.append(cur)
                cur = came_from.get(cur)
            path.reverse()
            return path

        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nbx, nby = bx+dx, by+dy
            if not (0 <= nbx < 13 and 0 <= nby < 13):
                continue
            if (nbx, nby) in closed:
                continue
            blocked, cost = is_blocked_big(nbx, nby)
            if blocked:
                continue
            new_g = g + cost
            h = abs(nbx - target_bx) + abs(nby - target_by)
            new_f = new_g + h
            if (nbx, nby) not in g_score or new_g < g_score[(nbx, nby)]:
                g_score[(nbx, nby)] = new_g
                heapq.heappush(open_set, (new_f, new_g, nbx, nby, (bx, by)))

    return None

def direction_from_big_path(start_bx, start_by, next_bx, next_by):
    if next_bx > start_bx:
        return 'RIGHT'
    if next_bx < start_bx:
        return 'LEFT'
    if next_by > start_by:
        return 'DOWN'
    if next_by < start_by:
        return 'UP'
    return None

class EnemyTank(Tank):
    def __init__(self, grid_x, grid_y, enemy_type='basic'):
        color = ENEMY_COLORS.get(enemy_type, ENEMY_COLORS['basic'])
        super().__init__(grid_x, grid_y, color, is_player=False)
        self.enemy_type = enemy_type
        self.direction = 'DOWN'
        self.is_player = False

        if enemy_type == 'basic':
            self.speed = TANK_SPEED['enemy']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 100
            self.shoot_chance = 0.018
        elif enemy_type == 'fast':
            self.speed = TANK_SPEED['fast']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 200
            self.shoot_chance = 0.025
        elif enemy_type == 'power':
            self.speed = TANK_SPEED['enemy'] * 1.1
            self.health = 1
            self.bullet_power = 1
            self.score_value = 300
            self.shoot_chance = 0.045
        elif enemy_type == 'armor':
            self.speed = TANK_SPEED['enemy'] * 0.75
            self.health = 4
            self.bullet_power = 1
            self.score_value = 400
            self.shoot_chance = 0.020

        self.spawn_protection = 60
        self.invulnerable_timer = 60
        self.powerup_carrier = random.random() < 0.25

        self.state = 'wander'
        self.target_dir_timer = 0
        self.stuck_timer = 0
        self.last_pos = (self.x, self.y)
        self.flash_timer = 0
        self.target_player_id = None
        self.base_attack_cooldown = 0
        self.path = []
        self.path_timer = 0
        self.path_target = None

    def can_move_dir(self, dir_name, tilemap, other_tanks, ignore_brick=False):
        dx, dy = DIRS[dir_name]
        test_x = self.x + dx * self.speed
        test_y = self.y + dy * self.speed
        new_rect = self.rect.copy()
        new_rect.center = (test_x, test_y)

        if new_rect.left < PLAYFIELD_X - 6 or new_rect.right > PLAYFIELD_X + PLAYFIELD_W + 6:
            return False
        if new_rect.top < PLAYFIELD_Y - 6 or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + 6:
            return False

        check_rect = new_rect.inflate(-4, -4)
        tiles = tilemap.get_tiles_in_rect(check_rect)
        for ttype, gx, gy, trect in tiles:
            if not check_rect.colliderect(trect):
                continue
            if ignore_brick and ttype == TILE_BRICK:
                continue
            return False

        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect.inflate(-4, -4)):
                return False
        return True

    def get_blocking_tile_type(self, dir_name, tilemap):
        dx, dy = DIRS[dir_name]
        test_x = self.x + dx * (TANK_SIZE//2 + 8)
        test_y = self.y + dy * (TANK_SIZE//2 + 8)
        gx = int((test_x - PLAYFIELD_X) // TILE_SIZE)
        gy = int((test_y - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            return tilemap.tiles[gy][gx]
        return None

    def has_line_of_sight(self, target_x, target_y, tilemap):
        if abs(target_x - self.x) > 12 and abs(target_y - self.y) > 12:
            return False, None

        if abs(target_x - self.x) < 14:
            step_y = 1 if target_y > self.y else -1
            y = int(self.y + step_y * (TANK_SIZE//2 + 2))
            target_y_int = int(target_y)
            while (step_y > 0 and y < target_y_int) or (step_y < 0 and y > target_y_int):
                gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
                gy = int((y - PLAYFIELD_Y) // TILE_SIZE)
                if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                    tt = tilemap.tiles[gy][gx]
                    if tt == TILE_STEEL:
                        return False, TILE_STEEL
                    if tt == TILE_BRICK:
                        return True, TILE_BRICK
                y += step_y * TILE_SIZE
            return True, None
        elif abs(target_y - self.y) < 14:
            step_x = 1 if target_x > self.x else -1
            x = int(self.x + step_x * (TANK_SIZE//2 + 2))
            target_x_int = int(target_x)
            while (step_x > 0 and x < target_x_int) or (step_x < 0 and x > target_x_int):
                gx = int((x - PLAYFIELD_X) // TILE_SIZE)
                gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
                if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                    tt = tilemap.tiles[gy][gx]
                    if tt == TILE_STEEL:
                        return False, TILE_STEEL
                    if tt == TILE_BRICK:
                        return True, TILE_BRICK
                x += step_x * TILE_SIZE
            return True, None
        return False, None

    def update_ai(self, tilemap, players, other_tanks, bullets_list, base=None):
        if not self.alive:
            return None

        self.flash_timer += 1
        self.target_dir_timer -= 1
        if self.base_attack_cooldown > 0:
            self.base_attack_cooldown -= 1

        dist = math.hypot(self.x - self.last_pos[0], self.y - self.last_pos[1])
        if dist < 0.8:
            self.stuck_timer += 1
        else:
            self.stuck_timer = 0
        self.last_pos = (self.x, self.y)

        # --- Fix for enemy stuck bug: detect overlapping tanks and force separation ---
        # When two enemies spawn too close or get stuck overlapping each other (same position),
        # their normal can_move_dir check will block all directions because they overlap.
        # This causes them to stay forever in original location. We force separation.
        overlapping_tanks = []
        for other in (other_tanks + players):
            if other is self or not other.alive:
                continue
            d = math.hypot(self.x - other.x, self.y - other.y)
            if d < TANK_SIZE * 0.95:  # overlapping / too close
                overlapping_tanks.append((other, d))

        if overlapping_tanks:
            # Find nearest overlapping
            nearest, _ = min(overlapping_tanks, key=lambda x: x[1])
            dx = self.x - nearest.x
            dy = self.y - nearest.y
            # Choose direction away from nearest
            if abs(dx) > abs(dy):
                dir_away = 'RIGHT' if dx > 0 else 'LEFT'
            else:
                dir_away = 'DOWN' if dy > 0 else 'UP'
            self.direction = dir_away
            self.target_dir_timer = 15
            # Try to move ignoring other tanks for separation (only tile collision)
            # We directly call base try_move with empty other list to allow separation
            moved_sep = super().try_move(dir_away, tilemap, [])
            if not moved_sep:
                # If still blocked by tile, try perpendicular away directions
                perp = {'UP': ['LEFT','RIGHT'], 'DOWN': ['LEFT','RIGHT'], 'LEFT': ['UP','DOWN'], 'RIGHT': ['UP','DOWN']}
                for pd in perp.get(dir_away, []):
                    if super().try_move(pd, tilemap, []):
                        self.direction = pd
                        moved_sep = True
                        break
            # If still overlapping heavily, give a small push to unstick (teleport slightly)
            if math.hypot(self.x - nearest.x, self.y - nearest.y) < TANK_SIZE * 0.8:
                # push 2px away
                push_dx = (dx / (math.hypot(dx, dy) or 1)) * 2.5
                push_dy = (dy / (math.hypot(dx, dy) or 1)) * 2.5
                self.x += push_dx
                self.y += push_dy
                self.rect.center = (self.x, self.y)

        if self.target_dir_timer <= 0 or self.stuck_timer > 25:
            self.choose_new_direction(players, tilemap, base)
            self.target_dir_timer = random.randint(25, 90)
            if self.stuck_timer > 25:
                self.target_dir_timer = random.randint(10, 30)
            self.stuck_timer = 0

        moved = self.try_move(self.direction, tilemap, other_tanks + players)
        if not moved:
            block_type = self.get_blocking_tile_type(self.direction, tilemap)
            if block_type == TILE_BRICK:
                if random.random() < 0.7 and self.can_shoot():
                    new_b = self.shoot()
                    if new_b:
                        bullets_list.append(new_b)
                        self.base_attack_cooldown = 20
            perp = {'UP': ['LEFT','RIGHT'], 'DOWN': ['LEFT','RIGHT'], 'LEFT': ['UP','DOWN'], 'RIGHT': ['UP','DOWN']}
            for pd in perp.get(self.direction, []):
                if self.can_move_dir(pd, tilemap, other_tanks + players, ignore_brick=True):
                    self.direction = pd
                    self.target_dir_timer = random.randint(20, 60)
                    break
            else:
                self.target_dir_timer = 0
        else:
            if self.state in ('chase_base', 'attack_base') and base and base.alive:
                ahead_type = self.get_blocking_tile_type(self.direction, tilemap)
                if ahead_type == TILE_BRICK and random.random() < 0.15:
                    if self.can_shoot():
                        nb = self.shoot()
                        if nb:
                            bullets_list.append(nb)

        new_bullet = None
        aligned_target = None
        is_base = False
        if base and base.alive:
            base_x, base_y = base.rect.centerx, base.rect.centery
            dist_to_base = math.hypot(base_x - self.x, base_y - self.y)
            if dist_to_base < 8 * TILE_SIZE or self.state == 'attack_base':
                los, block_type = self.has_line_of_sight(base_x, base_y, tilemap)
                if los:
                    aligned_target = (base_x, base_y)
                    is_base = True
                    self.state = 'attack_base'

        if aligned_target is None:
            for p in players:
                if not p.alive:
                    continue
                los, _ = self.has_line_of_sight(p.rect.centerx, p.rect.centery, tilemap)
                if los:
                    if abs(p.x - self.x) < 16 and ((self.direction == 'DOWN' and p.y > self.y) or (self.direction == 'UP' and p.y < self.y)):
                        aligned_target = (p.rect.centerx, p.rect.centery)
                        break
                    if abs(p.y - self.y) < 16 and ((self.direction == 'RIGHT' and p.x > self.x) or (self.direction == 'LEFT' and p.x < self.x)):
                        aligned_target = (p.rect.centerx, p.rect.centery)
                        break

        shoot_chance = self.shoot_chance
        if aligned_target:
            shoot_chance *= 4.5
            if is_base:
                shoot_chance *= 1.5
        if base and self.state == 'attack_base':
            shoot_chance *= 1.8

        if random.random() < shoot_chance and self.base_attack_cooldown == 0:
            new_bullet = self.shoot()
            if new_bullet:
                bullets_list.append(new_bullet)
                if is_base:
                    self.base_attack_cooldown = 30

        super().update(tilemap, other_tanks + players)
        self.bullets = [b for b in self.bullets if b.alive]
        return new_bullet

    def choose_new_direction(self, players, tilemap, base=None):
        possible = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        opposite = {'UP':'DOWN','DOWN':'UP','LEFT':'RIGHT','RIGHT':'LEFT'}

        if self.direction in opposite and self.stuck_timer < 15:
            rev = opposite[self.direction]
            if rev in possible and random.random() < 0.85:
                possible.remove(rev)

        target_x, target_y = None, None
        target_bx, target_by = None, None
        alive_players = [p for p in players if p.alive] if players else []

        use_base = True
        if base and base.alive:
            base_cx, base_cy = base.rect.centerx, base.rect.centery
            dist_to_base = math.hypot(base_cx - self.x, base_cy - self.y)
            if alive_players:
                closest_p = min(alive_players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
                dist_to_player = math.hypot(closest_p.x - self.x, closest_p.y - self.y)
                if dist_to_player < 4 * TILE_SIZE:
                    use_base = random.random() < 0.4
                elif dist_to_player < 8 * TILE_SIZE:
                    use_base = random.random() < 0.65
                else:
                    use_base = random.random() < 0.75
            if dist_to_base < 5 * TILE_SIZE:
                use_base = True
                self.state = 'attack_base'
            elif dist_to_base > 12 * TILE_SIZE:
                self.state = 'wander' if random.random() < 0.5 else 'chase_base'
        else:
            use_base = False

        if use_base and base and base.alive:
            target_x, target_y = base.rect.centerx, base.rect.centery
            target_bx = int((target_x - PLAYFIELD_X) // TILE_SIZE) // 2
            target_by = int((target_y - PLAYFIELD_Y) // TILE_SIZE) // 2
            self.state = 'chase_base'
            if dist_to_base < 5 * TILE_SIZE:
                self.state = 'attack_base'
        elif alive_players:
            closest = min(alive_players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
            target_x, target_y = closest.rect.centerx, closest.rect.centery
            target_bx = int((target_x - PLAYFIELD_X) // TILE_SIZE) // 2
            target_by = int((target_y - PLAYFIELD_Y) // TILE_SIZE) // 2
            self.target_player_id = closest.player_id
            self.state = 'chase_player'
        else:
            self.state = 'wander'
            self.direction = random.choice(possible)
            return

        self.path_timer -= 1
        start_bx = int((self.x - PLAYFIELD_X) // TILE_SIZE) // 2
        start_by = int((self.y - PLAYFIELD_Y) // TILE_SIZE) // 2
        need_new_path = False
        if self.path_timer <= 0 or not self.path or self.path_target != (target_bx, target_by):
            need_new_path = True
        elif self.stuck_timer > 20:
            need_new_path = True

        if need_new_path and target_bx is not None and base and self.state in ('chase_base', 'attack_base', 'chase_player'):
            path = a_star_big_tile(tilemap, start_bx, start_by, target_bx, target_by)
            if path and len(path) >= 2:
                self.path = path
                self.path_target = (target_bx, target_by)
                self.path_timer = random.randint(30, 60)
                next_bx, next_by = path[1]
                dir_from_path = direction_from_big_path(start_bx, start_by, next_bx, next_by)
                if dir_from_path and dir_from_path in possible:
                    if self.can_move_dir(dir_from_path, tilemap, players, ignore_brick=True):
                        self.direction = dir_from_path
                        return
            else:
                self.path = []
                self.path_timer = random.randint(20, 40)
        elif self.path and len(self.path) >= 2 and self.path_timer > 0:
            try:
                for i, (bx, by) in enumerate(self.path):
                    if bx == start_bx and by == start_by and i+1 < len(self.path):
                        next_bx, next_by = self.path[i+1]
                        dir_from_path = direction_from_big_path(start_bx, start_by, next_bx, next_by)
                        if dir_from_path and dir_from_path in possible and self.can_move_dir(dir_from_path, tilemap, players, ignore_brick=True):
                            self.direction = dir_from_path
                            return
            except:
                pass

        dx = target_x - self.x
        dy = target_y - self.y
        preferred_order = []
        if abs(dx) > abs(dy):
            preferred_order.append('RIGHT' if dx > 0 else 'LEFT')
            preferred_order.append('DOWN' if dy > 0 else 'UP')
        else:
            preferred_order.append('DOWN' if dy > 0 else 'UP')
            preferred_order.append('RIGHT' if dx > 0 else 'LEFT')

        for d in ['UP','DOWN','LEFT','RIGHT']:
            if d not in preferred_order:
                preferred_order.append(d)

        force_chance = 1.0 if self.state == 'attack_base' else 0.82
        second_chance = 0.0 if self.state == 'attack_base' else 0.15

        for d in preferred_order:
            if d not in possible:
                continue
            if self.can_move_dir(d, tilemap, players, ignore_brick=True):
                if d in preferred_order[:2] and random.random() < force_chance:
                    self.direction = d
                    return
                elif d not in preferred_order[:2] and random.random() < second_chance:
                    self.direction = d
                    return

        if self.state == 'attack_base':
            dx = target_x - self.x
            dy = target_y - self.y
            forbidden = []
            if dy > 0:
                forbidden.append('UP')
            else:
                forbidden.append('DOWN')
            if dx > 0:
                forbidden.append('LEFT')
            else:
                forbidden.append('RIGHT')
            valid = [d for d in possible if d not in forbidden and self.can_move_dir(d, tilemap, players, ignore_brick=True)]
            if valid:
                self.direction = random.choice(valid)
                return
            valid = [d for d in possible if self.can_move_dir(d, tilemap, players, ignore_brick=True)]
            if valid:
                self.direction = random.choice(valid)
                return
        else:
            valid = [d for d in possible if self.can_move_dir(d, tilemap, players, ignore_brick=True)]
            if valid:
                self.direction = random.choice(valid)
                return

        valid = [d for d in possible if self.can_move_dir(d, tilemap, players, ignore_brick=True)]
        if valid:
            self.direction = random.choice(valid)
        else:
            self.direction = opposite.get(self.direction, random.choice(['UP','DOWN','LEFT','RIGHT']))

    def shoot(self):
        if not self.can_shoot():
            return None
        sx, sy = self.get_bullet_spawn()
        b = Bullet(sx, sy, self.direction, 'enemy', power=self.bullet_power, color=(255, 100, 100))
        self.bullets.append(b)
        # Authentic cooldown varies by type (merged with sound)
        if self.enemy_type == 'fast':
            self.cooldown = random.randint(30, 70)
        elif self.enemy_type == 'power':
            self.cooldown = random.randint(25, 60)
        else:
            self.cooldown = random.randint(40, 95)
        try:
            from ..sound_manager import sound_manager
            sound_manager.play_shoot()
        except:
            pass
        return b

    def take_damage(self, power=1):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        self.health -= power
        if self.health <= 0:
            self.die()
            return True
        else:
            self.invulnerable_timer = 10
            return False

    def draw(self, screen):
        if not self.alive:
            return
        if self.powerup_carrier:
            if (self.flash_timer // 8) % 2 == 0:
                orig = self.color
                self.color = (255, 50, 50)
                super().draw(screen)
                self.color = orig
                return
        super().draw(screen)
        if self.enemy_type == 'armor' and self.health > 1:
            bar_w = 20
            bar_h = 3
            cx, cy = self.rect.centerx, self.rect.top - 6
            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
            health_colors = [(0,255,0), (255,255,0), (255,140,0), (180,180,180)]
            col = health_colors[self.health-1] if self.health <= len(health_colors) else (0,255,0)
            pygame.draw.rect(screen, col, (cx-bar_w//2, cy, int(bar_w*(self.health/4)), bar_h))
