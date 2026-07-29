extends Node2D

# Tank93 Main Game Loop - Godot port of Python game.py + web-pure game.js
# Progressive difficulty: total_stages_cleared counter, same formulas as Python

@onready var tilemap_layer: TileMapLayer = $GameLayer/TileMap
@onready var bullet_layer: Node2D = $GameLayer/BulletLayer
@onready var explosion_layer: Node2D = $GameLayer/ExplosionLayer
@onready var camera: Camera2D = $Camera
@onready var stage_label: Label = $UI/HUD/StageLabel
@onready var debug_label: Label = $UI/DebugLabel

var level_data: Array = [] # 26x26 ints 0-5
var tiles: Array = [] # 2D
var brick_health: Dictionary = {}
var players: Array = []
var enemies: Array = []
var bullets: Array = []
var powerups: Array = []

var current_level: int = 0
var total_stages_cleared: int = 0
var current_loop: int = 0
var vehicle_choice: String = "tank" # always tank OG now, truck is item-only 3 min
var state: String = "menu"
var menu_selected: int = 0
var enemies_total: int = 20
var enemies_killed: int = 0
var enemies_spawned: int = 0
var spawn_timer: float = 0.0
var max_enemies_on_field: int = 4
var spawn_interval: float = 2.5
var difficulty_ramp_timer: float = 0.0
var high_score: int = 0

# Juice
var screenshake: float = 0.0
var screenshake_decay: float = 0.9
var flash_alpha: float = 0.0

func _ready():
	vehicle_choice = "tank" # always OG tank now, truck is item-only
	total_stages_cleared = Save.total_stages_cleared
	print("[Godot Tank93] Ready - OG Tank - total stages=%d - Truck is item-only 3 min + multi-weapons" % [total_stages_cleared])
	state = "menu"
	_init_level(0, 1)

func _unhandled_input(event):
	if state == "menu":
		if event.is_action_pressed("ui_up") or event.is_action_pressed("p1_up"):
			menu_selected = (menu_selected - 1 + 5) % 5
		elif event.is_action_pressed("ui_down") or event.is_action_pressed("p1_down"):
			menu_selected = (menu_selected + 1) % 5
		elif event.is_action_pressed("ui_left") or event.is_action_pressed("p1_left"):
			menu_selected = 1 if menu_selected == 0 else 0
		elif event.is_action_pressed("ui_right") or event.is_action_pressed("p1_right"):
			menu_selected = 1 if menu_selected == 0 else 0
		elif event.is_action_pressed("ui_accept") or event.is_action_pressed("p1_shoot"):
			_handle_menu_select()
	elif state == "playing":
		if event.is_action_pressed("pause"):
			state = "paused"
	elif state in ["gameover", "stage_clear", "paused"]:
		if event.is_action_pressed("ui_accept"):
			if state == "stage_clear":
				_next_level()
			else:
				state = "menu"

func _handle_menu_select():
	if menu_selected == 0:
		_init_level(0, 1)
		state = "playing"
	elif menu_selected == 1:
		_init_level(0, 2)
		state = "playing"
	elif menu_selected == 2:
		print("[Menu] Level select - not yet, starting 1P")
		_init_level(0, 1)
		state = "playing"
	elif menu_selected == 4:
		get_tree().quit()

