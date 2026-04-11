"""
inventory_service.py — High-level inventory management service.

Orchestrates BigQuery and JSON data sources, provides clean APIs
for the Flask routes and agents.
"""
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from tools.inventory_tools import get_inventory_status, get_transfer_options
from tools.weather_tools import get_weather_forecast

STORES = {
    "ST001": {"name": "Metro Central",   "location": "London"},
    "ST002": {"name": "West End Express", "location": "Birmingham"},
    "ST003": {"name": "Northgate Fresh",  "location": "Manchester"},
    "ST004": {"name": "Riverside Local",  "location": "Leeds"},
    "ST005": {"name": "Parkview Large",   "location": "Bristol"},
}


def get_store_dashboard(store_id: str) -> dict:
    """
    Get a complete dashboard data package for a store.

    Returns inventory, weather, and risk summary in one call.
    """
    inv     = get_inventory_status(store_id)
    weather = get_weather_forecast(store_id)
    store   = STORES.get(store_id, {})

    # Risk breakdown
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in inv.get("inventory", []):
        risk = item.get("risk_level", "LOW")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    return {
        "store_id":        store_id,
        "store_name":      store.get("name", store_id),
        "location":        store.get("location", ""),
        "query_date":      date.today().isoformat(),
        "inventory":       inv,
        "weather":         weather,
        "risk_summary":    risk_counts,
        "total_at_risk_gbp": inv.get("total_potential_waste_gbp", 0),
    }


def get_all_stores_summary() -> list:
    """Get a quick summary of all stores for the network dashboard."""
    summaries = []
    for store_id, store_info in STORES.items():
        try:
            inv = get_inventory_status(store_id)
            weather = get_weather_forecast(store_id)
            critical = sum(1 for i in inv["inventory"] if i["risk_level"] == "CRITICAL")
            high     = sum(1 for i in inv["inventory"] if i["risk_level"] == "HIGH")
            summaries.append({
                "store_id":          store_id,
                "store_name":        store_info["name"],
                "location":          store_info["location"],
                "critical_items":    critical,
                "high_items":        high,
                "waste_risk_gbp":    inv.get("total_potential_waste_gbp", 0),
                "weather_condition": weather.get("forecast", [{}])[0].get("condition", "N/A"),
                "demand_impact":     weather.get("demand_impact", {}).get("overall", "NORMAL"),
            })
        except Exception as e:
            summaries.append({
                "store_id":   store_id,
                "store_name": store_info["name"],
                "error":      str(e),
            })
    return summaries


def get_store_list() -> dict:
    """Return the store directory with display names."""
    return {
        sid: f"{info['name']} ({info['location']})"
        for sid, info in STORES.items()
    }
