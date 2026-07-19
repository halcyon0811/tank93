import pygame, time, math, random
from game.entities.enemy import EnemyTank

def test_full_game_400_frames_no_crash(game):
    game.menu_selected=0
    game.handle_menu_select()
    for frame in range(400):
        game.handle_events()
        assert game.state=='playing', f"bounced at {frame} to {game.state}"
        game.update_playing(16)
        game.draw()
    # Check DB
    from tests.conftest import get_db
    dl=get_db()
    bounces=dl.query_sql("SELECT * FROM state_changes WHERE old_state='playing' AND new_state='menu' AND reason LIKE '%CRASH%'")
    assert len(bounces)==0
    exc=dl.query_sql("SELECT * FROM exceptions_log")
    assert len(exc)==0

def test_boss_escape_and_homing_track(game):
    game.menu_selected=0
    game.handle_menu_select()
    bx,by=game.tilemap.base_pos
    walls_before=sum(1 for dy in range(-1,3) for dx in range(-1,3) if 0<=bx+dx<26 and 0<=by+dy<26 and game.tilemap.tiles[by+dy][bx+dx]!=0)
    game.base.take_damage()
    game.release_monster_boss()
    boss=game.boss_enemy
    assert boss is not None
    walls_after=sum(1 for dy in range(-1,3) for dx in range(-1,3) if 0<=bx+dx<26 and 0<=by+dy<26 and game.tilemap.tiles[by+dy][bx+dx]!=0)
    # After release, walls should be mostly intact except 1 opening (partial)
    assert walls_after >= walls_before-2, "boss should be trapped with partial walls"
    # Boss should be able to crush
    boss.invulnerable_timer=0
    boss.spawn_protection=0
    # Try to move and crush
    for _ in range(20):
        boss.try_move('UP', game.tilemap, game.enemies)
    # Should have crushed some
    # Test homing missile prioritizes boss
    from game.entities.bullet import Bullet
    from game.settings import PLAYFIELD_X, PLAYFIELD_Y
    boss.x=PLAYFIELD_X+300; boss.y=PLAYFIELD_Y+300; boss.rect.center=(boss.x,boss.y)
    bullet=Bullet(PLAYFIELD_X+100, PLAYFIELD_Y+100, 'RIGHT', 'player1', power=2, homing=True, bullet_type='power_homing')
    bullet.x=PLAYFIELD_X+100; bullet.y=PLAYFIELD_Y+100; bullet.rect.center=(bullet.x,bullet.y)
    target=bullet._find_nearest_target([boss])
    assert target and getattr(target,'is_boss',False), "homing should prioritize boss"

def test_2p_life_share(game):
    game.menu_selected=0
    game.handle_menu_select()
    game.player_join(2)
    chad=game.players[0]; lida=game.players[1]
    chad.lives=5; lida.lives=1
    assert game.share_life()
    assert chad.lives==4 and lida.lives==2
    # Dead Lida
    lida.lives=-1; lida.alive=False
    chad.lives=3
    assert game.share_life()
    assert lida.alive and lida.lives==0

def test_venom_spillover(game):
    game.menu_selected=0
    game.handle_menu_select()
    chad=game.players[0]
    e=EnemyTank(9,24,'basic')
    e.x=chad.x+30; e.y=chad.y; e.rect.center=(e.x,e.y)
    e.invulnerable_timer=0; e.spawn_protection=0; e.armor=0; e.health=1
    game.enemies=[e]
    from game.settings import VENOM_DISSOLVE_TIME
    chad.venom_timer=VENOM_DISSOLVE_TIME
    chad.venom_level=0.0
    for _ in range(25):
        game.update_playing(16)
    assert not e.alive, "venom spillover should kill nearby enemy"

def test_stage_clear_flow(game):
    game.menu_selected=0
    game.handle_menu_select()
    # Kill all enemies quickly via bomb (armor damage)
    # Spawn armor enemies that need 2 bombs
    game.enemies=[]
    for i in range(3):
        e=EnemyTank(i*2,2,'basic')
        e.armor=0; e.health=1; e.invulnerable_timer=0; e.spawn_protection=0
        game.enemies.append(e)
    game.enemies_total=3
    game.enemies_killed=0
    chad=game.players[0]
    game.apply_powerup('grenade', chad)
    game.update_playing(16)
    assert game.enemies_killed==3
    game.update_playing(16)
    assert game.state=='stage_clear'

def test_fuzz_monkey_no_crash(game):
    """Random inputs for 500 frames should not crash"""
    game.menu_selected=0
    game.handle_menu_select()
    random.seed(0)
    keys=[pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_SPACE, pygame.K_p, pygame.K_l, pygame.K_n]
    for frame in range(500):
        # Post random key
        if random.random()<0.1:
            k=random.choice(keys)
            ev=pygame.event.Event(pygame.KEYDOWN, key=k, mod=0)
            pygame.event.post(ev)
        game.handle_events()
        if game.state!='playing':
            # If paused, resume
            if game.state=='paused':
                ev=pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)
                pygame.event.post(ev)
                game.handle_events()
                assert game.state=='playing'
            else:
                break
        try:
            game.update_playing(16)
            game.draw()
        except Exception as e:
            assert False, f"Crash at frame {frame}: {e}"
    from tests.conftest import get_db
    dl=get_db()
    bounces=dl.query_sql("SELECT * FROM state_changes WHERE reason LIKE '%CRASH%'")
    assert len(bounces)==0