func _init_level(idx: int, num_players: int):
	current_level = idx % 35
	var maps = Settings.maps_data.get("levels_26", [])
	if maps.size() > 0:
		level_data = maps[current_level]
	else:
		# fallback empty
		level_data = []
		for y in 26:
			var row = []
			for x in 26:
				row.append(0)
			level_data.append(row)

	enemies_total = Settings.get_enemy_total_for_level(current_level, total_stages_cleared)
	enemies_killed = 0
	enemies_spawned = 0
	spawn_timer = 0.0
	var diff = Settings.get_difficulty_params(total_stages_cleared)
	max_enemies_on_field = diff.max_on_field
	spawn_interval = diff.spawn_interval / 60.0 # convert frames to seconds (FPS 60)
	difficulty_ramp_timer = 0.0

	print("[Level] Stage %d/35 Total %d Loop %d Enemies %d Max %d Spawn %.2fs Vehicle %s" % [current_level+1, total_stages_cleared, diff.loop, enemies_total, max_enemies_on_field, spawn_interval, vehicle_choice])

	# Build tile visuals (simple colored rects for now, TileSet later)
	_draw_tilemap()

	# Spawn players with vehicle choice
	players.clear()
	for i in num_players:
		var spawn = Settings.PLAYER_SPAWN[i] if i < Settings.PLAYER_SPAWN.size() else Vector2i(8,24)
		var p = _create_player(spawn, i+1)
		players.append(p)
		add_child(p)

func _create_player(spawn: Vector2i, player_id: int) -> Node2D:
	var scene = preload("res://entities/Player.tscn")
	var p = scene.instantiate()
	p.position = Vector2(Settings.PLAYFIELD_X + spawn.x * Settings.TILE_SIZE + Settings.TILE_SIZE/2, Settings.PLAYFIELD_Y + spawn.y * Settings.TILE_SIZE + Settings.TILE_SIZE/2)
	p.player_id = player_id
	p.vehicle_choice = "tank" # always OG tank start, truck is item-only 3 min
	p.total_stages_cleared = total_stages_cleared
	# Ensure player starts as OG tank 1.0x, not truck (truck is item)
	return p

func _draw_tilemap():
	# For MVP: we will draw tiles as colored rects in TileMapLayer or via custom
	# For now use a simple Node2D drawing in _draw callback, will be replaced by TileSet later
	queue_redraw()

func _draw():
	if level_data.is_empty():
		return
	# Draw playfield border
	draw_rect(Rect2(Settings.PLAYFIELD_X - 4, Settings.PLAYFIELD_Y - 4, Settings.PLAYFIELD_W + 8, Settings.PLAYFIELD_H + 8), Color(0.27,0.27,0.35), false, 4.0)
	# Draw tiles
	for y in 26:
		for x in 26:
			if y >= level_data.size() or x >= level_data[y].size():
				continue
			var t = level_data[y][x]
			if t == 0:
				continue
			var rx = Settings.PLAYFIELD_X + x * Settings.TILE_SIZE
			var ry = Settings.PLAYFIELD_Y + y * Settings.TILE_SIZE
			var col = Color.WHITE
			if t == 1: col = Color(0.82, 0.22, 0.09) # brick
			elif t == 2: col = Color(0.82, 0.82, 0.82) # steel
			elif t == 3: col = Color(0.11, 0.35, 0.94) # water
			elif t == 4: col = Color(0.23, 0.62, 0.078) # grass
			elif t == 5: col = Color(0.74, 0.74, 0.74) # ice
			draw_rect(Rect2(rx, ry, Settings.TILE_SIZE, Settings.TILE_SIZE), col)

func _process(delta):
	match state:
		"menu":
			debug_label.text = "TANK 93 - OG Classic Tank - Press ENTER - Stage %d Total %d - Truck is item-only 3 min" % [current_level+1, total_stages_cleared]
		"playing":
			_update_playing(delta)
		"paused":
			debug_label.text = "PAUSED - P to resume"
		"gameover":
			debug_label.text = "GAME OVER - ENTER for menu - Score %d - High %d" % [players[0].score if players.size()>0 else 0, Save.high_score]
		"stage_clear":
			debug_label.text = "STAGE CLEAR! ENTER for next - Total %d Loop %d" % [total_stages_cleared, current_loop]

	# Screenshake
	if screenshake > 0.1:
		camera.offset = Vector2(randf_range(-screenshake, screenshake), randf_range(-screenshake, screenshake))
		screenshake *= screenshake_decay
	else:
		camera.offset = Vector2.ZERO

	# Flash
	if flash_alpha > 0:
		queue_redraw() # to draw flash overlay
		flash_alpha -= delta * 4.0

