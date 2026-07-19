"""E2E test: no tank should be stuck at edge of map or inside wall/brick/concrete (steel).

Covers user reports:
- enemy tank outside map boundary
- player tank stuck attached to edge
- destroyed brick channel too small to pass (now 20px collision)
"""
import pygame
import math
import random
from game.settings import PLAYFIELD_X, PLAYFIELD_W, PLAYFIELD_Y, PLAYFIELD_H, TANK_SIZE, TILE_SIZE, GRID_W, GRID_H, TILE_BRICK, TILE_STEEL
from game.entities.enemy import EnemyTank


def _assert_inside_playfield(tank, msg=""):
    """Tank rect must be fully inside playfield (with tiny 2px tolerance for rounding)"""
    assert tank.rect.left >= PLAYFIELD_X - 2, f"{msg} left outside: {tank.rect.left} < {PLAYFIELD_X} tank pos {tank.x},{tank.y}"
    assert tank.rect.right <= PLAYFIELD_X + PLAYFIELD_W + 2, f"{msg} right outside: {tank.rect.right} > {PLAYFIELD_X+PLAYFIELD_W}"
    assert tank.rect.top >= PLAYFIELD_Y - 2, f"{msg} top outside: {tank.rect.top} < {PLAYFIELD_Y}"
    assert tank.rect.bottom <= PLAYFIELD_Y + PLAYFIELD_H + 2, f"{msg} bottom outside: {tank.rect.bottom} > {PLAYFIELD_Y+PLAYFIELD_H}"


def _assert_not_inside_wall(tank, tilemap, msg=""):
    """Normal tank (not giant/boss) should not be inside brick/steel with its 20x20 collision rect"""
    if not tank.alive:
        return
    is_giant = getattr(tank, 'is_giant', False) and getattr(tank, 'giant_timer', 0) > 0
    is_boss = getattr(tank, 'is_boss', False)
    if is_giant or is_boss:
        return  # giant/boss can crush, allowed to intersect briefly
    # Use same collision rect as Tank.try_move: 20x20 (inflate -12)
    check_rect = tank.rect.inflate(-12, -12)
    tiles = tilemap.get_tiles_in_rect(check_rect)
    for ttype, gx, gy, trect in tiles:
        if check_rect.colliderect(trect):
            # If it's brick/steel and we are intersecting, it's stuck inside wall
            assert False, f"{msg} tank {getattr(tank, 'player_id', getattr(tank, 'enemy_type', 'enemy'))} inside wall at grid {(gx,gy)} type={ttype} tank rect {tank.rect} check_rect {check_rect} tile rect {trect} pos {tank.x:.1f},{tank.y:.1f}"


def test_no_tank_outside_map_random_play(game):
    """Run 600 frames with random inputs, ensure no tank ever outside playfield."""
    game.menu_selected = 0
    game.handle_menu_select()
    random.seed(1)
    # Add second player for 2P edge case
    game.player_join(2)

    for frame in range(600):
        # Random key spam to push tanks to edges
        if random.random() < 0.15:
            k = random.choice([pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                               pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT])
            ev = pygame.event.Event(pygame.KEYDOWN, key=k, mod=0)
            pygame.event.post(ev)
        game.handle_events()
        if game.state != 'playing':
            if game.state == 'paused':
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)
                pygame.event.post(ev)
                game.handle_events()
            else:
                break
        game.update_playing(16)

        # Check all tanks inside
        for p in game.players:
            if p.alive:
                _assert_inside_playfield(p, f"Player {p.player_id} frame {frame}")
        for e in game.enemies:
            if e.alive:
                _assert_inside_playfield(e, f"Enemy {e.enemy_type} frame {frame} at grid {(e.x, e.y)}")

    # Final check
    assert len(game.players) >= 1


def test_no_tank_inside_brick_or_steel(game):
    """Ensure no tank ever ends up inside a brick/steel tile (stuck within wall)."""
    game.menu_selected = 0
    game.handle_menu_select()
    random.seed(42)
    game.player_join(2)

    for frame in range(500):
        # Push towards walls
        if frame % 20 == 0:
            # Try to push player into nearby brick wall
            ev = pygame.event.Event(pygame.KEYDOWN, key=random.choice([pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d]), mod=0)
            pygame.event.post(ev)
        game.handle_events()
        if game.state != 'playing':
            if game.state == 'paused':
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)
                pygame.event.post(ev)
                game.handle_events()
            else:
                break
        game.update_playing(16)

        # Check inside wall
        for p in game.players:
            if p.alive:
                _assert_not_inside_wall(p, game.tilemap, f"Player {p.player_id} frame {frame}")
        for e in game.enemies:
            if e.alive:
                _assert_not_inside_wall(e, game.tilemap, f"Enemy frame {frame}")

    # Also check initial spawn positions are not inside walls
    for p in game.players:
        if p.alive:
            _assert_not_inside_wall(p, game.tilemap, "Player spawn")


