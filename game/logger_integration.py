"""
Patch to integrate debug_logger into entity modules without invasive rewrites
Provides mixin that logs key gameplay events
"""

# This file is imported as game.logger_integration - sets up global hooks
import sys

def safe_log_gameplay(event_type, level_idx=-1, player_id=None, data=None):
    try:
        from game.debug_logger import debug_logger
        if debug_logger._session_id is not None:
            debug_logger.log_gameplay(event_type, level_idx=level_idx, player_id=player_id, data=data)
    except Exception:
        pass

def safe_log_event(tag, message, level="INFO", extra=None, with_stack=False):
    try:
        from game.debug_logger import debug_logger
        debug_logger.log_event(tag, message, level=level, extra=extra, with_stack=with_stack)
    except Exception:
        pass

def safe_log_exception(where, exc, extra=None):
    try:
        from game.debug_logger import debug_logger
        debug_logger.log_exception(where, exc, extra=extra)
    except Exception:
        pass