func _update_playing(delta):
	spawn_timer += delta
	difficulty_ramp_timer += delta

	if difficulty_ramp_timer >= 12.0:
		difficulty_ramp_timer = 0.0
		if max_enemies_on_field < Settings.DIFFICULTY_MAX_ENEMIES_CAP:
			max_enemies_on_field += 1
			print("[Difficulty] Ramp max %d" % max_enemies_on_field)
		spawn_interval = max(Settings.DIFFICULTY_SPAWN_MIN / 60.0, spawn_interval - 0.13)

	if spawn_timer >= spawn_interval:
		spawn_timer = 0.0
		_spawn_enemy()

	if enemies_killed >= enemies_total and enemies.size() == 0:
		state = "stage_clear"
		total_stages_cleared += 1
		current_loop = int(total_stages_cleared / 35)
		GameData.total_stages_cleared = total_stages_cleared
		GameData.current_loop = current_loop
		Save.total_stages_cleared = total_stages_cleared
		Save.best_stage = max(Save.best_stage, current_level+1)
		if players.size()>0:
			Save.high_score = max(Save.high_score, players[0].score)
		Save.save_game()
		print("[Stage Clear] Total %d Loop %d" % [total_stages_cleared, current_loop])

	var diff = Settings.get_difficulty_params(total_stages_cleared)
	var truck_info = ""
	if players.size() > 0 and players[0].is_monster_truck:
		truck_info = " TRUCK %ds" % int(players[0].monster_truck_timer)
	stage_label.text = "STAGE %d/35 TOTAL %d LOOP %d MAX %d SPAWN %.1fs x%.2f%s" % [current_level+1, total_stages_cleared, diff.loop, diff.max_on_field, diff.spawn_interval/60.0, diff.speed_mult, truck_info]

func _spawn_enemy():
	if enemies_spawned >= enemies_total:
		return
	if enemies.size() >= max_enemies_on_field:
		return
	var spawn = Settings.ENEMY_SPAWNS.pick_random()
	var scene = preload("res://entities/Enemy.tscn")
	var e = scene.instantiate()
	e.position = Vector2(Settings.PLAYFIELD_X + spawn.x * Settings.TILE_SIZE + Settings.TILE_SIZE/2, Settings.PLAYFIELD_Y + spawn.y * Settings.TILE_SIZE + Settings.TILE_SIZE/2)
	# Apply loop speed/shoot mult
	var diff = Settings.get_difficulty_params(total_stages_cleared)
	e.speed_mult = diff.speed_mult
	add_child(e)
	enemies.append(e)
	enemies_spawned += 1
	# Juice: spawn particles
	_spawn_explosion(e.position, false, "spawn")

func _next_level():
	current_level = (current_level + 1) % 35
	# Clear old players
	for p in players:
		p.queue_free()
	players.clear()
	for e in enemies:
		e.queue_free()
	enemies.clear()
	_init_level(current_level, 1)
	state = "playing"

func _spawn_explosion(pos: Vector2, big: bool, kind: String):
	# Authentic NES explosion with juice
	var exp_scene = preload("res://entities/Explosion.tscn")
	var exp = exp_scene.instantiate()
	exp.position = pos
	exp.is_big = big
	exp.kind = kind
	explosion_layer.add_child(exp)

	# Juice: screenshake + flash + sound
	match kind:
		"base":
			screenshake = 14
			flash_alpha = 1.0
		"boss":
			screenshake = 10
			flash_alpha = 0.6
		"armor":
			screenshake = 6
			flash_alpha = 0.3
		_:
			screenshake = 3
			flash_alpha = 0.15

	# Hitstop for boss/base
	if kind in ["boss","base"]:
		Engine.time_scale = 0.1
		await get_tree().create_timer(0.05).timeout
		Engine.time_scale = 1.0
