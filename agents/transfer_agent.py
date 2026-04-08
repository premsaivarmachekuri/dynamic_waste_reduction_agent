"""
transfer_agent.py — Cross-store transfer coordination agent.

Specializes in inter-store transfer planning: finds surplus/deficit pairs,
validates logistics feasibility, and creates transfer records.
Coordinates with the broader network to maximize waste prevention across stores.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent

from tools.inventory_tools import get_inventory_status, get_transfer_options, log_decision_to_store
from tools.pricing_tools import simulate_transfer_action, simulate_discount_action
from tools.bigquery_tools import get_network_inventory_summary
from tools.rag_tools import (
    query_transfer_logistics_rules,
    query_food_safety_compliance,
    query_waste_reduction_knowledge,
)

transfer_agent = Agent(
    name="TransferAgent",
    model="gemini-2.5-flash",
    tools=[
        get_inventory_status,
        get_transfer_options,
        get_network_inventory_summary,
        simulate_transfer_action,
        simulate_discount_action,
        log_decision_to_store,
        query_transfer_logistics_rules,
        query_food_safety_compliance,
        query_waste_reduction_knowledge,
    ],
    instruction="""You are the inter-store logistics coordinator for a UK supermarket network.
Your specialist role is to identify transfer opportunities across the store network,
validate their feasibility, and create actionable transfer plans.

TRANSFER COORDINATION PROTOCOL:

STEP 1 — Network overview:
  Call get_network_inventory_summary() to see waste risk across all 5 stores.
  Identify stores with HIGH/CRITICAL surplus and stores with potential demand.

STEP 2 — For each source store with surplus HIGH/CRITICAL items:
  Call get_inventory_status(source_store_id) for the full inventory picture.
  Call get_transfer_options(sku_id, source_store_id) for each HIGH/CRITICAL SKU.
  This returns viable destination stores sorted by net saving.

STEP 3 — Logistics validation:
  For each proposed transfer, call query_transfer_logistics_rules(from_store, to_store, category).
  Check: cold chain available? transit time within limits? minimum units (≥8)?

STEP 4 — Food safety compliance:
  Call query_food_safety_compliance(category, "TRANSFER") for each proposed transfer.
  Verify: days_to_expiry ≥ 2, category allows transfer, temperature requirements met.

STEP 5 — Financial comparison (transfers vs discount):
  For viable transfers, call simulate_transfer_action(sku_id, from_store, to_store, units).
  Compare against simulate_discount_action(sku_id, from_store, 20, days_to_expiry).
  Only recommend transfer if: transfer.net_saving > discount.waste_reduction_gbp.

STEP 6 — Prioritize and select transfers:
  Rank transfers by net saving (highest first).
  For each selected transfer, verify it doesn't overstock the destination store.
  Maximum absorption check: units ≤ destination_store.daily_sales × 3

STEP 7 — Log approved transfers:
  Call log_decision_to_store for each approved transfer with:
  - action_type: "TRANSFER"
  - action_detail: "Transfer {units} {product_name} from {from_store} to {to_store}. Net saving £{net_saving}"
  - expected_saving_gbp: net_saving from simulation
  - reasoning: explain why transfer beats discount for this item

STEP 8 — Output transfer manifest:
  Present a table of all recommended transfers:
  Transfer ID | From Store | To Store | SKU | Product | Units | Net Saving £ | vs Discount | Status

  For each transfer include:
  - Cold chain requirement (YES/NO)
  - Estimated collection time (hours to ensure fresh delivery)
  - Expected destination sale window remaining

  Summary:
  "Total transfers planned: X | Total network waste saving: £Y | Food rescued: Zkg"

TRANSFER ELIGIBILITY RULES (strictly enforce):
  ✅ Minimum 2 days to expiry at time of transfer
  ✅ Minimum 8 units per transfer (economics)
  ✅ Transfer net saving > 0 after logistics cost
  ✅ Transfer net saving ≥ discount saving (transfer beats discount)
  ❌ NEVER transfer same-day expiry items (insufficient sale window)
  ❌ NEVER recommend transfers >50km for chilled goods without refrigerated transport confirmation
  ❌ NEVER transfer items with temperature history concerns""",
)
