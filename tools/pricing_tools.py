"""
pricing_tools.py — ADK FunctionTools for discount simulation, transfer analysis,
loyalty coupon modeling, and ESG metrics.

Uses category-aware price elasticity coefficients sourced from the RAG knowledge base.
"""

import json
import os
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_inventory.json"

# Category-aware elasticity coefficients (from price_elasticity_data.txt)
_ELASTICITY = {
    "Meat & Poultry": 1.8,
    "Fish & Seafood":  1.5,
    "Dairy":           0.7,
    "Bakery":          1.7,
    "Produce":         1.9,
    "Ready Meals":     1.5,
}
_DEFAULT_ELASTICITY = 1.5


def _get_item(sku_id: str, store_id: str) -> dict | None:
    with open(_DATA_PATH) as f:
        data = json.load(f)
    return next(
        (i for i in data["inventory"] if i["sku_id"] == sku_id and i["store_id"] == store_id),
        None,
    )


def simulate_discount_action(
    sku_id: str,
    store_id: str,
    discount_pct: int,
    days_to_expiry: int,
) -> dict:
    """
    Simulate applying a markdown discount to a SKU and calculate margin/waste tradeoff.

    Uses category-specific price elasticity coefficients to accurately model
    demand response. Enforces minimum 25% gross margin floor.

    Args:
        sku_id: Product SKU identifier
        store_id: Store where discount is applied
        discount_pct: Discount percentage to simulate (e.g. 10, 20, 25, 30, 40, 50)
        days_to_expiry: Days remaining before use-by date

    Returns:
        Detailed P&L simulation including projected sales, waste saved, margin,
        and a recommendation string.
    """
    item = _get_item(sku_id, store_id)
    if not item:
        return {"error": f"Item {sku_id} not found in {store_id}"}

    unit_price  = item["unit_price"]
    unit_cost   = item["unit_cost"]
    stock_qty   = item["stock_qty"]
    daily_sales = item["daily_sales"]
    category    = item.get("category", "")

    # Category-specific elasticity
    elasticity        = _ELASTICITY.get(category, _DEFAULT_ELASTICITY)
    demand_uplift_pct = discount_pct * elasticity / 100
    new_daily_sales   = daily_sales * (1 + demand_uplift_pct)
    projected_sold    = min(new_daily_sales * max(days_to_expiry, 0), stock_qty)
    projected_unsold  = max(stock_qty - projected_sold, 0)

    discounted_price = unit_price * (1 - discount_pct / 100)
    revenue_sold     = projected_sold * discounted_price
    cost_all         = stock_qty * unit_cost
    gross_margin     = ((revenue_sold - cost_all) / revenue_sold * 100) if revenue_sold > 0 else -999

    # Baseline without discount
    baseline_sold    = min(daily_sales * max(days_to_expiry, 0), stock_qty)
    baseline_unsold  = max(stock_qty - baseline_sold, 0)
    baseline_waste_cost = baseline_unsold * unit_cost
    waste_cost          = projected_unsold * unit_cost
    waste_reduction_gbp = baseline_waste_cost - waste_cost

    viable = gross_margin >= 25

    return {
        "sku_id":                  sku_id,
        "product_name":            item["name"],
        "category":                category,
        "store_id":                store_id,
        "action":                  "DISCOUNT",
        "discount_pct":            discount_pct,
        "price_elasticity_used":   elasticity,
        "original_price_gbp":      round(unit_price, 2),
        "discounted_price_gbp":    round(discounted_price, 2),
        "projected_units_sold":    round(projected_sold, 1),
        "projected_units_wasted":  round(projected_unsold, 1),
        "gross_margin_pct":        round(gross_margin, 1),
        "waste_reduction_gbp":     round(waste_reduction_gbp, 2),
        "revenue_gbp":             round(revenue_sold, 2),
        "viable":                  viable,
        "recommendation": (
            f"Apply {discount_pct}% discount — margin {gross_margin:.1f}%, "
            f"saves £{waste_reduction_gbp:.2f} in waste, "
            f"moves {projected_sold:.0f}/{stock_qty} units"
        ) if viable else (
            f"Discount {discount_pct}% NOT viable — margin {gross_margin:.1f}% below 25% floor"
        ),
    }


