import pygame
import random
import math
import heapq
from .tank import Tank
from .bullet import Bullet
from ..settings import *

# Debug logging
try:
    from ..logger_integration import safe_log_gameplay, safe_log_event
    HAS_DEBUG = True
except:
    HAS_DEBUG = False
    def safe_log_gameplay(*a, **kw): pass
    def safe_log_event(*a, **kw): pass

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
    def __init__(self, grid_x, grid_y, enemy_type='basic', is_mega=None):
        color = ENEMY_COLORS.get(enemy_type, ENEMY_COLORS['basic'])
        super().__init__(grid_x, grid_y, color, is_player=False, is_mega=is_mega)
        self.enemy_type = enemy_type
        self.direction = 'DOWN'
        self.is_player = False

        self.is_boss = False
        if enemy_type == 'basic':
            self.speed = TANK_SPEED['enemy']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 100
            self.shoot_chance = 0.018
            self.armor = ARMOR_INITIAL_ENEMY.get('basic', 50)
            self.max_armor = self.armor
        elif enemy_type == 'fast':
            self.speed = TANK_SPEED['fast']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 200
            self.shoot_chance = 0.025
            self.armor = ARMOR_INITIAL_ENEMY.get('fast', 40)
            self.max_armor = self.armor
        elif enemy_type == 'power':
            self.speed = TANK_SPEED['enemy'] * 1.1
            self.health = 1
            self.bullet_power = 1
            self.score_value = 300
            self.shoot_chance = 0.045
            self.armor = ARMOR_INITIAL_ENEMY.get('power', 80)
            self.max_armor = self.armor
        elif enemy_type == 'armor':
            self.speed = TANK_SPEED['enemy'] * 0.75
            self.health = 4
            self.bullet_power = 1
            self.score_value = 400
            self.shoot_chance = 0.020
            self.armor = ARMOR_INITIAL_ENEMY.get('armor', 150)
            self.max_armor = self.armor
        elif enemy_type in ('boss', 'monster_boss', 'monster'):
            # Monster boss - slowed to normal enemy speed per user request (was 1.5x player = 3.3, now 1.2 same as basic)
            # Further slowed shooting and venom per user request "slow down the venom and shooting speed of boss"
            self.speed = TANK_SPEED['enemy']  # same as normal enemy (1.8 currently, 1.2 originally) - slowed down
            self.health = 18  # tougher boss still
            self.bullet_power = 2
            self.score_value = 3500
            self.shoot_chance = 0.045  # slowed: was 0.12, now 0.045 similar to power enemy (user requested slower)
            self.is_boss = True
            self.venom_cooldown = 0
            self.venom_shoot_chance = 0.025  # slowed venom: was 0.06, now 0.025 (user request slower)
            self.armor = ARMOR_INITIAL_ENEMY.get('monster_boss', 400)
            self.max_armor = self.armor
            # Make boss bigger
            self.rect = pygame.Rect(0,0, int((TANK_SIZE-4)*1.8), int((TANK_SIZE-4)*1.8))
            self.rect.center = (self.x, self.y)
        else:
            self.speed = TANK_SPEED['enemy']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 100
            self.shoot_chance = 0.018
            self.armor = ARMOR_INITIAL_ENEMY.get('basic', 50)
            self.max_armor = self.armor

        # Boss has less spawn protection but more flashy
        if enemy_type in ('boss', 'monster_boss', 'monster'):
            self.spawn_protection = 30
            self.invulnerable_timer = 30
        else:
            self.spawn_protection = 60
            self.invulnerable_timer = 60
        self.powerup_carrier = random.random() < 0.25
        # Item abilities that can be randomly assigned when boss is released
        self.homing_active = False
        self.spread_active = False
        self.rapid_active = False

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

        edge_tolerance = 12
        # Axis-specific edge check to allow sliding along edge (fix player stuck at edge)
        if dx != 0:
            if new_rect.left < PLAYFIELD_X - edge_tolerance or new_rect.right > PLAYFIELD_X + PLAYFIELD_W + edge_tolerance:
                return False
        else:
            if new_rect.left < PLAYFIELD_X - edge_tolerance*2 or new_rect.right > PLAYFIELD_X + PLAYFIELD_W + edge_tolerance*2:
                return False
        if dy != 0:
            if new_rect.top < PLAYFIELD_Y - edge_tolerance or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + edge_tolerance:
                return False
        else:
            if new_rect.top < PLAYFIELD_Y - edge_tolerance*2 or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + edge_tolerance*2:
                return False

        # Fixed: tank 32 vs tile 24 - use 24x24 collision for tiles so single destroyed brick is passable
        # Same fix as player tank: inflate -8 for normal tanks
        if getattr(self, 'is_boss', False) or getattr(self, 'is_giant', False):
            check_rect = new_rect.copy()  # boss/giant full for crushing
        else:
            check_rect = new_rect.inflate(-8, -8)  # 32->24
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
            if new_rect.colliderect(other.rect):
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
        # Enhanced for 2 bugs: edge stuck and spawn stuck
        overlapping_tanks = []
        for other in (other_tanks + players):
            if other is self or not other.alive:
                continue
            d = math.hypot(self.x - other.x, self.y - other.y)
            if d < TANK_SIZE * 0.95:  # overlapping / too close
                overlapping_tanks.append((other, d))

        if overlapping_tanks:
            # Find nearest overlapping
            nearest, nearest_dist = min(overlapping_tanks, key=lambda x: x[1])
            dx = self.x - nearest.x
            dy = self.y - nearest.y
            # Handle exact overlap (dx=0, dy=0) - pick random direction
            if abs(dx) < 1 and abs(dy) < 1:
                # Exact overlap, pick random away direction
                dir_away = random.choice(['UP', 'DOWN', 'LEFT', 'RIGHT'])
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
            else:
                # Choose direction away from nearest
                if abs(dx) > abs(dy):
                    dir_away = 'RIGHT' if dx > 0 else 'LEFT'
                else:
                    dir_away = 'DOWN' if dy > 0 else 'UP'
            self.direction = dir_away
            self.target_dir_timer = 20
            # During spawn protection, allow moving through other tanks (ignore collision) to unstick from spawn point
            # This fixes bug where enemy just spawned stays there not moving because blocked by other tank
            ignore_tanks = self.spawn_protection > 0 or nearest_dist < TANK_SIZE * 0.5
            move_other_tanks = [] if ignore_tanks else []
            moved_sep = super().try_move(dir_away, tilemap, move_other_tanks)
            if not moved_sep:
                # If still blocked by tile, try perpendicular away directions
                perp = {'UP': ['LEFT','RIGHT'], 'DOWN': ['LEFT','RIGHT'], 'LEFT': ['UP','DOWN'], 'RIGHT': ['UP','DOWN']}
                for pd in perp.get(dir_away, []):
                    if super().try_move(pd, tilemap, move_other_tanks):
                        self.direction = pd
                        moved_sep = True
                        break
            # If still overlapping heavily, give stronger push to unstick
            current_dist = math.hypot(self.x - nearest.x, self.y - nearest.y)
            if current_dist < TANK_SIZE * 0.8:
                # Push more aggressively for stuck case (5px instead of 2.5)
                # For exact overlap, push random 8px
                if current_dist < 1:
                    push_dx = random.uniform(-8, 8)
                    push_dy = random.uniform(-8, 8)
                else:
                    push_dx = (dx / (max(current_dist, 1))) * 5.0
                    push_dy = (dy / (max(current_dist, 1))) * 5.0
                self.x += push_dx
                self.y += push_dy
                self.rect.center = (self.x, self.y)
                # Log stuck event for debug DB
                try:
                    from ..logger_integration import safe_log_gameplay
                    safe_log_gameplay("ENEMY_STUCK_PUSH", data={"enemy_type": self.enemy_type, "dist": current_dist, "push": (push_dx, push_dy), "dir": dir_away, "x": self.x, "y": self.y})
                except:
                    pass

        # Enhanced stuck detection with logging for debug DB
        if self.stuck_timer > 40:
            try:
                from ..logger_integration import safe_log_gameplay
                safe_log_gameplay("ENEMY_STUCK", data={"enemy_type": self.enemy_type, "stuck_timer": self.stuck_timer, "x": self.x, "y": self.y, "dir": self.direction, "is_boss": getattr(self, 'is_boss', False)})
            except:
                pass
            # If stuck for long (>60 frames ~1 sec), try emergency unstuck: destroy brick in front or teleport
            if self.stuck_timer > 60:
                # Try to shoot brick in front
                if self.can_shoot():
                    # Force shoot to clear path
                    try:
                        nb = self.shoot()
                        if nb:
                            if isinstance(nb, list):
                                bullets_list.extend(nb)
                            else:
                                bullets_list.append(nb)
                    except:
                        pass
                # If still stuck >90 frames, teleport to nearby free spawn point
                if self.stuck_timer > 90:
                    # Try to find nearby free position (search in 3-tile radius)
                    for _ in range(10):
                        try:
                            tx = self.x + random.randint(-48, 48)
                            ty = self.y + random.randint(-48, 48)
                            test_rect = self.rect.copy()
                            test_rect.center = (tx, ty)
                            # Check bounds
                            if test_rect.left < PLAYFIELD_X - 12 or test_rect.right > PLAYFIELD_X + PLAYFIELD_W + 12:
                                continue
                            if test_rect.top < PLAYFIELD_Y - 12 or test_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + 12:
                                continue
                            # Check tile collision with smaller rect
                            check_r = test_rect.inflate(-8, -8)
                            blocked = False
                            for _, _, _, trect in tilemap.get_tiles_in_rect(check_r):
                                if check_r.colliderect(trect):
                                    blocked = True
                                    break
                            if not blocked:
                                self.x = tx
                                self.y = ty
                                self.rect.center = (tx, ty)
                                self.stuck_timer = 0
                                self.target_dir_timer = 5
                                try:
                                    from ..logger_integration import safe_log_gameplay
                                    safe_log_gameplay("ENEMY_TELEPORT_UNSTUCK", data={"enemy_type": self.enemy_type, "new_x": tx, "new_y": ty})
                                except:
                                    pass
                                break
                        except:
                            pass

        if self.target_dir_timer <= 0 or self.stuck_timer > 25:
            # For boss, pass other_tanks so it can target enemies too
            if getattr(self, 'is_boss', False):
                self.choose_new_direction(players, tilemap, base, other_tanks)
            else:
                self.choose_new_direction(players, tilemap, base)
            self.target_dir_timer = random.randint(25, 90)
            if self.stuck_timer > 25:
                self.target_dir_timer = random.randint(10, 30)
            self.stuck_timer = 0

        # Boss can run over enemy tanks like giant (crush them)
        if getattr(self, 'is_boss', False):
            # Boss tries to move ignoring enemy tanks for crushing, but still blocked by players? No, boss should crush enemies but be blocked by players? Actually boss should be threat to both, but crushing enemies is okay
            # Check if we can move into enemy and crush
            # First try normal move, if blocked by enemy, try to crush
            # We handle crushing in try_move override below
            moved = self.try_move(self.direction, tilemap, other_tanks + players)
            # If blocked by enemy tank, try to crush it
            if not moved:
                # Check if blocked by enemy tank (not player)
                for ot in other_tanks:
                    if ot is self or not ot.alive:
                        continue
                    if getattr(ot, 'is_player', False):
                        continue
                    if getattr(ot, 'is_boss', False):
                        continue
                    # Check if this enemy is blocking us
                    test_x = self.x
                    dx, dy = DIRS.get(self.direction, (0,0))
                    test_x = self.x + dx * self.speed
                    test_y = self.y + dy * self.speed
                    test_rect = self.rect.copy()
                    test_rect.center = (test_x, test_y)
                    if test_rect.colliderect(ot.rect):
                        # Crush enemy tank
                        try:
                            ot.die()
                            from ..logger_integration import safe_log_gameplay
                            safe_log_gameplay("BOSS_CRUSH_ENEMY", data={"boss_x": self.x, "boss_y": self.y, "enemy_type": getattr(ot, 'enemy_type', 'unknown')})
                            # Give score to nearest player
                            # (handled in game.py via killer detection, but we log)
                            # Try to move again after crushing
                            moved = self.try_move(self.direction, tilemap, [])
                            if moved:
                                break
                        except:
                            ot.alive = False
        else:
            moved = self.try_move(self.direction, tilemap, other_tanks + players)
        if not moved:
            block_type = self.get_blocking_tile_type(self.direction, tilemap)
            if block_type == TILE_BRICK:
                if random.random() < 0.7 and self.can_shoot():
                    new_b = self.shoot()
                    if new_b:
                        if isinstance(new_b, list):
                            bullets_list.extend(new_b)
                        else:
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
                            if isinstance(nb, list):
                                bullets_list.extend(nb)
                            else:
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
            # For boss, check both players and enemy tanks (free-for-all)
            if getattr(self, 'is_boss', False):
                # Check players first (higher priority)
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
                # If no player aligned, check enemy tanks (boss attacks enemies too)
                if aligned_target is None:
                    for et in other_tanks:
                        if et is self or not et.alive:
                            continue
                        if getattr(et, 'is_player', False) or getattr(et, 'is_boss', False):
                            continue
                        los, _ = self.has_line_of_sight(et.rect.centerx, et.rect.centery, tilemap)
                        if los:
                            if abs(et.x - self.x) < 16 and ((self.direction == 'DOWN' and et.y > self.y) or (self.direction == 'UP' and et.y < self.y)):
                                aligned_target = (et.rect.centerx, et.rect.centery)
                                break
                            if abs(et.y - self.y) < 16 and ((self.direction == 'RIGHT' and et.x > self.x) or (self.direction == 'LEFT' and et.x < self.x)):
                                aligned_target = (et.rect.centerx, et.rect.centery)
                                break
            else:
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
        if base and self.state == 'attack_base' and not getattr(self, 'is_boss', False):
            shoot_chance *= 1.8
        # Boss gets bonus shoot chance when chasing players (Chad/Lida preference) but slightly less for enemies
        if getattr(self, 'is_boss', False):
            if self.state == 'chase_player':
                shoot_chance *= 1.6  # prefer shooting Chad/Lida
            elif self.state == 'chase_enemy':
                shoot_chance *= 1.2  # lower chance for enemies

        if random.random() < shoot_chance and self.base_attack_cooldown == 0:
            # boss has chance to shoot venom instead - now can target enemies too
            if getattr(self, 'is_boss', False) and random.random() < 0.5:
                vb = self.shoot_venom(players, other_tanks)
                if vb:
                    if isinstance(vb, list):
                        bullets_list.extend(vb)
                    else:
                        bullets_list.append(vb)
                    new_bullet = vb
                else:
                    new_bullet = self.shoot()
                    if new_bullet:
                        if isinstance(new_bullet, list):
                            bullets_list.extend(new_bullet)
                        else:
                            bullets_list.append(new_bullet)
            else:
                new_bullet = self.shoot()
                if new_bullet:
                    if isinstance(new_bullet, list):
                        bullets_list.extend(new_bullet)
                    else:
                        bullets_list.append(new_bullet)
            if is_base:
                self.base_attack_cooldown = 30
        else:
            # boss independent venom timer even when not aligned - also attacks enemies
            if getattr(self, 'is_boss', False):
                if random.random() < getattr(self, 'venom_shoot_chance', 0.04):
                    vb = self.shoot_venom(players, other_tanks)
                    if vb:
                        if isinstance(vb, list):
                            bullets_list.extend(vb)
                        else:
                            bullets_list.append(vb)
                        new_bullet = vb

        super().update(tilemap, other_tanks + players)
        self.bullets = [b for b in self.bullets if b.alive]
        if getattr(self, 'venom_cooldown', 0) > 0:
            self.venom_cooldown -= 1
        return new_bullet

    def choose_new_direction(self, players, tilemap, base=None, other_tanks=None):
        # Boss monster special: can target both players and enemy tanks, preferring players (75% vs 25%)
        # This makes monster a free-for-all threat when released
        is_boss = getattr(self, 'is_boss', False)
        possible = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        opposite = {'UP':'DOWN','DOWN':'UP','LEFT':'RIGHT','RIGHT':'LEFT'}

        if self.direction in opposite and self.stuck_timer < 15:
            rev = opposite[self.direction]
            if rev in possible and random.random() < 0.85:
                possible.remove(rev)

        target_x, target_y = None, None
        target_bx, target_by = None, None
        alive_players = [p for p in players if p.alive] if players else []
        # For boss, also consider enemy tanks as potential targets
        alive_enemies = []
        if is_boss and other_tanks:
            for ot in other_tanks:
                if ot is self:
                    continue
                if not getattr(ot, 'alive', False):
                    continue
                # Don't target other bosses (only one boss typically)
                if getattr(ot, 'is_boss', False):
                    continue
                # Only target enemy tanks (not players, already in alive_players)
                if getattr(ot, 'is_player', False):
                    continue
                alive_enemies.append(ot)

        use_base = True
        if base and base.alive and not is_boss:
            # Boss does NOT chase base after release (base already destroyed)
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
        elif is_boss and (alive_players or alive_enemies):
            # Boss chooses target: 75% players (Chad/Lida), 25% enemies
            # Prefer closer targets but with bias to players
            candidates = []
            for p in alive_players:
                dist = math.hypot(p.x - self.x, p.y - self.y)
                # Weight players higher: effective distance * 0.6 (so they appear closer)
                candidates.append(('player', p, dist * 0.6))
            for e in alive_enemies:
                dist = math.hypot(e.x - self.x, e.y - self.y)
                candidates.append(('enemy', e, dist))
            
            if candidates:
                # Sort by weighted distance
                candidates.sort(key=lambda x: x[2])
                # 75% choose player if available, else closest
                if alive_players and random.random() < 0.75:
                    # Pick closest player
                    player_candidates = [c for c in candidates if c[0]=='player']
                    if player_candidates:
                        chosen_type, chosen_tank, _ = player_candidates[0]
                    else:
                        chosen_type, chosen_tank, _ = candidates[0]
                else:
                    # Pick from all, but still weighted
                    if random.random() < 0.5 and alive_enemies:
                        # Sometimes pick enemy for variety
                        enemy_candidates = [c for c in candidates if c[0]=='enemy']
                        if enemy_candidates:
                            chosen_type, chosen_tank, _ = enemy_candidates[0]
                        else:
                            chosen_type, chosen_tank, _ = candidates[0]
                    else:
                        chosen_type, chosen_tank, _ = candidates[0]
                
                target_x, target_y = chosen_tank.rect.centerx, chosen_tank.rect.centery
                target_bx = int((target_x - PLAYFIELD_X) // TILE_SIZE) // 2
                target_by = int((target_y - PLAYFIELD_Y) // TILE_SIZE) // 2
                if chosen_type == 'player':
                    self.target_player_id = chosen_tank.player_id
                    self.state = 'chase_player'
                    # Log boss targeting player (Chad/Lida)
                    try:
                        from ..logger_integration import safe_log_gameplay
                        safe_log_gameplay("BOSS_TARGET_PLAYER", data={"target": getattr(chosen_tank, 'player_id', 0), "dist": math.hypot(chosen_tank.x - self.x, chosen_tank.y - self.y)})
                    except:
                        pass
                else:
                    self.state = 'chase_enemy'
                    try:
                        from ..logger_integration import safe_log_gameplay
                        safe_log_gameplay("BOSS_TARGET_ENEMY", data={"enemy_type": getattr(chosen_tank, 'enemy_type', 'unknown'), "dist": math.hypot(chosen_tank.x - self.x, chosen_tank.y - self.y)})
                    except:
                        pass
            else:
                self.state = 'wander'
                self.direction = random.choice(possible)
                return
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

    def shoot(self, venom=False):
        if not self.can_shoot() and not venom:
            return None

        # Handle spread - fire 8 directions at once (if item assigned)
        if getattr(self, 'spread_active', False):
            bullets = []
            try:
                from ..settings import EIGHT_DIRS
            except:
                EIGHT_DIRS = ['UP','UP_RIGHT','RIGHT','DOWN_RIGHT','DOWN','DOWN_LEFT','LEFT','UP_LEFT']
            for d in EIGHT_DIRS:
                sx, sy = self.get_bullet_spawn_for(d) if hasattr(self, 'get_bullet_spawn_for') else self.get_bullet_spawn()
                if hasattr(self, 'get_bullet_spawn_for'):
                    sx, sy = self.get_bullet_spawn_for(d)
                is_homing = getattr(self, 'homing_active', False)
                is_rapid = getattr(self, 'rapid_active', False)
                b_type = 'homing' if is_homing else 'rapid' if is_rapid else 'spread'
                b = Bullet(sx, sy, d, 'enemy', power=self.bullet_power, color=(255, 100, 100), homing=is_homing, bullet_type=b_type)
                if getattr(self, 'rapid_active', False):
                    b.speed *= 1.2
                self.bullets.append(b)
                bullets.append(b)
            # Cooldown for spread - longer, but rapid reduces - slowed for boss
            base_cd = 40
            if getattr(self, 'rapid_active', False):
                base_cd = max(10, base_cd // 2)
            if self.enemy_type == 'fast':
                self.cooldown = random.randint(30, 60)
            elif getattr(self, 'is_boss', False):
                self.cooldown = random.randint(65, 110)  # slowed: was 35-70, now 65-110
            else:
                self.cooldown = random.randint(base_cd, base_cd+30)
            try:
                from ..sound_manager import sound_manager
                sound_manager.play_shoot()
            except:
                pass
            return bullets  # return list for spread

        sx, sy = self.get_bullet_spawn()
        # Determine owner: boss uses 'boss' for all bullets (so it can hit both players and enemies)
        owner_type = 'boss' if getattr(self, 'is_boss', False) else 'enemy'
        if venom or (getattr(self, 'is_boss', False) and random.random() < 0.45):
            # venom shot from boss - slowed down per user request
            b = Bullet(sx, sy, self.direction, owner_type, power=1, venom=True, bullet_type='venom')
            b.owner = 'boss'  # ensure boss owner
            b._shooter_ref = self  # prevent self-hit
            self.bullets.append(b)
            if getattr(self, 'is_boss', False):
                self.cooldown = random.randint(70, 130)  # slowed: was 35-80, now 70-130
                self.venom_cooldown = 60  # slowed: was 25, now 60
            try:
                from ..sound_manager import sound_manager
                sound_manager.play_shoot()
            except:
                pass
            return b

        is_homing = getattr(self, 'homing_active', False)
        is_rapid = getattr(self, 'rapid_active', False)
        b_type = 'homing' if is_homing else 'rapid' if is_rapid else 'normal'
        if self.bullet_power >= 2:
            b_type = 'power'
        b = Bullet(sx, sy, self.direction, owner_type, power=self.bullet_power, color=(255, 100, 100), homing=is_homing, bullet_type=b_type)
        b._shooter_ref = self
        b.owner = owner_type
        if getattr(self, 'rapid_active', False):
            b.speed *= 1.2
        self.bullets.append(b)

        # Cooldown handling - rapid reduces cooldown for 3x attack feel
        # Slowed down boss per user request
        if getattr(self, 'rapid_active', False):
            # Rapid: faster shooting, but boss slower than before
            if self.enemy_type == 'fast':
                self.cooldown = random.randint(12, 28)
            elif getattr(self, 'is_boss', False):
                self.cooldown = random.randint(30, 60)  # slowed: was 15-35, now 30-60
            else:
                self.cooldown = random.randint(15, 40)
        else:
            if self.enemy_type == 'fast':
                self.cooldown = random.randint(30, 70)
            elif self.enemy_type == 'power':
                self.cooldown = random.randint(25, 60)
            elif getattr(self, 'is_boss', False):
                self.cooldown = random.randint(65, 115)  # slowed: was 30-60, now 65-115
            else:
                self.cooldown = random.randint(40, 95)

        try:
            from ..sound_manager import sound_manager
            # Use appropriate sound type
            if is_homing:
                sound_manager.play_shoot('homing')
            elif getattr(self, 'rapid_active', False):
                sound_manager.play_shoot('rapid')
            else:
                sound_manager.play_shoot()
        except:
            pass
        return b

    def shoot_venom(self, players, other_tanks=None):
        if not getattr(self, 'is_boss', False):
            return None
        if getattr(self, 'venom_cooldown', 0) > 0:
            self.venom_cooldown -= 1
            return None
        # Boss venom now can target both players (Chad/Lida) and enemy tanks, preferring players 75% vs 25%
        # This makes monster a free-for-all threat
        alive_players = [p for p in players if p.alive] if players else []
        alive_enemies = []
        if other_tanks:
            for ot in other_tanks:
                if ot is self or not ot.alive:
                    continue
                if getattr(ot, 'is_player', False) or getattr(ot, 'is_boss', False):
                    continue
                alive_enemies.append(ot)

        if not alive_players and not alive_enemies:
            return None

        # Choose target: 75% player, 25% enemy if both available
        target = None
        if alive_players and alive_enemies:
            if random.random() < 0.75:
                target = min(alive_players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
            else:
                target = min(alive_enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
        elif alive_players:
            target = min(alive_players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
        else:
            target = min(alive_enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))

        if not target:
            return None

        # aim at chosen target
        dx = target.x - self.x
        dy = target.y - self.y
        # choose direction closest to target
        best_dir = None
        best_dot = -2
        for dname, (ddx, ddy) in DIRS.items():
            if ddx == 0 and ddy == 0:
                continue
            ndx, ndy = ddx, ddy
            if ndx != 0 and ndy != 0:
                nlen = math.hypot(ndx, ndy)
                ndx /= nlen
                ndy /= nlen
            norm = math.hypot(dx, dy) or 1
            dot = (dx/norm)*ndx + (dy/norm)*ndy
            if dot > best_dot:
                best_dot = dot
                best_dir = dname
        if best_dir:
            self.direction = best_dir
        return self.shoot(venom=True)

    def take_damage(self, power=1, bullet_type='normal'):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        
        # Use parent armor logic first
        # If armor protects, don't reduce health
        if hasattr(self, 'armor') and self.armor > 0:
            # Call parent to handle armor damage - if returns False, armor protected
            parent_result = super().take_damage(power, bullet_type)
            if not parent_result:
                # Armor absorbed it, flash
                return False
            # Armor broken, continue to health damage in this same hit? No, armor breaks absorb this hit
            # Actually super returns False when armor protects, True would mean no armor - but we handled in super
            # So if we reach here, armor was 0 or just broke, check health
            if self.armor > 0:
                return False
        
        # Armor depleted, damage health
        self.health -= power
        if self.health <= 0:
            self.die()
            return True
        else:
            self.invulnerable_timer = 10
            return False

    def draw(self, screen, tilemap=None):
        if not self.alive:
            return
        # Forest hiding for normal enemies - completely hidden in forest
        if tilemap and not getattr(self, 'is_boss', False):
            try:
                if hasattr(tilemap, 'is_in_forest') and tilemap.is_in_forest(self.x, self.y):
                    return
                else:
                    # fallback check via tiles
                    gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
                    gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
                    if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                        if tilemap.tiles[gy][gx] == TILE_GRASS:
                            return
            except Exception:
                pass
        # Boss monster tank - special drawing
        if getattr(self, 'is_boss', False):
            cx, cy = self.rect.center
            size = self.rect.width
            # Shadow
            pygame.draw.ellipse(screen, (0,0,0, 100), (cx - size//2 +4, cy - size//2 +12, size-8, size//3))
            # Boss body - monster tank hybrid
            # Main body - green monster with tank tracks
            body_color = (80, 200, 80)
            # Body base
            body_rect = pygame.Rect(0,0,size-6, size-6)
            body_rect.center = (cx, cy)
            pygame.draw.rect(screen, body_color, body_rect, border_radius=8)
            pygame.draw.rect(screen, (40,100,30), body_rect, 3, border_radius=8)
            # Tracks - dark
            pygame.draw.rect(screen, (30,30,30), (cx - size//2 +2, cy - size//2 +4, 8, size-8), border_radius=3)
            pygame.draw.rect(screen, (30,30,30), (cx + size//2 -10, cy - size//2 +4, 8, size-8), border_radius=3)
            # Turret / cannon direction
            # Use direction to draw cannon
            import math
            from ..settings import DIR_ANGLE, DIRS
            ang = DIR_ANGLE.get(self.direction, 0)
            vx = math.sin(math.radians(ang))
            vy = -math.cos(math.radians(ang))
            x2 = cx + vx * (size//2 + 8)
            y2 = cy + vy * (size//2 + 8)
            pygame.draw.line(screen, (20,20,20), (cx, cy), (x2, y2), 6)
            # Monster face on top of tank
            # Eyes
            t = getattr(self, 'flash_timer', 0)
            bob = (t//10)%4 -2
            eye_y = cy - 6 + bob
            # White eyes big
            pygame.draw.circle(screen, (255,255,255), (cx-8, eye_y), 7)
            pygame.draw.circle(screen, (255,255,255), (cx+8, eye_y), 7)
            # Red pupils angry
            pygame.draw.circle(screen, (255,0,0), (cx-8, eye_y), 3)
            pygame.draw.circle(screen, (255,0,0), (cx+8, eye_y), 3)
            # Horns
            pygame.draw.polygon(screen, (200,30,30), [(cx-14, cy-12), (cx-12, cy-22), (cx-6, cy-12)])
            pygame.draw.polygon(screen, (200,30,30), [(cx+6, cy-12), (cx+12, cy-22), (cx+14, cy-12)])
            # Mouth
            pygame.draw.arc(screen, (0,0,0), (cx-10, eye_y+4, 20, 12), 0, 3.14, 3)
            # Teeth
            pygame.draw.rect(screen, (255,255,200), (cx-6, eye_y+8, 3, 5))
            pygame.draw.rect(screen, (255,255,200), (cx+3, eye_y+8, 3, 5))
            # Venom drip from mouth when about to shoot
            if random.random() < 0.3:
                pygame.draw.circle(screen, (80, 200, 40), (cx, eye_y+14), 2)
                pygame.draw.circle(screen, (60, 180, 60), (cx+1, eye_y+16), 1)
            # Speed lines for 1.5x
            if getattr(self, 'move_timer', 0) % 6 < 3:
                pygame.draw.line(screen, (255,255,100), (cx-size//2-2, cy-4), (cx-size//2-6, cy-4), 2)
                pygame.draw.line(screen, (255,255,100), (cx-size//2-2, cy+6), (cx-size//2-7, cy+6), 2)
            # Boss label and health bar - big
            bar_w = 48
            bar_h = 7
            bar_x = cx - bar_w//2
            bar_y = cy - size//2 - 14
            pygame.draw.rect(screen, (0,0,0), (bar_x-1, bar_y-1, bar_w+2, bar_h+2))
            pygame.draw.rect(screen, (60,60,60), (bar_x, bar_y, bar_w, bar_h))
            max_h = 18.0
            frac = max(0, self.health / max_h)
            col = (int(255*(1-frac)), int(255*frac), 0)
            pygame.draw.rect(screen, col, (bar_x, bar_y, int(bar_w*frac), bar_h))
            # BOSS text
            font = pygame.font.Font(None, 18)
            txt = font.render("BOSS", True, (255,50,50))
            screen.blit(txt, (cx-14, bar_y-14))
            # Flash when powerup carrier or invulnerable
            if self.powerup_carrier and (self.flash_timer // 8) % 2 == 0:
                pygame.draw.rect(screen, (255,50,50), body_rect, 3, border_radius=8)
            return

        if self.powerup_carrier:
            if (self.flash_timer // 8) % 2 == 0:
                orig = self.color
                self.color = (255, 50, 50)
                super().draw(screen)
                self.color = orig
                return
        super().draw(screen)
        # Health bar for armor and boss
        if self.health > 1:
            bar_w = 20 if not getattr(self, 'is_boss', False) else 40
            bar_h = 3 if not getattr(self, 'is_boss', False) else 6
            cx, cy = self.rect.centerx, self.rect.top - 6
            if getattr(self, 'is_boss', False):
                cy = self.rect.top - 12
            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
            health_colors = [(0,255,0), (255,255,0), (255,140,0), (180,180,180)]
            if self.health <= len(health_colors):
                col = health_colors[self.health-1]
            else:
                # boss gradient green->red
                frac = self.health / 12.0
                col = (int(255*(1-frac)), int(255*frac), 0)
            # For armor, health is out of 4; for boss out of 12
            max_h = 4 if self.enemy_type == 'armor' else 12
            pygame.draw.rect(screen, col, (cx-bar_w//2, cy, int(bar_w*(self.health/max_h)), bar_h))
