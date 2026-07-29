extends Node

# Tank93 Settings - generated from Python game/settings.py via scripts/generate_web_assets.py
# Source of truth: game/settings.py 86 keys
# This autoload mirrors Python constants for Godot port

var SCREEN_WIDTH: int = 960
var SCREEN_HEIGHT: int = 720
var FPS: int = 60

var TILE_SIZE: int = 24
var GRID_W: int = 26
var GRID_H: int = 26
var PLAYFIELD_W: int = 624
var PLAYFIELD_H: int = 624
var PLAYFIELD_X: int = 48
var PLAYFIELD_Y: int = 48
var BASE_POS: Vector2i = Vector2i(12, 24)
var PLAYER_SPAWN: Array = [Vector2i(8,24), Vector2i(16,24)]
var ENEMY_SPAWNS: Array = [Vector2i(0,0), Vector2i(12,0), Vector2i(24,0)]
var TANK_SIZE: int = 32

var TANK_SPEED: Dictionary = {"player": 3.3, "enemy": 1.8, "fast": 3.0}
var BULLET_SPEED: float = 8.25
var BULLET_SIZE: int = 6

var ARMOR_INITIAL_PLAYER: int = 100
var ARMOR_INITIAL_ENEMY: Dictionary = {"basic":50,"fast":40,"power":80,"armor":150,"boss":300,"monster_boss":400,"monster":300}
var ARMOR_MAX_PLAYER: int = 300

var BRICK_HITS_NEEDED: Dictionary = {"normal":2,"power":1,"rapid":3,"homing":4,"spread":2,"venom":2,"power_homing":1}
var STEEL_HITS_NEEDED: Dictionary = {"normal":5,"power":3,"rapid":8,"homing":6,"spread":5,"venom":4,"power_homing":3}

var ENEMIES_PER_LEVEL: int = 20
var MAX_ENEMIES_ON_FIELD: int = 4
var ENEMY_SPAWN_INTERVAL: float = 150.0

var POWERUP_TYPES: Array = ["helmet","clock","shovel","star","grenade","tank","gun","homing","spread","rapid","shrink","giant","monster_truck"]

var HOMING_SPEED: float = 3.564
var HOMING_MAX_DISTANCE: float = 574.08
var HOMING_TURN_SPEED: float = 0.068

var VENOM_DISSOLVE_TIME: int = 1080
var VENOM_SPEED: float = 3.7125

var DIFFICULTY_MAX_ENEMIES_BASE: int = 4
var DIFFICULTY_MAX_ENEMIES_PER_STAGE: float = 0.5
var DIFFICULTY_MAX_ENEMIES_CAP: int = 12
var DIFFICULTY_SPAWN_BASE: float = 150.0
var DIFFICULTY_SPAWN_PER_STAGE: float = 4.8
var DIFFICULTY_SPAWN_MIN: float = 24.0
var DIFFICULTY_ENEMY_TOTAL_PER_STAGE: int = 2
var DIFFICULTY_ENEMY_TOTAL_PER_LOOP: int = 5
var DIFFICULTY_SPEED_PER_LOOP: float = 0.12
var DIFFICULTY_SHOOT_PER_LOOP: float = 0.15

var TILE_EMPTY: int = 0
var TILE_BRICK: int = 1
var TILE_STEEL: int = 2
var TILE_WATER: int = 3
var TILE_GRASS: int = 4
var TILE_ICE: int = 5

var DIRS: Dictionary = {
	"UP": Vector2i(0,-1),
	"DOWN": Vector2i(0,1),
	"LEFT": Vector2i(-1,0),
	"RIGHT": Vector2i(1,0),
	"UP_LEFT": Vector2i(-1,-1),
	"UP_RIGHT": Vector2i(1,-1),
	"DOWN_LEFT": Vector2i(-1,1),
	"DOWN_RIGHT": Vector2i(1,1),
}

var EIGHT_DIRS: Array = ["UP","UP_RIGHT","RIGHT","DOWN_RIGHT","DOWN","DOWN_LEFT","LEFT","UP_LEFT"]

var MONSTER_TRUCK_SCALE: float = 2.0
var MONSTER_TRUCK_DURATION: int = 900
var GIANT_SCALE: float = 2.0

var PLAYER_NAMES: Array = ["Chad","Lida"]

var maps_data: Dictionary = {}
var settings_data: Dictionary = {}

func _ready():
	_load_assets()

func _load_assets():
	# Load maps.json and settings.json - same pipeline as web-pure generate_web_assets.py
	var maps_file = FileAccess.open("res://assets/maps.json", FileAccess.READ)
	if maps_file:
		var txt = maps_file.get_as_text()
		var json = JSON.new()
		if json.parse(txt) == OK:
			maps_data = json.data
			print("[Godot] Loaded maps.json stages=%d" % maps_data.get("levels_26", []).size())
	else:
		print("[Godot] Failed to load maps.json")

	var settings_file = FileAccess.open("res://assets/settings.json", FileAccess.READ)
	if settings_file:
		var txt = settings_file.get_as_text()
		var json = JSON.new()
		if json.parse(txt) == OK:
			settings_data = json.data
			# Apply overrides
			if settings_data.has("TILE_SIZE"): TILE_SIZE = settings_data["TILE_SIZE"]
			if settings_data.has("BULLET_SPEED"): BULLET_SPEED = settings_data["BULLET_SPEED"]
			if settings_data.has("HOMING_SPEED"): HOMING_SPEED = settings_data["HOMING_SPEED"]
			print("[Godot] Loaded settings.json %d keys" % settings_data.size())

func get_difficulty_params(total_cleared: int) -> Dictionary:
	var loop = int(total_cleared / 35)
	var max_on_field = mini(DIFFICULTY_MAX_ENEMIES_CAP, DIFFICULTY_MAX_ENEMIES_BASE + int(total_cleared * DIFFICULTY_MAX_ENEMIES_PER_STAGE))
	var spawn_interval = maxf(DIFFICULTY_SPAWN_MIN, DIFFICULTY_SPAWN_BASE - total_cleared * DIFFICULTY_SPAWN_PER_STAGE)
	var speed_mult = 1.0 + loop * DIFFICULTY_SPEED_PER_LOOP
	var shoot_mult = 1.0 + loop * DIFFICULTY_SHOOT_PER_LOOP
	return {
		"total": total_cleared,
		"loop": loop,
		"max_on_field": max_on_field,
		"spawn_interval": spawn_interval,
		"speed_mult": speed_mult,
		"shoot_mult": shoot_mult,
	}

func get_enemy_total_for_level(lvl: int, total_cleared: int) -> int:
	var loop = int(total_cleared / 35)
	var base = 20
	if maps_data.has("enemy_queues") and maps_data["enemy_queues"].size() > lvl:
		base = maps_data["enemy_queues"][lvl].size()
	var extra = total_cleared * DIFFICULTY_ENEMY_TOTAL_PER_STAGE + loop * DIFFICULTY_ENEMY_TOTAL_PER_LOOP + lvl*2 + int(lvl/5)*3
	return base + extra