def simulate_transfer_action(
    sku_id: str,
    from_store_id: str,
    to_store_id: str,
    units_to_transfer: int,
) -> dict:
    """
    Simulate transferring stock units from one store to another.

    Calculates logistics cost, waste value saved, net saving, and ESG impact.
    Uses the standard UK retail logistics cost of £0.18/unit.

    Args:
        sku_id: Product SKU identifier
        from_store_id: Source store identifier
        to_store_id: Destination store identifier
        units_to_transfer: Number of units to move

    Returns:
        Transfer cost/benefit analysis with ESG impact metrics.
    """
    item = _get_item(sku_id, from_store_id)
    if not item:
        return {"error": f"Item {sku_id} not found in {from_store_id}"}

    logistics_cost_per_unit = 0.18  # £0.18/unit standard UK retail logistics
    total_logistics_cost    = units_to_transfer * logistics_cost_per_unit
    waste_value_saved       = units_to_transfer * item["unit_cost"]
    net_saving              = waste_value_saved - total_logistics_cost
    kg_food_saved           = round(units_to_transfer * item["weight_kg"], 2)
    co2_avoided_kg          = round(kg_food_saved * 3.3, 2)
    meals_equivalent        = int(kg_food_saved / 0.3)

    return {
        "sku_id":               sku_id,
        "product_name":         item["name"],
        "category":             item.get("category", ""),
        "from_store":           from_store_id,
        "to_store":             to_store_id,
        "action":               "TRANSFER",
        "units_transferred":    units_to_transfer,
        "logistics_cost_gbp":   round(total_logistics_cost, 2),
        "waste_value_saved_gbp": round(waste_value_saved, 2),
        "net_saving_gbp":       round(net_saving, 2),
        "viable":               net_saving > 0 and units_to_transfer >= 8,
        "kg_food_saved":        kg_food_saved,
        "co2_avoided_kg":       co2_avoided_kg,
        "meals_equivalent":     meals_equivalent,
        "recommendation": (
            f"Transfer {units_to_transfer} units to {to_store_id} — "
            f"net saving £{net_saving:.2f}, saves {kg_food_saved}kg food "
            f"({co2_avoided_kg}kg CO₂ avoided)"
        ) if net_saving > 0 else (
            f"Transfer not cost-effective: net saving £{net_saving:.2f} after £{total_logistics_cost:.2f} logistics"
        ),
    }


def simulate_loyalty_coupon(
    sku_id: str,
    store_id: str,
    coupon_value_pct: int,
    target_customers: int,
) -> dict:
    """
    Simulate sending targeted loyalty coupons to drive demand for at-risk stock.

    Models redemption rates based on customer tier distribution and coupon value.
    Best for: medium-risk items with 2-3 days to expiry and large local loyalty base.

    Args:
        sku_id: Product SKU identifier
        store_id: Store identifier
        coupon_value_pct: Coupon discount percentage (e.g. 10, 15, 20)
        target_customers: Number of loyalty app users to send the coupon to

    Returns:
        Expected redemptions, cost, and net benefit from the coupon campaign.
    """
    item = _get_item(sku_id, store_id)
    if not item:
        return {"error": f"Item {sku_id} not found in {store_id}"}

    # Tiered redemption model (matches RAG data)
    if target_customers >= 400:
        redemption_rate = 0.15   # mix of gold/silver/bronze
    elif target_customers >= 200:
        redemption_rate = 0.18   # smaller, more engaged segment
    else:
        redemption_rate = 0.22   # highly targeted = higher rate

    expected_redemptions = int(target_customers * redemption_rate)
    units_moved          = min(expected_redemptions, item["stock_qty"])
    coupon_cost          = units_moved * item["unit_price"] * (coupon_value_pct / 100)
    waste_value_saved    = units_moved * item["unit_cost"]
    net_benefit          = waste_value_saved - coupon_cost
    kg_saved             = round(units_moved * item["weight_kg"], 2)

    return {
        "sku_id":               sku_id,
        "product_name":         item["name"],
        "store_id":             store_id,
        "action":               "LOYALTY_COUPON",
        "coupon_value_pct":     coupon_value_pct,
        "customers_targeted":   target_customers,
        "redemption_rate_pct":  round(redemption_rate * 100, 1),
        "expected_redemptions": expected_redemptions,
        "units_moved":          units_moved,
        "coupon_cost_gbp":      round(coupon_cost, 2),
        "waste_value_saved_gbp": round(waste_value_saved, 2),
        "net_benefit_gbp":      round(net_benefit, 2),
        "kg_food_saved":        kg_saved,
        "viable":               net_benefit > 0,
        "recommendation": (
            f"Send {coupon_value_pct}% coupon to {target_customers} customers — "
            f"expect {expected_redemptions} redemptions, net benefit £{net_benefit:.2f}, "
            f"saves {kg_saved}kg food"
        ) if net_benefit > 0 else (
            f"Coupon not viable: net benefit £{net_benefit:.2f} after £{coupon_cost:.2f} coupon cost"
        ),
    }


