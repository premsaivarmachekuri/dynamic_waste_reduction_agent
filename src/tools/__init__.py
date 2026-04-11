"""
__init__.py for tools package — lazy imports to avoid ADK dependency at module load
"""

def get_inventory_status(*args, **kwargs):
    from tools.inventory_tools import get_inventory_status as _fn
    return _fn(*args, **kwargs)

def get_transfer_options(*args, **kwargs):
    from tools.inventory_tools import get_transfer_options as _fn
    return _fn(*args, **kwargs)

def log_decision_to_store(*args, **kwargs):
    from tools.inventory_tools import log_decision_to_store as _fn
    return _fn(*args, **kwargs)

def get_weather_forecast(*args, **kwargs):
    from tools.weather_tools import get_weather_forecast as _fn
    return _fn(*args, **kwargs)

def simulate_discount_action(*args, **kwargs):
    from tools.pricing_tools import simulate_discount_action as _fn
    return _fn(*args, **kwargs)

def simulate_transfer_action(*args, **kwargs):
    from tools.pricing_tools import simulate_transfer_action as _fn
    return _fn(*args, **kwargs)

def simulate_loyalty_coupon(*args, **kwargs):
    from tools.pricing_tools import simulate_loyalty_coupon as _fn
    return _fn(*args, **kwargs)

def calculate_esg_metrics(*args, **kwargs):
    from tools.pricing_tools import calculate_esg_metrics as _fn
    return _fn(*args, **kwargs)

__all__ = [
    "get_inventory_status",
    "get_transfer_options",
    "log_decision_to_store",
    "get_weather_forecast",
    "simulate_discount_action",
    "simulate_transfer_action",
    "simulate_loyalty_coupon",
    "calculate_esg_metrics",
]
