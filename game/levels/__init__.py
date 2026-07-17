"""Level package - contains authentic 35 NES maps."""
from .battle_city import LEVELS_13, LEVELS_26, ENEMY_QUEUES, BOTS_RAW, STAGE_COUNT

# Primary exports
# LEVELS_26 = 35 x 26x26 precise (half-brick support)
# LEVELS_13 = 35 x 13x13 simplified
# ENEMY_QUEUES = 35 x list[20] of enemy types in spawn order
# BOTS_RAW = 35 x list[str] like ["18*basic","2*fast"]
__all__ = ["LEVELS_13", "LEVELS_26", "ENEMY_QUEUES", "BOTS_RAW", "STAGE_COUNT"]
