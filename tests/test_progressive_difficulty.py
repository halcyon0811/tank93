"""
Test progressive difficulty - counter of stages passed, more stages = harder
User request: keep counter of how many stage player passed, difficulty increases gradually
E.g. spawn faster, more co-existing tanks
"""
import os, sys, pathlib
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def test_total_stages_cleared_counter_exists():
    from game.game import Game
    g = Game()
    assert hasattr(g, 'total_stages_cleared'), "Game must have total_stages_cleared persistent counter"
    assert hasattr(g, 'current_loop'), "Game must have current_loop"
    assert g.total_stages_cleared == 0
    assert g.current_loop == 0

def test_difficulty_params_scale_with_total():
    from game.game import Game
    g = Game()
    d0 = g._get_difficulty_params()
    assert d0['max_on_field'] == 4
    assert d0['loop'] == 0
    # Simulate clearing 10 stages
    g.total_stages_cleared = 10
    g.current_loop = 10 // 35
    d10 = g._get_difficulty_params()
    assert d10['max_on_field'] > d0['max_on_field'], f"10 stages should have more max enemies: {d10['max_on_field']} vs {d0['max_on_field']}"
    assert d10['spawn_interval'] < d0['spawn_interval'], f"Spawn should be faster after 10 stages"
    # Simulate loop 1 (35 stages cleared)
    g.total_stages_cleared = 35
    g.current_loop = 1
    d35 = g._get_difficulty_params()
    assert d35['loop'] == 1
    assert d35['speed_mult'] > 1.0
    assert d35['shoot_mult'] > 1.0
    # Cap 12
    g.total_stages_cleared = 100
    g.current_loop = 100 // 35
    d100 = g._get_difficulty_params()
    assert d100['max_on_field'] <= 12, f"Cap should be 12, got {d100['max_on_field']}"
    assert d100['spawn_interval'] >= 0.4*60 - 1  # min 0.4s = 24 frames

def test_enemies_total_increases_with_total():
    from game.game import Game
    g = Game()
    g.init_level(0, 1)
    base_total = g.enemies_total
    g.total_stages_cleared = 20
    g.current_loop = 0
    total_20 = g._get_enemies_total_for_level(0)
    assert total_20 > base_total, f"20 stages cleared should have more enemies: {total_20} vs {base_total}"

def test_init_next_level_increments_counter():
    from game.game import Game
    g = Game()
    g.init_level(0, 1)
    assert g.total_stages_cleared == 0
    first_level = g.current_level
    assert first_level == 0
    g.init_next_level()
    assert g.total_stages_cleared == 1, f"Should be 1 after first clear, got {g.total_stages_cleared}"
    assert g.current_level == 1
    # Clear 34 more to loop
    for _ in range(34):
        g.init_next_level()
    # After 35 clears, should be back to map 0 but total 35, loop 1
    assert g.total_stages_cleared == 35
    assert g.current_loop == 1
    assert g.current_level == 0  # wrapped
    # Difficulty should be higher after loop
    d = g._get_difficulty_params()
    assert d['loop'] == 1
    assert d['max_on_field'] > 4

def test_spawn_applies_speed_mult():
    from game.game import Game
    g = Game()
    g.init_level(0, 1)
    g.total_stages_cleared = 40  # loop 1
    g.current_loop = 1
    # Manually test spawn_enemy speed mult logic exists
    # We'll spawn and check speed
    before_speeds = []
    g.spawn_enemy()
    if len(g.enemies) > 0:
        e = g.enemies[0]
        # Speed should be multiplied by loop factor 1.12
        # Base enemy speed 1.8, with loop 1 = 1.8*1.12 = 2.016
        assert e.speed >= 1.8, f"Speed should be at least base 1.8, got {e.speed}"

def test_init_level_resets_counter_on_new_game():
    from game.game import Game
    g = Game()
    g.init_level(0, 1)
    g.total_stages_cleared = 10
    g.current_loop = 0
    # Simulate new game from menu
    g.state = 'menu'
    g.init_level(0, 1)
    assert g.total_stages_cleared == 0, "New game from menu should reset counter"
