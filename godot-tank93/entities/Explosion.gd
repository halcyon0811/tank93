extends Node2D

# Authentic NES Explosion - blocky + screenshake + flash + juice
# Small: white 8 -> yellow plus 16 -> orange star 20 -> smoke
# Big: 12 -> 24 -> 32 + glow blend

@onready var particles: CPUParticles2D = $Particles
@onready var flash_rect: ColorRect = $Flash

var is_big: bool = false
var kind: String = "tank" # tank, armor, boss, base, monster

var lifetime: float = 0.4
var timer: float = 0.0
var frame_idx: int = 0
var ticks_per_frame: float = 0.07

func _ready():
	# Set particle color based on kind
	match kind:
		"base":
			particles.color = Color(1, 0.6, 0.2)
			particles.amount = 30
			lifetime = 0.8
			flash_rect.color = Color(1,1,1,0.8)
		"boss":
			particles.color = Color(0.8, 0.2, 0.2)
			particles.amount = 24
			lifetime = 0.6
		"armor":
			particles.color = Color(0.9, 0.5, 0.1)
			particles.amount = 18
		_:
			particles.color = Color(1, 0.8, 0.2)
			particles.amount = 14

	# Flash for first 2 frames like NES
	flash_rect.visible = true
	flash_rect.modulate.a = 1.0
	var tween = create_tween()
	tween.tween_property(flash_rect, "modulate:a", 0.0, 0.15)

	# Juice: scale pulse
	scale = Vector2(0.2, 0.2)
	var tween2 = create_tween()
	tween2.tween_property(self, "scale", Vector2(1.3 if is_big else 1.0, 1.3 if is_big else 1.0), 0.1).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween2.tween_property(self, "scale", Vector2.ONE, 0.2)

func _process(delta):
	timer += delta
	if timer >= lifetime:
		queue_free()

	if timer > ticks_per_frame * 2:
		flash_rect.visible = false
