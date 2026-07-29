extends Area2D
# Bullet - homing 3.564 turn 0.068 fuel 574, flamethrower, power

@onready var sprite: ColorRect = $Sprite

var direction: String = "UP"
var bullet_type: String = "normal" # normal, power, homing, flamethrower, etc
var owner_id: int = 1
var power: int = 1
var speed: float = 8.25 * 24.0
var velocity: Vector2 = Vector2.ZERO
var travel: float = 0.0
var max_distance: float = 1000.0
var is_homing: bool = false
var turn_speed: float = 0.068
var life: float = 2.0

func _ready():
	speed = Settings.BULLET_SPEED * 24.0
	if bullet_type == "flamethrower":
		speed *= 1.5
		# Orange flame
		sprite.color = Color(1, 0.6, 0.1)
		scale = Vector2(1.5, 1.5)
		life = 0.5
	elif bullet_type == "power":
		sprite.color = Color(1, 1, 0.3)
		speed *= 1.3
	elif bullet_type == "homing":
		is_homing = true
		speed = Settings.HOMING_SPEED * 24.0
		turn_speed = Settings.HOMING_TURN_SPEED
		sprite.color = Color(1, 0.55, 0)
		max_distance = Settings.HOMING_MAX_DISTANCE

	var dir_vec = Settings.DIRS.get(direction, Vector2i(0,-1))
	velocity = Vector2(dir_vec) * speed

func _physics_process(delta):
	if bullet_type == "flamethrower":
		life -= delta
		if life <= 0:
			queue_free()
			return
		position += velocity * delta
		# Melt bricks
		# TODO: call Main to destroy tile at position
		travel += speed * delta
		if travel >= max_distance:
			queue_free()
			return
	elif is_homing:
		# Find nearest enemy/player
		var targets = get_tree().get_nodes_in_group("enemy" if owner_id > 0 else "player")
		if targets.size() > 0:
			var nearest = null
			var min_dist = INF
			for t in targets:
				if not is_instance_valid(t):
					continue
				var d = position.distance_to(t.position)
				# Boss priority 0.5*dist
				if t.get("is_boss"):
					d *= 0.5
				if d < min_dist:
					min_dist = d
					nearest = t
			if nearest:
				var desired = (nearest.position - position).normalized()
				velocity = velocity.lerp(desired * speed, turn_speed)
		position += velocity * delta
		travel += speed * delta
		if travel >= max_distance:
			# Out of fuel explosion
			var main = get_parent()
			if main and main.has_method("_spawn_explosion"):
				main._spawn_explosion(position, false, "homing")
			queue_free()
			return
	else:
		position += velocity * delta

	# Bounds check
	if position.x < Settings.PLAYFIELD_X or position.x > Settings.PLAYFIELD_X + Settings.PLAYFIELD_W or position.y < Settings.PLAYFIELD_Y or position.y > Settings.PLAYFIELD_Y + Settings.PLAYFIELD_H:
		queue_free()

func _on_body_entered(body):
	if body.is_in_group("enemy") and owner_id > 0:
		if body.has_method("take_damage"):
			body.take_damage(power)
		# Explosion
		var main = get_parent()
		if main and main.has_method("_spawn_explosion"):
			main._spawn_explosion(position, false, "tank")
		queue_free()
	elif body.is_in_group("player") and owner_id < 0:
		if body.has_method("take_damage"):
			body.take_damage(power)
		queue_free()
