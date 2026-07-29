extends Node

# Save system - high score, best stage, unlocks
# For replay > story: high score, daily challenge, skins

var high_score: int = 0
var best_stage: int = 0
var total_stages_cleared: int = 0
var vehicle_choice: String = "tank" # tank or monster_truck
var unlocked_skins: Array = ["default"]
var coins: int = 0

const SAVE_PATH = "user://tank93_save.json"

func _ready():
	load_game()

func save_game():
	var data = {
		"high_score": high_score,
		"best_stage": best_stage,
		"total_stages_cleared": total_stages_cleared,
		"vehicle_choice": vehicle_choice,
		"unlocked_skins": unlocked_skins,
		"coins": coins,
	}
	var file = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(data))
		print("[Save] Saved to %s" % SAVE_PATH)

func load_game():
	if not FileAccess.file_exists(SAVE_PATH):
		print("[Save] No save file, fresh start")
		return
	var file = FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file:
		var txt = file.get_as_text()
		var json = JSON.new()
		if json.parse(txt) == OK:
			var data = json.data
			high_score = data.get("high_score", 0)
			best_stage = data.get("best_stage", 0)
			total_stages_cleared = data.get("total_stages_cleared", 0)
			vehicle_choice = data.get("vehicle_choice", "tank")
			unlocked_skins = data.get("unlocked_skins", ["default"])
			coins = data.get("coins", 0)
			print("[Save] Loaded high_score=%d best_stage=%d total=%d vehicle=%s" % [high_score, best_stage, total_stages_cleared, vehicle_choice])

func update_high_score(score: int, stage: int, total: int):
	var changed = false
	if score > high_score:
		high_score = score
		changed = true
	if stage > best_stage:
		best_stage = stage
		changed = true
	if total > total_stages_cleared:
		total_stages_cleared = total
		changed = true
	if changed:
		save_game()

func add_coins(amount: int):
	coins += amount
	save_game()
