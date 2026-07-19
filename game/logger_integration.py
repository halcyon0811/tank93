"""
Patch to integrate debug_logger into entity modules without invasive rewrites
Provides safe wrappers that never crash game

Enhanced for recent features observability:
- Network: broadcast fallback, No route, discovery flood, old client detection
- Steel: destructible concrete/steel harder than brick
- Edge: sliding through gap, auto-clamp, stuck detection
- Outside: spawn clamp, clamp outside
- Weapon: spread+homing stacking (both active), PWR index
- Map select: grid navigation, short names, no overlap
- HUD: explicit P/C buttons, HP renamed from ARMOR
- Startup: async network startup perf (was 5s blocking)
"""

import sys
import time

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

# --- Enhanced observability helpers for recent changes ---

def safe_log_network(event_type, data=None, player_id=None):
    """Network observability: broadcast fallback, discovery, old client, No route"""
    try:
        safe_log_gameplay(f"NETWORK_{event_type}", player_id=player_id, data=data)
        # Also log as NETWORK tag for easy filtering
        safe_log_event("NETWORK", f"{event_type}: {data}", level="INFO", extra=data)
    except:
        pass

def safe_log_steel(event_type, gx, gy, hits, needed, bullet_type, power, is_steel=True):
    """Steel/concrete destruction observability (new: destructible but harder)"""
    try:
        safe_log_gameplay(event_type, data={"x": gx, "y": gy, "hits": hits, "needed": needed, "type": bullet_type, "power": power, "is_steel": is_steel})
    except:
        pass

def safe_log_edge(event_type, data=None):
    """Edge stuck / sliding / clamp observability"""
    try:
        safe_log_gameplay(f"EDGE_{event_type}", data=data)
    except:
        pass

def safe_log_weapon(event_type, data=None, player_id=None):
    """Weapon stacking observability: spread+homing both, PWR index, etc."""
    try:
        safe_log_gameplay(f"WEAPON_{event_type}", player_id=player_id, data=data)
    except:
        pass

def safe_log_map(event_type, data=None):
    """Map select observability: grid navigation, short names"""
    try:
        safe_log_gameplay(f"MAP_{event_type}", data=data)
        safe_log_event("MAP", f"{event_type}: {data}", level="INFO", extra=data)
    except:
        pass

def safe_log_perf(metric, value_ms, extra=None):
    """Performance observability: startup time (was 5s blocking), network startup"""
    try:
        data = {"metric": metric, "value_ms": value_ms}
        if extra:
            data.update(extra)
        safe_log_gameplay(f"PERF_{metric.upper()}", data=data)
        safe_log_event("PERF", f"{metric}: {value_ms:.1f}ms", level="INFO", extra=data)
    except:
        pass

def safe_log_hud(event_type, data=None):
    """HUD observability: explicit P/C buttons, HP renamed, PWR index"""
    try:
        safe_log_gameplay(f"HUD_{event_type}", data=data)
    except:
        pass
