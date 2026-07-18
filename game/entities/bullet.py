import pygame
import math
import heapq
from collections import deque
from ..settings import *

# ------------------------------------------------------------
# Helpers for smart homing
# ------------------------------------------------------------
def _tile_at(tilemap, gx, gy):
    if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
        return tilemap.tiles[gy][gx]
    return None

def _is_blocking_for_homing(tilemap, gx, gy):
    """Brick and steel block homing missiles; water, grass, ice don't.
       Water does block tanks but bullet can fly over.
       For smart avoidance we treat BOTH brick and steel as walls to avoid.
    """
    t = _tile_at(tilemap, gx, gy)
    if t is None:
        return True  # out of bounds = blocking
    if t == TILE_BRICK or t == TILE_STEEL:
        return True
    # water blocks tank but missile can fly over? Requirement says avoid brick and walls.
    # Don't treat water as wall for missile pathing, but we will avoid it if possible for realism?
    # For now only brick/steel are hard walls.
    return False

def _pixel_to_grid(px, py):
    gx = int((px - PLAYFIELD_X) // TILE_SIZE)
    gy = int((py - PLAYFIELD_Y) // TILE_SIZE)
    return gx, gy

def _grid_to_pixel_center(gx, gy):
    return PLAYFIELD_X + gx * TILE_SIZE + TILE_SIZE * 0.5, PLAYFIELD_Y + gy * TILE_SIZE + TILE_SIZE * 0.5

def _line_of_sight_clear(tilemap, x0, y0, x1, y1):
    """Bresenham line check for brick/steel between two pixel points."""
    gx0, gy0 = _pixel_to_grid(x0, y0)
    gx1, gy1 = _pixel_to_grid(x1, y1)
    dx = abs(gx1 - gx0)
    dy = -abs(gy1 - gy0)
    sx = 1 if gx0 < gx1 else -1
    sy = 1 if gy0 < gy1 else -1
    err = dx + dy
    x, y = gx0, gy0
    steps = 0
    while True:
        if steps > 0:  # skip starting tile
            if _is_blocking_for_homing(tilemap, x, y):
                return False
        if x == gx1 and y == gy1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
        steps += 1
        if steps > 64:  # safety
            break
    return True

def _a_star_tile(tilemap, sx, sy, tx, ty):
    """A* on small 26x26 grid avoiding brick/steel. Returns list of (gx,gy) or None."""
    # bounds check
    if not (0 <= sx < GRID_W and 0 <= sy < GRID_H and 0 <= tx < GRID_W and 0 <= ty < GRID_H):
        return None
    if sx == tx and sy == ty:
        return [(sx, sy)]
    # if target itself is blocking, try neighbours
    if _is_blocking_for_homing(tilemap, tx, ty):
        # find nearest free attorno
        for r in range(1, 4):
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    nx, ny = tx+dx, ty+dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H and not _is_blocking_for_homing(tilemap, nx, ny):
                        tx, ty = nx, ny
                        break
                else:
                    continue
                break
            else:
                continue
            break
        if _is_blocking_for_homing(tilemap, tx, ty):
            return None

    open_heap = []
    heapq.heappush(open_heap, (0, 0, sx, sy, None))
    came_from = {}
    g_score = {(sx, sy): 0}
    closed = set()

    # Prefer cardinal + diagonal with cost
    neighbours = [ (1,0,1), (-1,0,1), (0,1,1), (0,-1,1),
                   (1,1,1.414), (-1,1,1.414), (1,-1,1.414), (-1,-1,1.414) ]

    nodes = 0
    max_nodes = 500  # 26x26 = 676

    while open_heap and nodes < max_nodes:
        f, g, x, y, parent = heapq.heappop(open_heap)
        if (x, y) in closed:
            continue
        came_from[(x, y)] = parent
        closed.add((x, y))
        nodes += 1
        if x == tx and y == ty:
            # reconstruct
            path = []
            cur = (x, y)
            while cur is not None:
                path.append(cur)
                cur = came_from.get(cur)
            path.reverse()
            return path
        for dx, dy, cost in neighbours:
            nx, ny = x+dx, y+dy
            if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                continue
            if (nx, ny) in closed:
                continue
            if _is_blocking_for_homing(tilemap, nx, ny):
                continue
            # diagonal corner check: don't cut through corners of walls
            if dx != 0 and dy != 0:
                if _is_blocking_for_homing(tilemap, x+dx, y) and _is_blocking_for_homing(tilemap, x, y+dy):
                    continue
            ng = g + cost
            if (nx, ny) not in g_score or ng < g_score[(nx, ny)]:
                g_score[(nx, ny)] = ng
                h = math.hypot(nx - tx, ny - ty)
                nf = ng + h
                heapq.heappush(open_heap, (nf, ng, nx, ny, (x, y)))
    return None


class Bullet:
    def __init__(self, x, y, direction, owner, power=1, color=None, homing=False, venom=False):
        self.x = x
        self.y = y
        self.dir = direction
        self.owner = owner  # 'player1', 'player2', 'enemy', 'boss'
        self.power = power
        self.color = color or COLOR_WHITE
        self.speed = BULLET_SPEED
        if power >= 2:
            self.speed = BULLET_SPEED * 1.3
        self.venom = venom
        if venom:
            self.speed = VENOM_SPEED
            self.color = (80, 220, 80)

        self.alive = True
        sz = BULLET_SIZE if not venom else BULLET_SIZE+2
        self.rect = pygame.Rect(x - sz//2, y - sz//2, sz, sz)

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

        if homing:
            self.speed = getattr(__import__('game.settings', fromlist=['HOMING_SPEED']), 'HOMING_SPEED', TANK_SPEED['player']*1.15)
            self.turn_speed = getattr(__import__('game.settings', fromlist=['HOMING_TURN_SPEED']), 'HOMING_TURN_SPEED', 0.055)
            if color is None or color == COLOR_WHITE:
                self.color = (255, 140, 0)  # orange missile
            self.trail_max = 12
            # smart missile state
            self.travelled = 0.0
            self.max_distance = getattr(__import__('game.settings', fromlist=['HOMING_MAX_DISTANCE']), 'HOMING_MAX_DISTANCE', 468)
            self.path = []  # list of (gx,gy) A* path
            self.path_world = []  # list of (px,py) centres smoothed
            self.path_index = 0
            self.replan_timer = 0
            self.replan_interval = getattr(__import__('game.settings', fromlist=['HOMING_ASTAR_REPLAN_INTERVAL']), 'HOMING_ASTAR_REPLAN_INTERVAL', 45)
            self.waypoint = None  # current waypoint pixel
            self.avoid_vector = (0.0, 0.0)
            self.stuck_timer = 0
            self.last_pos = (x, y)
            self.lost_target_timer = 0
            # Particle-ish flame offset
            self.flame_phase = 0
        else:
            self.turn_speed = 0
            self.trail_max = 6

    def _find_nearest_target(self, tanks):
        """Find nearest enemy for homing missile within detection range"""
        if not self.homing:
            return None
        candidates = []
        if self.owner.startswith('player'):
            for t in tanks:
                if t.alive and not getattr(t, 'is_player', False):
                    # ignore if far
                    dist = math.hypot(t.x - self.x, t.y - self.y)
                    if dist <= HOMING_DETECTION_RANGE:
                        candidates.append((dist, t))
                    elif not candidates:
                        # if none within range, still consider far one if it's the only one
                        candidates.append((dist, t))
        else:
            for t in tanks:
                if t.alive and getattr(t, 'is_player', False):
                    dist = math.hypot(t.x - self.x, t.y - self.y)
                    if dist <= HOMING_DETECTION_RANGE:
                        candidates.append((dist, t))
        if not candidates:
            return None
        # sort by dist
        candidates.sort(key=lambda x: x[0])
        # prefer those with LOS clear? Slight boost
        # pick first with LOS if any within 1.5x
        best = candidates[0][1]
        return best

    def _plan_path(self, tilemap, target_x, target_y):
        """Plan A* from current bullet pos to target."""
        sgx, sgy = _pixel_to_grid(self.x, self.y)
        tgx, tgy = _pixel_to_grid(target_x, target_y)
        # clamp
        sgx = max(0, min(GRID_W-1, sgx))
        sgy = max(0, min(GRID_H-1, sgy))
        tgx = max(0, min(GRID_W-1, tgx))
        tgy = max(0, min(GRID_H-1, tgy))
        path = _a_star_tile(tilemap, sgx, sgy, tgx, tgy)
        if not path:
            self.path = []
            self.path_world = []
            self.path_index = 0
            self.waypoint = None
            return False
        self.path = path
        # convert to world points, skip first (current)
        world = []
        for gx, gy in path[1:]:
            cx, cy = _grid_to_pixel_center(gx, gy)
            world.append((cx, cy))
        # smoothing: prune collinear points plus LOS shortcut
        if len(world) >= 3:
            # simple LOS pruning: if we can see 2 steps ahead, skip intermediate
            pruned = [world[0]]
            i = 0
            while i < len(world):
                # look ahead as far as possible with clear LOS
                furthest = i
                for j in range(len(world)-1, i, -1):
                    if _line_of_sight_clear(tilemap, self.x, self.y, world[j][0], world[j][1]):
                        furthest = j
                        break
                if furthest != i:
                    pruned.append(world[furthest])
                    i = furthest + 1
                else:
                    if i+1 < len(world):
                        pruned.append(world[i+1])
                    i += 1
            world = pruned
        self.path_world = world
        self.path_index = 0
        self.waypoint = world[0] if world else None
        return True

    def _update_waypoint(self, tilemap):
        if not self.path_world:
            return
        if self.waypoint is None:
            return
        # if close to waypoint, go next
        wx, wy = self.waypoint
        dx = wx - self.x
        dy = wy - self.y
        dist = math.hypot(dx, dy)
        # arrival threshold = slightly less than tile size for precision
        if dist < TILE_SIZE * 0.45:
            self.path_index += 1
            if self.path_index < len(self.path_world):
                self.waypoint = self.path_world[self.path_index]
            else:
                self.waypoint = None  # reached end, go direct to target

    def _compute_avoidance(self, tilemap):
        """Compute steering avoidance vector from nearby brick/steel using multi-range lookahead."""
        avx, avy = 0.0, 0.0
        offsets = [0, -0.65, 0.65, -1.3, 1.3]
        # sample at two distances: near and far
        for look_mult in (0.6, 1.0):
            look = TILE_SIZE * HOMING_AVOIDANCE_LOOKAHEAD * look_mult
            ahead_x = self.x + self.vx * look
            ahead_y = self.y + self.vy * look
            for off in offsets:
                px = -self.vy
                py = self.vx
                sx = ahead_x + px * off * TILE_SIZE * 0.6
                sy = ahead_y + py * off * TILE_SIZE * 0.6
                gx, gy = _pixel_to_grid(sx, sy)
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    if _is_blocking_for_homing(tilemap, gx+dx, gy+dy):
                        # repulsion
                        cx, cy = _grid_to_pixel_center(gx+dx, gy+dy)
                        rx = self.x - cx
                        ry = self.y - cy
                        d = math.hypot(rx, ry)
                        if d < 1:
                            d = 1
                        # weight inverse distance, stronger when closer
                        weight = (TILE_SIZE*2.0) / d
                        # forward look weight: more if in front (dot >0)
                        to_obs = (cx - self.x, cy - self.y)
                        dot = to_obs[0]*self.vx + to_obs[1]*self.vy
                        if dot > 0:
                            weight *= 2.0  # stronger for obstacles in front
                        avx += (rx / d) * weight
                        avy += (ry / d) * weight
        # normalize
        norm = math.hypot(avx, avy)
        if norm > 0.01:
            avx /= norm
            avy /= norm
            cgx, cgy = _pixel_to_grid(self.x, self.y)
            imminent = False
            very_close = False
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    if _is_blocking_for_homing(tilemap, cgx+dx, cgy+dy):
                        cx, cy = _grid_to_pixel_center(cgx+dx, cgy+dy)
                        d = math.hypot(cx-self.x, cy-self.y)
                        if d < TILE_SIZE*1.25:
                            imminent = True
                        if d < TILE_SIZE*0.75:
                            very_close = True
            if very_close:
                strength = 2.1
            elif imminent:
                strength = 1.55
            else:
                strength = 0.75
            self.avoid_vector = (avx*strength, avy*strength)
        else:
            self.avoid_vector = (self.avoid_vector[0]*0.72, self.avoid_vector[1]*0.72)

    def _steer_homing(self, tilemap, desired_dx, desired_dy):
        """Steer towards desired direction with avoidance blended, respecting turn_speed."""
        dx = desired_dx
        dy = desired_dy
        ax, ay = self.avoid_vector
        dx += ax
        dy += ay
        dnorm = math.hypot(dx, dy)
        if dnorm < 0.001:
            return
        dx /= dnorm
        dy /= dnorm
        # dynamic turn: faster turn when avoiding (evasion priority)
        avoid_mag = math.hypot(ax, ay)
        turn = self.turn_speed * (1.9 if avoid_mag > 0.9 else 1.0)
        turn = min(turn, 0.22)  # cap
        self.vx = self.vx * (1 - turn) + dx * turn
        self.vy = self.vy * (1 - turn) + dy * turn
        norm = math.hypot(self.vx, self.vy)
        if norm > 0:
            self.vx /= norm
            self.vy /= norm

    def _update_homing(self, tilemap, tanks):
        if not self.homing:
            return
        # Acquire target if none or dead
        if self.target is None or not getattr(self.target, 'alive', False):
            self.target = self._find_nearest_target(tanks)
            # reset path when new target
            if self.target is not None:
                self.replan_timer = 0  # force replan
            self.lost_target_timer = 0
        else:
            # if target far beyond detection and we have no path, maybe pick closer?
            dist_to_target = math.hypot(self.target.x - self.x, self.target.y - self.y)
            if dist_to_target > HOMING_DETECTION_RANGE * 1.4:
                alt = self._find_nearest_target(tanks)
                if alt and alt != self.target:
                    # pick if significantly closer
                    if math.hypot(alt.x - self.x, alt.y - self.y) < dist_to_target * 0.65:
                        self.target = alt
                        self.replan_timer = 0

        if self.target is None:
            # no target - fly straight but still avoid walls for a bit until range expires
            self.lost_target_timer += 1
            self._compute_avoidance(tilemap)
            # avoid only
            if math.hypot(self.avoid_vector[0], self.avoid_vector[1]) > 0.05:
                self._steer_homing(tilemap, self.vx + self.avoid_vector[0], self.vy + self.avoid_vector[1])
            return

        tx, ty = self.target.x, self.target.y

        # Direct LOS check: if direct line clear, go direct (more natural)
        direct = False
        if HOMING_LOS_CHECK:
            if _line_of_sight_clear(tilemap, self.x, self.y, tx, ty):
                # also check distance not too large for direct planning? Always ok
                direct = True

        # Replan logic
        self.replan_timer -= 1
        need_replan = direct == False and (self.replan_timer <= 0 or self.waypoint is None)
        # Also replan if we are stuck (not moving towards target)
        moved_dist = math.hypot(self.x - self.last_pos[0], self.y - self.last_pos[1])
        if moved_dist < 0.7:
            self.stuck_timer += 1
        else:
            self.stuck_timer = max(0, self.stuck_timer - 2)
        if self.stuck_timer > 18:
            need_replan = True
            self.stuck_timer = 0

        if need_replan and not direct:
            self._plan_path(tilemap, tx, ty)
            self.replan_timer = self.replan_interval

        self._update_waypoint(tilemap)
        self._compute_avoidance(tilemap)

        # Decide desired vector
        if direct or self.waypoint is None:
            # go straight to target with prediction?
            # slight prediction based on target velocity if target is moving
            # target velocity estimated from tank's direction & speed?
            pred_x, pred_y = tx, ty
            if hasattr(self.target, 'direction'):
                tdx, tdy = DIRS.get(getattr(self.target, 'direction'), (0,0))
                # if enemy moving, predict a few frames ahead based on dist/speed
                dist = math.hypot(tx - self.x, ty - self.y)
                # time to reach ~ dist / homing_speed
                eta = dist / max(self.speed, 0.1)
                # predict limited (not too far)
                eta = min(eta, 20)
                pred_x = tx + tdx * getattr(self.target, 'speed', 1.2) * eta * 0.35
                pred_y = ty + tdy * getattr(self.target, 'speed', 1.2) * eta * 0.35
            ddx = pred_x - self.x
            ddy = pred_y - self.y
            dlen = math.hypot(ddx, ddy)
            if dlen > 1:
                ddx /= dlen
                ddy /= dlen
            else:
                ddx, ddy = self.vx, self.vy
        else:
            wx, wy = self.waypoint
            ddx = wx - self.x
            ddy = wy - self.y
            dlen = math.hypot(ddx, ddy)
            if dlen > 1:
                ddx /= dlen
                ddy /= dlen
            else:
                ddx, ddy = self.vx, self.vy

        self._steer_homing(tilemap, ddx, ddy)

        # Update dir string for tile destruction if it eventually hits
        best = None
        best_dot = -2
        for dname, (ddx, ddy) in DIRS.items():
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

        # remember last for stuck detection
        self.last_pos = (self.x, self.y)

        # homing steering
        if self.homing:
            self._update_homing(tilemap, tanks)

        # move - use vx,vy for homing, else use DIRS[dir]
        if self.homing:
            nx = self.x + self.vx * self.speed
            ny = self.y + self.vy * self.speed
            # travel tracking
            self.travelled += math.hypot(nx - self.x, ny - self.y)
            self.x = nx
            self.y = ny
            # check max distance - exhaust
            if self.travelled >= self.max_distance:
                self.alive = False
                return 'out_of_fuel'
        else:
            dx, dy = DIRS.get(self.dir, (0, -1))
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

        # tile collision - for homing missile, we AVOID rather than explode on brick/steel
        # So if homing, check if we are colliding with blocking tile: instead try to slide away, only die if truly stuck inside wall
        gx = int((self.x - PLAYFIELD_X) // TILE_SIZE)
        gy = int((self.y - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            tt = tilemap.tiles[gy][gx]
            if tt == TILE_BRICK:
                if self.homing:
                    # Smart missile: NEVER destroy brick unless absolutely trapped.
                    # Requirement: avoid hitting brick and walls.
                    # So we do elastic bounce + aggressive replanning.
                    # Only after 45+ stuck frames in tight corridor and target beyond, we allow destroy as last resort.
                    if self.stuck_timer > HOMING_STUCK_DESTROY_THRESHOLD + 30:
                        # truly trapped, break brick to escape as last resort
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
                    else:
                        # elastic bounce: step back 2.2x speed
                        self.x -= self.vx * self.speed * 2.2
                        self.y -= self.vy * self.speed * 2.2
                        # inject strong perpendicular avoidance + away vector
                        cx, cy = _grid_to_pixel_center(gx, gy)
                        away_x = self.x - cx
                        away_y = self.y - cy
                        norm = math.hypot(away_x, away_y) or 1
                        away_x /= norm
                        away_y /= norm
                        # add perpendicular jitter to escape corridors
                        perp_x = -away_y
                        perp_y = away_x
                        # alternate left/right based on stuck parity
                        sign = 1 if (self.stuck_timer % 2 == 0) else -1
                        self.vx = away_x * 0.7 + perp_x * 0.35 * sign + self.vx * 0.15
                        self.vy = away_y * 0.7 + perp_y * 0.35 * sign + self.vy * 0.15
                        n = math.hypot(self.vx, self.vy) or 1
                        self.vx /= n
                        self.vy /= n
                        # boost avoidance vector for next frames
                        self.avoid_vector = (away_x * 2.0, away_y * 2.0)
                        self.rect.center = (self.x, self.y)
                        self.replan_timer = 0
                        self.stuck_timer += 7
                        # continue flying
                else:
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
                if self.homing:
                    # Steel = hard wall, always avoid. Never destroy unless power>=2 and extremely stuck (60 frames)
                    if self.power >= 2 and self.stuck_timer > HOMING_STUCK_DESTROY_THRESHOLD + 45:
                        destroyed = False
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
                    else:
                        self.x -= self.vx * self.speed * 2.4
                        self.y -= self.vy * self.speed * 2.4
                        self.rect.center = (self.x, self.y)
                        cx, cy = _grid_to_pixel_center(gx, gy)
                        away_x = self.x - cx
                        away_y = self.y - cy
                        norm = math.hypot(away_x, away_y) or 1
                        away_x /= norm
                        away_y /= norm
                        perp_x = -away_y
                        perp_y = away_x
                        sign = 1 if (self.stuck_timer % 2 == 0) else -1
                        self.vx = away_x * 0.75 + perp_x * 0.4 * sign + self.vx * 0.1
                        self.vy = away_y * 0.75 + perp_y * 0.4 * sign + self.vy * 0.1
                        n = math.hypot(self.vx, self.vy) or 1
                        self.vx /= n
                        self.vy /= n
                        self.avoid_vector = (away_x * 2.2, away_y * 2.2)
                        self.replan_timer = 0
                        self.stuck_timer += 8
                else:
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

        # base collision
        if base and base.alive:
            if base.rect.collidepoint(self.x, self.y):
                # Homing should never hit own base? If player missile, avoid base too? But base is at bottom, usually not in path to enemies.
                # Allow homing to avoid base similarly? For now keep behavior: if homing from player, avoid base as obstacle? Base is not in tilemap, but we can treat as blocking for player homing.
                if self.homing and self.owner.startswith('player'):
                    # bounce away from base
                    cx, cy = base.rect.center
                    away_x = self.x - cx
                    away_y = self.y - cy
                    norm = math.hypot(away_x, away_y) or 1
                    self.vx = self.vx * 0.3 + (away_x / norm) * 0.7
                    self.vy = self.vy * 0.3 + (away_y / norm) * 0.7
                    nn = math.hypot(self.vx, self.vy) or 1
                    self.vx /= nn
                    self.vy /= nn
                    self.x += self.vx * self.speed
                    self.y += self.vy * self.speed
                    self.rect.center = (self.x, self.y)
                else:
                    base.take_damage()
                    self.alive = False
                    try:
                        from ..sound_manager import sound_manager
                        sound_manager.play_explosion(big=True)
                    except:
                        pass
                    return 'hit_base'

        # tank collision + explosion SFX
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
                # venom handling
                if getattr(self, 'venom', False):
                    if tank.is_player and not getattr(tank, 'is_boss', False):
                        # apply venom to player
                        if hasattr(tank, 'venom_timer'):
                            tank.venom_timer = VENOM_DISSOLVE_TIME
                            tank.venom_level = 0.0
                            self.alive = False
                            return 'venom_hit'
                        # if no venom field, just damage
                    else:
                        # venom doesn't affect enemies
                        self.alive = False
                        return 'blocked'
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
        # trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / len(self.trail) if self.trail else 0
            size = int((BULLET_SIZE+2) * alpha)
            if size > 0:
                if self.homing:
                    # orange flame fading, plus distance fade when near max
                    fade = 1.0
                    if hasattr(self, 'travelled') and hasattr(self, 'max_distance'):
                        ratio = self.travelled / max(self.max_distance, 1)
                        fade = max(0.15, 1.0 - ratio*0.65)  # fade as fuel low
                    r = int((255 * alpha + 100 * (1-alpha)) * fade)
                    g = int((140 * alpha + 50 * (1-alpha)) * fade)
                    b = 0
                    pygame.draw.circle(screen, (r, g, b), (int(tx), int(ty)), max(1, int((size//2 + 1)*fade)))
                else:
                    pygame.draw.circle(screen, (100, 100, 100), (int(tx), int(ty)), size//2)
        # bullet body
        if self.homing:
            # missile shape: elongated with direction + fuel indicator
            # fuel low -> flicker red
            fuel_ratio = 1.0
            if hasattr(self, 'travelled'):
                fuel_ratio = max(0, 1.0 - self.travelled / max(self.max_distance, 1))
            base_col = self.color
            if fuel_ratio < 0.25:
                # flicker red when low
                if pygame.time.get_ticks() % 200 < 100:
                    base_col = (255, 40, 40)
            pygame.draw.circle(screen, base_col, (int(self.x), int(self.y)), BULLET_SIZE//2 + 3)
            pygame.draw.circle(screen, (255, 220, 0), (int(self.x), int(self.y)), BULLET_SIZE//2 + 1)
            # direction indicator line
            if hasattr(self, 'vx'):
                lx = int(self.x - self.vx * 8)
                ly = int(self.y - self.vy * 8)
                pygame.draw.line(screen, (255, 80, 0), (int(self.x), int(self.y)), (lx, ly), 2)
            # waypoint debug? Disabled, but useful: draw small waypoint marker
            # if self.waypoint:
            #     pygame.draw.circle(screen, (0,255,0), (int(self.waypoint[0]), int(self.waypoint[1])), 3, 1)
            # draw remaining range circle when very low? Not needed but helpful visual: draw faint range
            if fuel_ratio < 0.35:
                # draw dashed low fuel warning ring? Keep minimal
                pass
            # Draw avoidance vector debug? ignore
        elif getattr(self, 'venom', False):
            # Venom spit - gooey green blob with drips
            pygame.draw.circle(screen, (20, 100, 20), (int(self.x), int(self.y)), BULLET_SIZE//2 + 3)
            pygame.draw.circle(screen, (80, 220, 80), (int(self.x), int(self.y)), BULLET_SIZE//2 + 1)
            pygame.draw.circle(screen, (160, 255, 160), (int(self.x)+1, int(self.y)-1), 2)
            # drip trail
            for i, (tx, ty) in enumerate(self.trail[-4:]):
                pygame.draw.circle(screen, (60, 180, 60), (int(tx), int(ty+2)), 2)
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
