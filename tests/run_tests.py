"""
Standalone test runner — NO pytest, NO ADK imports.
Tests every tool function directly and prints a clear pass/fail report.

Run with:  python tests/run_tests.py
"""
import sys
import os
import json
import traceback
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(ROOT))
os.environ["DEMO_MODE"] = "true"

# ─── Test harness ─────────────────────────────────────────────────────────────
PASS = "\033[92m  ✅ PASS\033[0m"
FAIL = "\033[91m  ❌ FAIL\033[0m"
HEAD = "\033[96m{}\033[0m"

results = []

def test(name, fn):
    try:
        fn()
        print(f"{PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"{FAIL}  {name}")
        print(f"        {e}")
        results.append((name, False, str(e)))


# ─── Import tools directly (no ADK) ──────────────────────────────────────────
from tools.inventory_tools import get_inventory_status, get_transfer_options, log_decision_to_store
from tools.weather_tools import get_weather_forecast
from tools.pricing_tools import (
    simulate_discount_action,
    simulate_transfer_action,
    simulate_loyalty_coupon,
    calculate_esg_metrics,
)

print(HEAD.format("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
print(HEAD.format("  🌱 Dynamic Waste Reduction Engine — Test Suite"))
print(HEAD.format("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"))

# ─── INVENTORY TOOLS ─────────────────────────────────────────────────────────
print(HEAD.format("📦 Inventory Tools"))

def t_inv_basic():
    r = get_inventory_status("ST001")
    assert r["store_id"] == "ST001", "Wrong store_id"
    assert r["total_skus_checked"] > 0, "No SKUs returned"
    assert isinstance(r["inventory"], list), "inventory not a list"
    assert r["total_potential_waste_gbp"] >= 0, "negative waste value"

def t_inv_risk_fields():
    r = get_inventory_status("ST001")
    for item in r["inventory"]:
        assert item["risk_level"] in ("CRITICAL","HIGH","MEDIUM","LOW"), f"Bad risk_level: {item['risk_level']}"
        assert item["days_to_expiry"] >= 0
        assert 0 <= item["waste_risk_pct"] <= 100

def t_inv_category_filter():
    r = get_inventory_status("ST001", category="Dairy")
    for item in r["inventory"]:
        assert item["category"] == "Dairy", f"Got non-Dairy item: {item['category']}"

def t_inv_all_stores():
    for sid in ["ST001","ST002","ST003","ST004","ST005"]:
        r = get_inventory_status(sid)
        assert r["store_id"] == sid

def t_inv_unknown_store():
    r = get_inventory_status("ST999")
    assert r["total_skus_checked"] == 0

def t_inv_critical_exists():
    r = get_inventory_status("ST001")
    risk_levels = {i["risk_level"] for i in r["inventory"]}
    assert "CRITICAL" in risk_levels or "HIGH" in risk_levels, f"No CRITICAL/HIGH items. Levels: {risk_levels}"

def t_transfer_options():
    r = get_transfer_options("SKU-0001", "ST001")
    assert r["sku_id"] == "SKU-0001"
    assert isinstance(r["transfer_options"], list)
    for opt in r["transfer_options"]:
        assert "store_id" in opt
        assert opt["store_id"] != "ST001"  # must not be same store

def t_transfer_unknown():
    r = get_transfer_options("SKU-9999", "ST001")
    assert "error" in r

def t_log_decision():
    log_path = ROOT / "data" / "decisions_log.json"
    before_count = 0
    if log_path.exists():
        with open(log_path) as f:
            try: before_count = len(json.load(f))
            except: pass
    r = log_decision_to_store(
        sku_id="SKU-0001", store_id="ST001",
        action_type="DISCOUNT", action_detail="Test 20% markdown",
        units_affected=50, expected_saving_gbp=22.50,
        reasoning="Test suite: verifying log persistence"
    )
    assert r["status"] == "SUCCESS"
    assert "decision_id" in r["decision"]
    assert r["decision"]["action_type"] == "DISCOUNT"
    assert log_path.exists()
    with open(log_path) as f:
        data = json.load(f)
    assert len(data) > before_count

test("get_inventory_status — basic structure", t_inv_basic)
test("get_inventory_status — risk level fields", t_inv_risk_fields)
test("get_inventory_status — category filter", t_inv_category_filter)
test("get_inventory_status — all 5 stores", t_inv_all_stores)
test("get_inventory_status — unknown store returns empty", t_inv_unknown_store)
test("get_inventory_status — ST001 has CRITICAL/HIGH items", t_inv_critical_exists)
test("get_transfer_options — returns destinations excluding source", t_transfer_options)
test("get_transfer_options — unknown SKU returns error", t_transfer_unknown)
test("log_decision_to_store — persists to JSON", t_log_decision)

# ─── WEATHER TOOLS ───────────────────────────────────────────────────────────
print(HEAD.format("\n🌤️  Weather Tools"))

def t_weather_structure():
    r = get_weather_forecast("ST001")
    assert "forecast" in r
    assert "demand_impact" in r
    assert len(r["forecast"]) > 0
    f = r["forecast"][0]
    assert "date" in f and "temp_max" in f and "rain_mm" in f

def t_weather_all_stores():
    for sid in ["ST001","ST002","ST003","ST004","ST005"]:
        r = get_weather_forecast(sid)
        assert r["store_id"] == sid
        assert "city" in r

def t_weather_heatwave_st001():
    r = get_weather_forecast("ST001")
    assert r["demand_impact"]["heatwave"] is True, "ST001 should have heatwave in mock data"
    assert r["demand_impact"]["overall"] == "HIGH_RISK"

def t_weather_rain_st003():
    r = get_weather_forecast("ST003")
    assert r["demand_impact"]["total_rain_mm"] > 0, "ST003 should have rain in mock data"

def t_weather_unknown():
    r = get_weather_forecast("ST999")
    assert "error" in r

def t_weather_impact_notes():
    r = get_weather_forecast("ST001")
    impact = r["demand_impact"]
    assert isinstance(impact["notes"], list)
    assert len(impact["notes"]) > 0  # heatwave should generate notes

test("get_weather_forecast — basic structure", t_weather_structure)
test("get_weather_forecast — all 5 stores", t_weather_all_stores)
test("get_weather_forecast — ST001 heatwave detection", t_weather_heatwave_st001)
test("get_weather_forecast — ST003 rain detection", t_weather_rain_st003)
test("get_weather_forecast — unknown store returns error", t_weather_unknown)
test("get_weather_forecast — generates demand impact notes", t_weather_impact_notes)

# ─── PRICING TOOLS ───────────────────────────────────────────────────────────
print(HEAD.format("\n💰 Pricing Tools"))

def t_discount_structure():
    r = simulate_discount_action("SKU-0001", "ST001", 20, 2)
    for field in ["gross_margin_pct", "waste_reduction_gbp", "viable",
                  "projected_units_sold", "discounted_price_gbp"]:
        assert field in r, f"Missing field: {field}"

def t_discount_higher_pct_sells_more():
    r10 = simulate_discount_action("SKU-0001", "ST001", 10, 2)
    r30 = simulate_discount_action("SKU-0001", "ST001", 30, 2)
    assert r30["projected_units_sold"] >= r10["projected_units_sold"], \
        f"30% should sell more: {r30['projected_units_sold']} vs {r10['projected_units_sold']}"

def t_discount_margin_decreases():
    r10 = simulate_discount_action("SKU-0001", "ST001", 10, 2)
    r30 = simulate_discount_action("SKU-0001", "ST001", 30, 2)
    assert r30["gross_margin_pct"] <= r10["gross_margin_pct"]

def t_discount_price_correct():
    r = simulate_discount_action("SKU-0001", "ST001", 20, 2)
    inv = get_inventory_status("ST001")
    item = next(i for i in inv["inventory"] if i["sku_id"] == "SKU-0001")
    expected_price = round(item["unit_price"] * 0.80, 2)
    assert abs(r["discounted_price_gbp"] - expected_price) < 0.01, \
        f"Expected £{expected_price}, got £{r['discounted_price_gbp']}"

def t_discount_viability_flag():
    r_low = simulate_discount_action("SKU-0001", "ST001", 10, 2)
    assert isinstance(r_low["viable"], bool)

def t_transfer_basic():
    r = simulate_transfer_action("SKU-0001", "ST001", "ST002", 20)
    assert r["units_transferred"] == 20
    assert "net_saving_gbp" in r
    assert r["kg_food_saved"] == round(20 * 0.5, 2)  # 0.5kg per unit for SKU-0001

def t_transfer_co2():
    r = simulate_transfer_action("SKU-0001", "ST001", "ST002", 20)
    expected_co2 = round(r["kg_food_saved"] * 3.3, 2)
    assert abs(r["co2_avoided_kg"] - expected_co2) < 0.01

def t_transfer_net_saving_math():
    r = simulate_transfer_action("SKU-0001", "ST001", "ST002", 10)
    # net = waste_saved - logistics
    expected_net = round(r["waste_value_saved_gbp"] - r["logistics_cost_gbp"], 2)
    assert abs(r["net_saving_gbp"] - expected_net) < 0.01

def t_coupon_basic():
    r = simulate_loyalty_coupon("SKU-0001", "ST001", 15, 500)
    assert 0 < r["expected_redemptions"] <= 500
    assert r["units_moved"] > 0
    assert "net_benefit_gbp" in r
    assert "viable" in r

def t_coupon_redemption_rate():
    r = simulate_loyalty_coupon("SKU-0001", "ST001", 15, 1000)
    expected = int(1000 * 0.12)
    assert r["expected_redemptions"] == expected, \
        f"Expected {expected} redemptions, got {r['expected_redemptions']}"

def t_esg_metrics():
    decisions = [
        {"expected_saving_gbp": 50.0, "units_affected": 100},
        {"expected_saving_gbp": 30.0, "units_affected": 60},
    ]
    r = calculate_esg_metrics(decisions)
    assert r["total_decisions"] == 2
    assert r["total_waste_value_prevented_gbp"] == 80.0
    assert r["kg_food_saved"] == round(160 * 0.4, 2)
    assert r["co2_avoided_kg"] > 0
    assert r["meals_equivalent"] > 0

test("simulate_discount_action — structure", t_discount_structure)
test("simulate_discount_action — higher % sells more units", t_discount_higher_pct_sells_more)
test("simulate_discount_action — higher % reduces margin", t_discount_margin_decreases)
test("simulate_discount_action — discounted price calculation", t_discount_price_correct)
test("simulate_discount_action — viability flag is bool", t_discount_viability_flag)
test("simulate_transfer_action — basic structure", t_transfer_basic)
test("simulate_transfer_action — CO₂ calculation (3.3× food weight)", t_transfer_co2)
test("simulate_transfer_action — net saving math", t_transfer_net_saving_math)
test("simulate_loyalty_coupon — basic structure", t_coupon_basic)
test("simulate_loyalty_coupon — 12% redemption rate", t_coupon_redemption_rate)
test("calculate_esg_metrics — totals and CO₂", t_esg_metrics)

# ─── INTEGRATION TEST ────────────────────────────────────────────────────────
print(HEAD.format("\n🔗  Integration — Full Pipeline (Tools Only)"))

def t_full_pipeline():
    """End-to-end: forecast → simulate → decide → log → ESG"""
    store_id = "ST001"

    # Step 1: Forecast
    inv = get_inventory_status(store_id)
    weather = get_weather_forecast(store_id)
    assert inv["total_skus_checked"] > 0
    assert weather["demand_impact"]["overall"] in ("HIGH_RISK", "REDUCED_DEMAND", "NORMAL")

    # Step 2: Find worst item
    critical = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL","HIGH")]
    assert len(critical) > 0, "No CRITICAL/HIGH items in ST001"
    item = critical[0]

    # Step 3: Simulate all options
    d20 = simulate_discount_action(item["sku_id"], store_id, 20, item["days_to_expiry"])
    d30 = simulate_discount_action(item["sku_id"], store_id, 30, item["days_to_expiry"])
    transfers = get_transfer_options(item["sku_id"], store_id)
    coupon = simulate_loyalty_coupon(item["sku_id"], store_id, 15, 500)

    # Step 4: Decision logic
    options = [
        ("DISCOUNT_20", d20["waste_reduction_gbp"] if d20["viable"] else 0),
        ("DISCOUNT_30", d30["waste_reduction_gbp"] if d30["viable"] else 0),
        ("COUPON", coupon["net_benefit_gbp"] if coupon["viable"] else 0),
    ]
    best_action, best_saving = max(options, key=lambda x: x[1])
    assert best_saving > 0, "No viable action found"

    # Step 5: Log decision
    log = log_decision_to_store(
        sku_id=item["sku_id"], store_id=store_id,
        action_type="DISCOUNT" if "DISCOUNT" in best_action else "LOYALTY_COUPON",
        action_detail=f"Integration test: {best_action}",
        units_affected=item["stock_qty"],
        expected_saving_gbp=best_saving,
        reasoning=f"Integration test chose {best_action} with £{best_saving:.2f} saving"
    )
    assert log["status"] == "SUCCESS"

    # Step 6: ESG
    esg = calculate_esg_metrics([{"expected_saving_gbp": best_saving, "units_affected": item["stock_qty"]}])
    assert esg["kg_food_saved"] > 0
    assert esg["co2_avoided_kg"] > 0

    print(f"\n        🏆 Best action: {best_action} | £{best_saving:.2f} saving")
    print(f"        🌍 Food saved: {esg['kg_food_saved']}kg | CO₂ avoided: {esg['co2_avoided_kg']}kg")
    print(f"        📋 Decision ID: {log['decision']['decision_id']}")

test("Full pipeline: forecast → simulate → decide → log → ESG", t_full_pipeline)

# ─── Summary ──────────────────────────────────────────────────────────────────
print(HEAD.format("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total  = len(results)

if failed:
    print(f"\033[91m  {failed}/{total} tests FAILED\033[0m")
    for name, ok, err in results:
        if not ok:
            print(f"\033[91m    ✗ {name}: {err}\033[0m")
    sys.exit(1)
else:
    print(f"\033[92m  ✅ All {total} tests PASSED\033[0m")
    print(HEAD.format("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"))
    sys.exit(0)