def test_edge_sliding_not_stuck(game):
    """Tank at right/left/top/bottom edge moving along edge should slide, not get stuck."""
    game.menu_selected = 1  # 2P map
    game.handle_menu_select()
    # Clear map to empty for edge test (no bricks)
    from game.tilemap import TileMap
    tm = TileMap(is_mega=False)
    for y in range(tm.grid_h):
        for x in range(tm.grid_w):
            tm.tiles[y][x] = 0
    game.tilemap = tm

    from game.entities.tank import Tank
    # Place tank at right edge, try to move UP (should slide)
    t = Tank(20, 12, (255, 0, 0), is_player=True)
    t.x = PLAYFIELD_X + PLAYFIELD_W - TANK_SIZE//2 - 1
    t.y = PLAYFIELD_Y + PLAYFIELD_H//2
    t.rect.center = (t.x, t.y)

    start_y = t.y
    for _ in range(20):
        moved = t.try_move('UP', tm, [])
        # Should be able to move up even at right edge
        # If stuck, y won't change
    assert t.y < start_y, f"Tank at right edge should slide UP, but y stayed {t.y} vs {start_y}"
    _assert_inside_playfield(t, "after sliding up at right edge")

    # Left edge
    t2 = Tank(20, 12, (0, 255, 0), is_player=True)
    t2.x = PLAYFIELD_X + TANK_SIZE//2 + 1
    t2.y = PLAYFIELD_Y + 300
    t2.rect.center = (t2.x, t2.y)
    start_y2 = t2.y
    for _ in range(20):
        t2.try_move('DOWN', tm, [])
    assert t2.y > start_y2, "Tank at left edge should slide DOWN"
    _assert_inside_playfield(t2, "left edge down slide")


def test_destroyed_brick_channel_passable(game):
    """Single destroyed brick (24px gap) must be passable by normal tank (20px collision) even with slight misalignment."""
    game.menu_selected = 0
    game.handle_menu_select()
    from game.tilemap import TileMap
    from game.entities.tank import Tank

    tm = TileMap(is_mega=False)
    for y in range(tm.grid_h):
        for x in range(tm.grid_w):
            tm.tiles[y][x] = 0
    # Vertical wall at x=12, y=10-15 with single gap at 12,12
    wall_x = 12
    for wy in range(10, 16):
        if wy == 12:
            continue
        tm.tiles[wy][wall_x] = TILE_BRICK
    game.tilemap = tm

    t = Tank(10, 12, (255, 0, 0), is_player=True)
    t.x = PLAYFIELD_X + 10 * TILE_SIZE + TILE_SIZE//2
    t.y = PLAYFIELD_Y + 12 * TILE_SIZE + TILE_SIZE//2
    t.rect.center = (t.x, t.y)

    # Try to go through gap
    for _ in range(40):
        moved = t.try_move('RIGHT', tm, [])
        # Also test _assert_not_inside_wall during pass
        if t.alive:
            _assert_not_inside_wall(t, tm, "while passing gap")

    grid_x = (t.x - PLAYFIELD_X) / TILE_SIZE
    assert grid_x > 12.5, f"Tank should have passed through single brick gap, grid_x={grid_x:.2f}"

    # With 6px misalignment
    t2 = Tank(10, 12, (0, 255, 0), is_player=True)
    t2.x = PLAYFIELD_X + 10 * TILE_SIZE + TILE_SIZE//2
    t2.y = PLAYFIELD_Y + 12 * TILE_SIZE + TILE_SIZE//2 + 6  # 6px off
    t2.rect.center = (t2.x, t2.y)
    for _ in range(40):
        t2.try_move('RIGHT', tm, [])
    grid_x2 = (t2.x - PLAYFIELD_X) / TILE_SIZE
    assert grid_x2 > 12.5, f"Tank with 6px offset should slide through gap via offset logic, grid_x={grid_x2:.2f}"


def test_steel_destruction_not_blocking_forever(game):
    """Steel should be destructible (5 normal hits) so tank doesn't get permanently blocked by steel."""
    from game.tilemap import TileMap
    from game.settings import TILE_STEEL
    tm = TileMap(is_mega=False)
    for y in range(tm.grid_h):
        for x in range(tm.grid_w):
            tm.tiles[y][x] = 0
    tm.tiles[12][12] = TILE_STEEL
    tm.brick_health = {}

    # Hit steel 5 times with normal bullets
    for i in range(5):
        destroyed = tm.destroy_tile(12, 12, bullet_power=1, bullet_type='normal')
        if i < 4:
            assert not destroyed, f"Steel should not be destroyed after {i+1} hits"
        else:
            assert destroyed, "Steel should be destroyed after 5 normal hits"
    assert tm.tiles[12][12] == 0, "Steel tile should be empty after 5 hits"

    # Power should be 2 hits (base 3 minus 1 reduction = 2)
    tm.tiles[10][10] = TILE_STEEL
    tm.brick_health = {}
    for i in range(2):
        destroyed = tm.destroy_tile(10, 10, bullet_power=2, bullet_type='power')
        if i == 0:
            assert not destroyed, "Steel should need 2 power hits"
        else:
            assert destroyed, "Steel should be destroyed after 2 power hits"
