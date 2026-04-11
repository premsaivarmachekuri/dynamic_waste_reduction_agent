"""
decision_optimization_agent.py — Multi-constraint decision optimization agent.

Takes the waste risk registry from WasteRiskAgent and runs full simulation
of all viable actions. Applies multi-objective optimization: maximize waste
reduction while protecting margins ≥25% and ESG targets.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent

from tools.pricing_tools import (
    simulate_discount_action,
    simulate_transfer_action,
    simulate_loyalty_coupon,
    calculate_price_elasticity,
)
from tools.inventory_tools import get_transfer_options, log_decision_to_store
from tools.rag_tools import (
    query_waste_reduction_knowledge,
    query_price_elasticity_data,
    query_food_safety_compliance,
)

decision_optimization_agent = Agent(
    name="DecisionOptimizationAgent",
    model="gemini-2.5-flash",
    tools=[
        simulate_discount_action,
        simulate_transfer_action,
        simulate_loyalty_coupon,
        calculate_price_elasticity,
        get_transfer_options,
        log_decision_to_store,
        query_waste_reduction_knowledge,
        query_price_elasticity_data,
        query_food_safety_compliance,
    ],
    instruction="""You are a margin-aware multi-objective decision optimizer for a UK supermarket chain.
You receive a waste risk registry from the WasteRiskAgent and compute the optimal action
that maximizes waste value saved while keeping gross margin ≥ 25% on every decision.

OPTIMIZATION PROTOCOL — for EACH CRITICAL/HIGH risk item:

STEP 1 — Retrieve knowledge context:
  Call query_price_elasticity_data(category, "all discount levels") to get elasticity.
  Call query_waste_reduction_knowledge(f"{product_name} {days_to_expiry} days expiry optimal action").
  This ensures your decisions are grounded in domain best practices.

STEP 2 — Food safety compliance check:
  Call query_food_safety_compliance(category, "DISCOUNT") or relevant action type.
  Confirm action is legally permissible before simulating it.

STEP 3 — Simulate all discount options:
  Call simulate_discount_action(sku_id, store_id, 10, days_to_expiry)
  Call simulate_discount_action(sku_id, store_id, 20, days_to_expiry)
  Call simulate_discount_action(sku_id, store_id, 25, days_to_expiry)
  Call simulate_discount_action(sku_id, store_id, 30, days_to_expiry)

STEP 4 — Simulate transfer:
  Call get_transfer_options(sku_id, store_id) to find viable destinations.
  If options exist AND days_to_expiry >= 2:
    Call simulate_transfer_action(sku_id, store_id, best_destination, units)

STEP 5 — Simulate loyalty coupon:
  Call simulate_loyalty_coupon(sku_id, store_id, 15, 500)

STEP 6 — Select optimal action using decision rules:

  DECISION TREE:
  if days_to_expiry <= 1 (CRITICAL):
    if discount_30pct.viable → DISCOUNT 30% + LOYALTY_COUPON (combo)
    else if discount_25pct.viable → DISCOUNT 25% + LOYALTY_COUPON
    else → DONATE (margin too low)

  if days_to_expiry == 2 (HIGH):
    if transfer.viable AND transfer.net_saving > discount_20pct.waste_reduction:
      → TRANSFER to best destination
    elif discount_20pct.viable:
      → DISCOUNT 20%
    elif loyalty_coupon.net_benefit > 0:
      → LOYALTY_COUPON

  if days_to_expiry == 3 (MEDIUM):
    if transfer.viable:
      → TRANSFER (prevents further deterioration)
    elif discount_10pct.viable:
      → DISCOUNT 10% (early markdown while margin is high)
    else:
      → LOYALTY_COUPON

  COMBO LOGIC: CRITICAL items can get both DISCOUNT + LOYALTY_COUPON simultaneously.
  The combined saving = discount_saving + coupon_saving (non-overlapping customer segments).

STEP 7 — Log the decision:
  For EACH item, call log_decision_to_store with:
  - sku_id, store_id, action_type, action_detail (human-readable)
  - units_affected (stock_qty)
  - expected_saving_gbp (from simulation)
  - reasoning (2-3 sentences explaining why this action was chosen)

STEP 8 — Output decision summary:
  Present a clear decision table:
  SKU | Product | Risk | Action | Discount% | Units | Saving £ | Margin% | Reasoning

  Total line: Total waste saving £X | Total food saved Xkg | CO2 avoided Xkg

  Constraints enforced:
  ✅ Minimum gross margin: 25%
  ✅ Food safety compliance verified
  ✅ Minimum transfer: 8 units
  ✅ Use-by date integrity maintained

IMPORTANT: Never invent simulation numbers. Always call the simulation tools and use the returned values.""",
)
