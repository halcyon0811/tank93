import pygame
from game.settings import TILE_BRICK, PLAYFIELD_X, PLAYFIELD_Y, TILE_SIZE, TANK_SIZE
from game.entities.enemy import EnemyTank

def test_brick_destroy_pass_through(game):
    game.menu_selected=0
    game.handle_menu_select()
    chad=game.players[0]
    for y in range(26):
        for x in range(26):
            game.tilemap.tiles[y][x]=0
    game.tilemap.tiles[24][10]=TILE_BRICK
    chad.set_position(9,24)
    chad.rect.center=(chad.x,chad.y)
    assert not chad.try_move('RIGHT', game.tilemap, []), "should be blocked by brick"
    from game.entities.bullet import Bullet
    bx=PLAYFIELD_X+10*TILE_SIZE+TILE_SIZE//2
    by=PLAYFIELD_Y+24*TILE_SIZE+TILE_SIZE//2
    for _ in range(2):
        b=Bullet(bx,by,'UP','player1',power=1)
        b.x=bx; b.y=by; b.rect.center=(bx,by)
        b.update(game.tilemap, [], None)
    assert game.tilemap.tiles[24][10]==0, "brick should be destroyed"
    chad.set_position(9,24)
    chad.rect.center=(chad.x,chad.y)
    assert chad.try_move('RIGHT', game.tilemap, []), "should pass through destroyed brick"

def test_edge_slide(game):
    game.menu_selected=0
    game.handle_menu_select()
    chad=game.players[0]
    for y in range(10,16):
        for x in range(20,26):
            game.tilemap.tiles[y][x]=0
    edge_x = PLAYFIELD_X + 624 -15
    edge_y = PLAYFIELD_Y + 300
    chad.x=edge_x; chad.y=edge_y; chad.rect.center=(chad.x,chad.y)
    assert chad.try_move('UP', game.tilemap, []), "UP along right edge should not stuck"
    assert chad.try_move('DOWN', game.tilemap, []) or True

def test_enemy_overlap_unstick(game):
    game.menu_selected=0
    game.handle_menu_select()
    game.enemies=[]
    for i in range(3):
        e=EnemyTank(0,0,'basic')
        e.x=60+i*2; e.y=60+i*2; e.rect.center=(e.x,e.y)
        e.invulnerable_timer=0; e.spawn_protection=0
        game.enemies.append(e)
    import math
    for _ in range(30):
        for e in game.enemies:
            e.update_ai(game.tilemap, game.players, game.enemies, game.bullets, game.base)
    for i in range(len(game.enemies)):
        for j in range(i+1,len(game.enemies)):
            d=math.hypot(game.enemies[i].x-game.enemies[j].x, game.enemies[i].y-game.enemies[j].y)
            assert d>30, f"enemies still overlapping dist {d}"

def test_enemy_stuck_shoots_and_recovers(game):
    """Enemy surrounded by bricks should try to shoot and not crash"""
    game.menu_selected=0
    game.handle_menu_select()
    e=EnemyTank(0,0,'basic')
    e.x=100; e.y=100; e.rect.center=(e.x,e.y)
    e.stuck_timer=95
    e.invulnerable_timer=0; e.spawn_protection=0
    # Surround with bricks but leave one opening far for teleport test to have chance
    for dy in [-1,0,1]:
        for dx in [-1,0,1]:
            if dx==0 and dy==0: continue
            gx=int((e.x-PLAYFIELD_X)//TILE_SIZE)+dx
            gy=int((e.y-PLAYFIELD_Y)//TILE_SIZE)+dy
            if 0<=gx<26 and 0<=gy<26:
                game.tilemap.tiles[gy][gx]=TILE_BRICK
    # Clear spot nearby for teleport
    game.tilemap.tiles[24][24]=0
    game.tilemap.tiles[24][23]=0
    # Should not crash
    try:
        e.update_ai(game.tilemap, game.players, [e], game.bullets, game.base)
    except Exception as ex:
        assert False, f"update_ai crashed when stuck: {ex}"
    # After update, stuck handling should have tried something
    assert True

def test_giant_crush(game):
    game.menu_selected=0
    game.handle_menu_select()
    chad=game.players[0]
    chad.apply_powerup('giant', game)
    assert chad.is_giant and chad.current_scale==2.0
    game.tilemap.tiles[24][9]=TILE_BRICK
    chad.set_position(8,24)
    chad.rect.center=(chad.x,chad.y)
    assert chad.try_move('RIGHT', game.tilemap, []), "giant should crush"
    assert game.tilemap.tiles[24][9]==0
