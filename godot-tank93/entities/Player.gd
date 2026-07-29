extends CharacterBody2D
# Player Tank - OG Classic with vehicle choice: tank 1.0x or monster_truck 1.3x + flamethrower
# Port of Python game/entities/tank.py + player.py

@onready var sprite: Sprite2D = $Sprite
@onready var cannon: Node2D = $Cannon
@onready var flame_particles: CPUParticles2D = $FlameParticles
@onready var name_label: Label = $NameLabel
@onready var armor_bar: ColorRect = $ArmorBar

var player_id: int = 1
var vehicle_choice: String = "tank" # tank or monster_truck
var total_stages_cleared: int = 0

var health: int = 1
var armor: float = 100.0
var max_armor: float = 100.0
var lives: int = 3
var score: int = 0
var star_level: int = 0
var bullet_power: int = 1

var speed: float = 3.3 * 24.0 # convert from Python TILE_SIZE per frame to pixels/sec
var base_speed: float = 3.3 * 24.0
var direction: String = "UP"

# Timers
var invuln_timer: float = 2.0
var helmet_timer: float = 0.0
var giant_timer: float = 0.0
var shrink_timer: float = 0.0
var monster_truck_timer: float = 0.0
var is_giant: bool = false
var is_shrunk: bool = false
var is_monster_truck: bool = false

# Items PERM until death like Python
var homing_active: bool = false
var spread_active: bool = false
var rapid_active: bool = false
var flamethrower_active: bool = false
var flamethrower_level: int = 0

var current_scale: float = 1.0
var can_shoot_timer: float = 0.0

func _ready():
	add_to_group("player")
	name_label.text = "Chad" if player_id == 1 else "Lida"
	armor = Settings.ARMOR_INITIAL_PLAYER
	max_armor = armor
	_apply_vehicle_choice()

func _apply_vehicle_choice():
	if vehicle_choice == "monster_truck":
		is_monster_truck = true
		monster_truck_timer = 99999.0 # permanent until death, player chose it
		current_scale = 1.3
		scale = Vector2(current_scale, current_scale)
		flamethrower_active = true
		flamethrower_level = 1
		speed = base_speed * 1.2
		print("[Player] Monster Truck 1.3x + Flamethrower chosen P%d" % player_id)
	else:
		current_scale = 1.0
		scale = Vector2.ONE
		flamethrower_active = false

func _physics_process(delta):
	# Timers
	if invuln_timer > 0:
		invuln_timer -= delta
		modulate.a = 0.5 + 0.5 * sin(Time.get_ticks_msec() * 0.02) if invuln_timer > 0 else 1.0
	else:
		modulate.a = 1.0

	if can_shoot_timer > 0:
		can_shoot_timer -= delta

	if monster_truck_timer > 0 and vehicle_choice != "monster_truck":
		# monster truck item timer (temporary 2x)
		monster_truck_timer -= delta
		if monster_truck_timer <= 0:
			is_monster_truck = false
			current_scale = 1.3 if vehicle_choice == "monster_truck" else 1.0
			scale = Vector2(current_scale, current_scale)

	# Input - 8 directions + shoot
	var input_dir = Vector2.ZERO
	if player_id == 1:
		input_dir.x = Input.get_action_strength("p1_right") - Input.get_action_strength("p1_left")
		input_dir.y = Input.get_action_strength("p1_down") - Input.get_action_strength("p1_up")
		if Input.is_action_just_pressed("p1_shoot") and can_shoot_timer <= 0:
			_shoot()
	else:
		input_dir.x = Input.get_action_strength("p2_right") - Input.get_action_strength("p2_left")
		input_dir.y = Input.get_action_strength("p2_down") - Input.get_action_strength("p2_up")
		if Input.is_action_just_pressed("p2_shoot") and can_shoot_timer <= 0:
			_shoot()

	# Direction for cannon
	if input_dir != Vector2.ZERO:
		var ang = atan2(input_dir.y, input_dir.x)
		var deg = rad_to_deg(ang)
		# Map to 8 dirs
		if deg >= -22.5 and deg < 22.5:
			direction = "RIGHT"
		elif deg >= 22.5 and deg < 67.5:
			direction = "DOWN_RIGHT"
		elif deg >= 67.5 and deg < 112.5:
			direction = "DOWN"
		elif deg >= 112.5 and deg < 157.5:
			direction = "DOWN_LEFT"
		elif deg >= 157.5 or deg < -157.5:
			direction = "LEFT"
		elif deg >= -157.5 and deg < -112.5:
			direction = "UP_LEFT"
		elif deg >= -112.5 and deg < -67.5:
			direction = "UP"
		else:
			direction = "UP_RIGHT"
		cannon.rotation = ang + PI/2

		velocity = input_dir.normalized() * speed
		move_and_slide()

		# Crush logic if monster truck - 2x bigger crushes all
		if is_monster_truck or vehicle_choice == "monster_truck":
			_crush_tiles()

func _crush_tiles():
	# Monster truck crushes bricks, steel, forest
	var tile_pos = get_parent().get_node_or_null("TileMap")
	# For MVP, we will just emit signal to Main to crush
	# Main handles tile destruction
	pass

func _shoot():
	if flamethrower_active:
		# Flamethrower cone
		for i in 7:
			var b = preload("res://entities/Bullet.tscn").instantiate()
			b.position = position + Vector2.from_angle(cannon.rotation - PI/2) * 20
			b.direction = direction
			b.bullet_type = "flamethrower"
			b.owner_id = player_id
			b.power = 2
			# Cone spread
			b.velocity = Vector2.from_angle(cannon.rotation - PI/2 + randf_range(-0.35, 0.35)) * (Settings.BULLET_SPEED * 1.5 * 24.0)
			get_parent().add_child(b)
		can_shoot_timer = 0.08 # rapid
		flame_particles.emitting = true
		# Screenshake tiny
		get_parent().get_parent().screenshake = 1.0
	else:
		var b = preload("res://entities/Bullet.tscn").instantiate()
		b.position = position + Vector2.from_angle(cannon.rotation - PI/2) * 20
		b.direction = direction
		b.owner_id = player_id
		b.power = bullet_power
		get_parent().add_child(b)
		can_shoot_timer = 0.2 if star_level == 0 else 0.12

func take_damage(power: int) -> bool:
	if invuln_timer > 0:
		return false
	if armor > 0:
		armor -= power * 25
		if armor > 0:
			return false
	armor = 0
	health -= power
	if health <= 0:
		die()
		return true
	return false

func die():
	visible = false
	# Explosion
	var main = get_parent()
	if main and main.has_method("_spawn_explosion"):
		main._spawn_explosion(position, true, "player")
	lives -= 1
	if lives < 0:
		print("[Player] P%d Game Over" % player_id)
	else:
		await get_tree().create_timer(1.0).timeout
		# respawn
		visible = true
		invuln_timer = 3.0
		health = 1
		armor = Settings.ARMOR_INITIAL_PLAYER
