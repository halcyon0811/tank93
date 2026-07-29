extends Node

# Global game state - shared between scenes

var current_level: int = 0
var total_stages_cleared: int = 0
var current_loop: int = 0
var vehicle_choice: String = "tank" # tank 1.0x or monster_truck 1.3x + flame
var num_players: int = 1
var players_score: Array = [0,0]
var players_lives: Array = [3,3]

func reset_for_new_game():
	current_level = 0
	total_stages_cleared = 0
	current_loop = 0
	players_score = [0,0]
	players_lives = [3,3]
	# vehicle_choice persists from Save

func next_stage():
	total_stages_cleared += 1
	current_loop = int(total_stages_cleared / 35)
	current_level = (current_level + 1) % 35
	print("[GameData] Stage cleared! Total=%d Loop=%d Next=%d" % [total_stages_cleared, current_loop, current_level])

func get_difficulty() -> Dictionary:
	return Settings.get_difficulty_params(total_stages_cleared)
