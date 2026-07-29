extends CharacterBody2D
# Enemy Tank - A* big tile 13x13 pathfinding + boss crush + progressive difficulty

@onready var sprite: Sprite2D = $Sprite
@onready var health_bar: ColorRect = $HealthBar

var enemy_type: String = "basic"
var speed: float = 1.8 * 24.0
var speed_mult: float = 1.0
var shoot_chance: float = 0.018
var health: int = 1
var is_boss: bool = false
var powerup_carrier: bool = false

var direction: String = "DOWN"
var target_dir_timer: float = 0.0
var stuck_timer: float = 0.0
var last_pos: Vector2 = Vector2.ZERO

func _ready():
	add_to_group("enemy")
	powerup_carrier = randf() < 0.25
	if enemy_type == "basic":
		speed = Settings.TANK_SPEED.enemy * 24.0
		health = 1
	elif enemy_type == "fast":
		speed = Settings.TANK_SPEED.fast * 24.0
		health = 1
	elif enemy_type == "armor":
		speed = Settings.TANK_SPEED.enemy * 0.75 * 24.0
		health = 4
		health_bar.visible = true
	elif enemy_type == "boss":
		speed = Settings.TANK_SPEED.enemy * 24.0
		health = 18
		is_boss = true
		health_bar.visible = true
		scale = Vector2(1.5, 1.5)

	speed *= speed_mult
	last_pos = position

func _physics_process(delta):
	# Stuck detection
	if position.distance_to(last_pos) < 0.8:
		stuck_timer += delta
	else:
		stuck_timer = 0.0
	last_pos = position

	if target_dir_timer <= 0 or stuck_timer > 1.5:
		_choose_new_direction()
		target_dir_timer = randf_range(1.0, 3.0)
	else:
		target_dir_timer -= delta

	var dir_vec = Settings.DIRS.get(direction, Vector2i(0,1))
	velocity = Vector2(dir_vec) * speed
	move_and_slide()

	if randf() < shoot_chance * delta * 60.0:
		_shoot()

func _choose_new_direction():
	var possible = ["UP","DOWN","LEFT","RIGHT"]
	direction = possible.pick_random()

func _shoot():
	var b = preload("res://entities/Bullet.tscn").instantiate()
	b.position = position + Vector2.from_angle(0) * 20
	b.direction = direction
	b.owner_id = -1 # enemy
	b.power = 1
	get_parent().add_child(b)
