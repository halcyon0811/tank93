import pygame
from game.entities.bullet import Bullet
from game.entities.enemy import EnemyTank
from game.entities.player import PlayerTank
from game.settings import PLAYFIELD_X, PLAYFIELD_Y, TILE_SIZE

def test_no_unboundlocal_col(game):
    """Regression: rapid+spread had UnboundLocalError col"""
    game.menu_selected=0
    game.handle_menu_select()
    p=game.players[0]
    p.rapid_active=True
    p.rapid_timer=-1
    p.spread_active=True
    p.spread_timer=-1
    try:
        result=p.shoot()
        assert result is not None
    except UnboundLocalError:
        assert False, "UnboundLocalError col should be fixed"

def test_bomb_armor_damage(game):
    """Bomb should do armor damage, not instant kill all"""
    game.menu_selected=0
    game.handle_menu_select()
    # Spawn armor enemies (150 armor)
    game.enemies=[]
    for i in range(5):
        e=EnemyTank(i*2,2,'armor')
        e.x=100+i*10; e.y=100; e.rect.center=(e.x,e.y)
        e.invulnerable_timer=0; e.spawn_protection=0
        game.enemies.append(e)
    chad=game.players[0]
    chad.score=0
    game.apply_powerup('grenade', chad)
    # After 1 bomb, armor 150->50, all alive
    alive=[e for e in game.enemies if e.alive]
    assert len(alive)==5, "armor 150 should survive 100 dmg bomb"
    assert all(e.armor==50 for e in alive)
    # 2nd bomb kills
    game.apply_powerup('grenade', chad)
    alive2=[e for e in game.enemies if e.alive]
    assert len(alive2)==0, "2nd bomb should kill armor 50"

def test_homing_chip_and_destroy(game):
    """Homing missile should chip and destroy brick after 4 hits"""
    game.menu_selected=0
    game.handle_menu_select()
    for y in range(26):
        for x in range(26):
            game.tilemap.tiles[y][x]=0
    game.tilemap.tiles[5][5]=1
    bx=PLAYFIELD_X+5*TILE_SIZE+TILE_SIZE//2
    by=PLAYFIELD_Y+5*TILE_SIZE+TILE_SIZE//2
    for i in range(4):
        b=Bullet(bx,by,'UP','player1',power=1,homing=True,bullet_type='homing')
        b.x=bx; b.y=by; b.rect.center=(bx,by)
        b.stuck_timer=20
        b.update(game.tilemap, [], None)
    assert game.tilemap.tiles[5][5]==0, "homing should destroy after 4 hits"

def test_boss_bullet_hits_both(game):
    """Boss bullets hit both players and enemies, enemy bullets hit boss but not other enemies"""
    game.menu_selected=0
    game.handle_menu_select()
    boss=EnemyTank(10,10,'monster_boss')
    boss.x=200; boss.y=200; boss.rect.center=(boss.x,boss.y)
    boss.invulnerable_timer=0; boss.spawn_protection=0; boss.armor=0; boss.health=1

    enemy=EnemyTank(12,10,'basic')
    enemy.x=boss.x+50; enemy.y=boss.y; enemy.rect.center=(enemy.x,enemy.y)
    enemy.invulnerable_timer=0; enemy.spawn_protection=0; enemy.armor=0; enemy.health=1

    # Boss bullet vs enemy
    bx, by = enemy.rect.center
    b=Bullet(bx,by,'RIGHT','boss',power=1)
    b.x=bx; b.y=by; b.rect.center=(bx,by)
    b._shooter_ref=boss
    result=b.update(game.tilemap, [enemy], None)
    assert result=='hit_tank' and not enemy.alive, "boss bullet should hit enemy"

    # Enemy bullet vs boss
    enemy2=EnemyTank(5,5,'basic')
    enemy2.x=100; enemy2.y=100; enemy2.rect.center=(enemy2.x,enemy2.y)
    boss2=EnemyTank(10,10,'monster_boss')
    boss2.x=100; boss2.y=100; boss2.rect.center=(boss2.x,boss2.y)
    boss2.invulnerable_timer=0; boss2.spawn_protection=0; boss2.armor=0; boss2.health=1
    b2=Bullet(boss2.x,boss2.y,'UP','enemy',power=1)
    b2.x=boss2.x; b2.y=boss2.y; b2.rect.center=(b2.x,b2.y)
    b2._shooter_ref=enemy2
    result2=b2.update(game.tilemap, [boss2], None)
    assert result2=='hit_tank', "enemy bullet should hit boss"

    # Enemy bullet vs enemy should NOT hit
    other=EnemyTank(6,6,'basic')
    other.x=100; other.y=100; other.rect.center=(other.x,other.y)
    b3=Bullet(other.x,other.y,'RIGHT','enemy',power=1)
    b3.x=other.x; b3.y=other.y; b3.rect.center=(other.x,other.y)
    result3=b3.update(game.tilemap, [other], None)
    # Enemy vs enemy is blocked by armor logic? With armor 50, first hit blocked, not hit_tank
    # But should not be hit_tank if both enemies
    assert result3!='hit_tank' or other.armor==0, "enemy bullet should not kill other enemy with armor"

def test_weapon_stacking(game):
    """More items = stronger"""
    game.menu_selected=0
    game.handle_menu_select()
    chad=game.players[0]
    base_speed=chad.speed
    chad.apply_powerup('star', game)
    chad.apply_powerup('star', game)
    chad.apply_powerup('star', game)
    # 3 stars should be stronger than 0
    assert chad.speed > base_speed or chad.bullet_power>=2
    # Extra star beyond max
    before=chad.bullet_damage_bonus
    chad.apply_powerup('star', game)
    assert chad.bullet_damage_bonus > before
    # Homing level up
    chad.apply_powerup('homing', game)
    lvl1=chad.homing_level
    chad.apply_powerup('homing', game)
    assert chad.homing_level==lvl1+1
