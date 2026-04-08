"""
Test suite for all tools and core logic — runs without any API keys.
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DEMO_MODE"] = "true"

import pytest


# ─── Inventory Tools ──────────────────────────────────────────────────────────

def test_get_inventory_status_returns_data():
    from tools.inventory_tools import get_inventory_status
    result = get_inventory_status("ST001")
    assert result["store_id"] == "ST001"
    assert result["total_skus_checked"] > 0
    assert isinstance(result["inventory"], list)
    assert result["total_potential_waste_gbp"] >= 0


def test_get_inventory_status_has_risk_levels():
    from tools.inventory_tools import get_inventory_status
    result = get_inventory_status("ST001")
    for item in result["inventory"]:
        assert item["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert item["days_to_expiry"] >= 0
        assert item["projected_unsold_units"] >= 0
        assert 0 <= item["waste_risk_pct"] <= 100


def test_get_inventory_status_category_filter():
    from tools.inventory_tools import get_inventory_status
    result = get_inventory_status("ST001", category="Dairy")
    for item in result["inventory"]:
        assert item["category"] == "Dairy"


def test_get_inventory_status_unknown_store():
    from tools.inventory_tools import get_inventory_status
    result = get_inventory_status("ST999")
    assert result["total_skus_checked"] == 0


def test_get_transfer_options():
    from tools.inventory_tools import get_transfer_options
    result = get_transfer_options("SKU-0001", "ST001")
    assert result["sku_id"] == "SKU-0001"
    assert isinstance(result["transfer_options"], list)


def test_log_decision_creates_file():
    from tools.inventory_tools import log_decision_to_store
    log_path = Path(__file__).parent.parent / "data" / "decisions_log.json"
    # Remove if exists
    if log_path.exists():
        log_path.unlink()

    result = log_decision_to_store(
        sku_id="SKU-0001",
        store_id="ST001",
        action_type="DISCOUNT",
        action_detail="Apply 20% discount",
        units_affected=120,
        expected_saving_gbp=24.50,
        reasoning="Test reasoning",
    )
    assert result["status"] == "SUCCESS"
    assert log_path.exists()
    assert "decision_id" in result["decision"]
    assert result["decision"]["action_type"] == "DISCOUNT"


# ─── Weather Tools ────────────────────────────────────────────────────────────

def test_get_weather_forecast_structure():
    from tools.weather_tools import get_weather_forecast
    result = get_weather_forecast("ST001")
    assert "forecast" in result
    assert "demand_impact" in result
    assert len(result["forecast"]) > 0


def test_get_weather_forecast_all_stores():
    from tools.weather_tools import get_weather_forecast
    for store_id in ["ST001", "ST002", "ST003", "ST004", "ST005"]:
        result = get_weather_forecast(store_id)
        assert result["store_id"] == store_id
        assert "city" in result


def test_get_weather_forecast_unknown_store():
    from tools.weather_tools import get_weather_forecast
    result = get_weather_forecast("ST999")
    assert "error" in result


def test_weather_heatwave_detection():
    from tools.weather_tools import get_weather_forecast
    # ST001 (London) has heatwave in mock data
    result = get_weather_forecast("ST001")
    assert result["demand_impact"]["heatwave"] is True
    assert result["demand_impact"]["overall"] == "HIGH_RISK"


# ─── Pricing Tools ────────────────────────────────────────────────────────────

def test_simulate_discount_action_viability():
    from tools.pricing_tools import simulate_discount_action
    result = simulate_discount_action("SKU-0001", "ST001", 20, 2)
    assert "gross_margin_pct" in result
    assert "waste_reduction_gbp" in result
    assert isinstance(result["viable"], bool)
    assert result["discount_pct"] == 20


def test_simulate_discount_higher_discount_saves_more():
    from tools.pricing_tools import simulate_discount_action
    r10 = simulate_discount_action("SKU-0001", "ST001", 10, 2)
    r30 = simulate_discount_action("SKU-0001", "ST001", 30, 2)
    # Higher discount should sell more units (less waste)
    assert r30["projected_units_sold"] >= r10["projected_units_sold"]


def test_simulate_discount_margin_decreases_with_higher_discount():
    from tools.pricing_tools import simulate_discount_action
    r10 = simulate_discount_action("SKU-0001", "ST001", 10, 2)
    r30 = simulate_discount_action("SKU-0001", "ST001", 30, 2)
    assert r30["gross_margin_pct"] <= r10["gross_margin_pct"]


def test_simulate_transfer_action():
    from tools.pricing_tools import simulate_transfer_action
    result = simulate_transfer_action("SKU-0001", "ST001", "ST002", 20)
    assert result["units_transferred"] == 20
    assert "net_saving_gbp" in result
    assert "kg_food_saved" in result
    assert "co2_avoided_kg" in result


def test_simulate_loyalty_coupon():
    from tools.pricing_tools import simulate_loyalty_coupon
    result = simulate_loyalty_coupon("SKU-0001", "ST001", 15, 500)
    assert 0 < result["expected_redemptions"] <= 500
    assert result["units_moved"] > 0
    assert "net_benefit_gbp" in result


def test_calculate_esg_metrics():
    from tools.pricing_tools import calculate_esg_metrics
    decisions = [
        {"expected_saving_gbp": 50.0, "units_affected": 100},
        {"expected_saving_gbp": 30.0, "units_affected": 60},
    ]
    result = calculate_esg_metrics(decisions)
    assert result["total_decisions"] == 2
    assert result["total_waste_value_prevented_gbp"] == 80.0
    assert result["kg_food_saved"] > 0
    assert result["co2_avoided_kg"] > 0
    assert result["meals_equivalent"] > 0


# ─── Integration: full analysis mock ─────────────────────────────────────────

def test_full_analysis_pipeline():
    """Simulates the full agent pipeline using tools directly."""
    from tools.inventory_tools import get_inventory_status, get_transfer_options, log_decision_to_store
    from tools.weather_tools import get_weather_forecast
    from tools.pricing_tools import simulate_discount_action, simulate_transfer_action, calculate_esg_metrics

    store_id = "ST001"

    # Step 1: Forecasting
    inv = get_inventory_status(store_id)
    weather = get_weather_forecast(store_id)

    assert inv["total_skus_checked"] > 0
    assert len(weather["forecast"]) > 0

    # Step 2: Decision — find critical items and simulate
    critical = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]
    assert len(critical) > 0

    item = critical[0]
    discount = simulate_discount_action(item["sku_id"], store_id, 20, item["days_to_expiry"])
    assert discount["gross_margin_pct"] is not None

    # Step 3: Execution — log decision
    log = log_decision_to_store(
        sku_id=item["sku_id"],
        store_id=store_id,
        action_type="DISCOUNT",
        action_detail="Integration test decision",
        units_affected=item["stock_qty"],
        expected_saving_gbp=discount["waste_reduction_gbp"],
        reasoning="Integration test: automated pipeline verification",
    )
    assert log["status"] == "SUCCESS"

    print(f"\n✅ Integration test passed: {item['name']} → {log['decision']['action_type']} (ID: {log['decision']['decision_id']})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
