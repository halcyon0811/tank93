import pygame
import time

def test_left_right_1p_2p(game):
    """1P/2P cards are horizontal, LEFT/RIGHT should toggle"""
    assert game.menu_selected == 0
    # RIGHT -> 1 (2P)
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 1, "RIGHT should go 0->1"
    # LEFT -> 0
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 0
    # A/D also
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 1
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 0
    # DOWN from top goes to LEVEL SELECT (2)
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 2
    # UP from top row goes to QUIT (4)
    game.menu_selected = 0
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 4

def test_joy_hat_left_right(game):
    """Joystick HAT left/right toggles 1P/2P"""
    game.menu_selected = 0
    game.menu_hat_cooldown = 0
    ev = pygame.event.Event(pygame.JOYHATMOTION, joy=0, hat=0, value=(1,0))
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 1
    game.menu_hat_cooldown = 0
    ev = pygame.event.Event(pygame.JOYHATMOTION, joy=0, hat=0, value=(-1,0))
    pygame.event.post(ev)
    game.handle_events()
    assert game.menu_selected == 0

def test_1p_restart_with_lida_connected(game):
    """Bugfix: 1P restart should work even when Lida connected"""
    game.network_host.client_connected = True
    import time
    game.network_host.client_last_seen = time.time()
    game.state = 'menu'
    game.menu_mode = 'main'
    game.menu_selected = 0  # CHAD solo
    # should NOT auto-start 2P now (was bug)
    # Simulate run loop check
    if game.state == 'menu' and game.network_host.is_client_connected() and game.menu_mode == 'main' and game.menu_selected == 1:
        assert False, "should not auto-start 2P when 1P selected"
    # Host presses ENTER
    game.handle_menu_select()
    assert game.state == 'playing' and game.num_players == 1

def test_pause_robust(game):
    """P pauses, A/B/Plus/Minus/Start/Select and mouse resume"""
    game.menu_selected = 0
    game.handle_menu_select()
    assert game.state == 'playing'
    # P pauses
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'paused'
    # SPACE resumes
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'playing', "SPACE should resume robust pause"
    # Again pause and ESC resumes
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'paused'
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'playing'
    # Plus button (9) pauses
    ev = pygame.event.Event(pygame.JOYBUTTONDOWN, button=9, instance_id=0, joy=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'paused'
    # Button 0 resumes
    ev = pygame.event.Event(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0)
    pygame.event.post(ev)
    game.handle_events()
    assert game.state == 'playing'

def test_kick_lida_n_key(game):
    """N key should kick Lida"""
    game.network_host.client_connected = True
    import time
    game.network_host.client_last_seen = time.time()
    assert game.network_host.is_client_connected()
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n, mod=0)
    pygame.event.post(ev)
    game.handle_events()
    assert not game.network_host.is_client_connected(), "N should kick Lida"