def calculate_price_elasticity(
    category: str,
    discount_pct: float,
) -> dict:
    """
    Calculate expected demand uplift for a given category and discount percentage.

    Uses category-specific price elasticity coefficients from the knowledge base.
    Returns the uplift percentage and new demand multiplier.

    Args:
        category: Product category (e.g. 'Meat & Poultry', 'Dairy', 'Produce')
        discount_pct: Discount percentage to model (e.g. 20.0)

    Returns:
        Dict with elasticity coefficient, demand uplift percentage, and demand multiplier.
    """
    elasticity     = _ELASTICITY.get(category, _DEFAULT_ELASTICITY)
    demand_uplift  = discount_pct * elasticity / 100
    demand_multiplier = 1 + demand_uplift

    return {
        "category":           category,
        "discount_pct":       discount_pct,
        "elasticity_coeff":   elasticity,
        "demand_uplift_pct":  round(demand_uplift * 100, 1),
        "demand_multiplier":  round(demand_multiplier, 3),
        "interpretation":     (
            f"A {discount_pct}% discount on {category} products increases demand by "
            f"{demand_uplift*100:.1f}% (elasticity ε = {elasticity}). "
            f"Daily sales multiply by {demand_multiplier:.2f}x."
        ),
    }


def calculate_esg_metrics(decisions_log: list) -> dict:
    """
    Calculate aggregate ESG impact metrics from a list of executed decisions.

    Uses WRAP Courtauld Commitment standards for CO2 emission factors.

    Args:
        decisions_log: List of decision dicts from the decision log.
                       Each dict should have: units_affected, expected_saving_gbp,
                       action_type fields.

    Returns:
        ESG summary with food saved, CO2 avoided, meals equivalent, and social value.
    """
    with open(_DATA_PATH) as f:
        data = json.load(f)

    sku_weights = {i["sku_id"]: i["weight_kg"] for i in data["inventory"]}

    total_saving_gbp = sum(d.get("expected_saving_gbp", 0) for d in decisions_log)
    total_units      = sum(d.get("units_affected", 0) for d in decisions_log)

    # Calculate weighted average kg using actual SKU weights where possible
    total_kg = 0.0
    for d in decisions_log:
        weight  = sku_weights.get(d.get("sku_id", ""), 0.4)
        units   = d.get("units_affected", 0)
        total_kg += units * weight

    total_kg         = round(total_kg, 2)
    co2_avoided      = round(total_kg * 3.3, 2)   # WRAP standard: 3.3 kg CO2e/kg
    meals_equivalent = int(total_kg / 0.3)          # 300g per meal
    trees_equivalent = round(co2_avoided / 21, 1)   # 21 kg CO2/tree/year
    social_value     = round(total_saving_gbp * 2.2, 2)  # NEF social value multiplier

    action_breakdown = {}
    for d in decisions_log:
        at = d.get("action_type", "UNKNOWN")
        action_breakdown[at] = action_breakdown.get(at, 0) + 1

    return {
        "total_decisions":                  len(decisions_log),
        "action_breakdown":                 action_breakdown,
        "total_waste_value_prevented_gbp":  round(total_saving_gbp, 2),
        "social_value_gbp":                 social_value,
        "total_units_saved":                total_units,
        "kg_food_saved":                    total_kg,
        "co2_avoided_kg":                   co2_avoided,
        "meals_equivalent":                 meals_equivalent,
        "trees_equivalent":                 trees_equivalent,
        "sdg_contribution":                 "SDG 2 (Zero Hunger), SDG 12.3 (Food Waste), SDG 13 (Climate Action)",
        "wrap_courtauld_progress_pct":      round(co2_avoided / 150 * 100, 1),  # vs 150kg CO2 annual target per store
    }
