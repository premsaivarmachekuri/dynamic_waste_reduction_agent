"""
Decision Agent — orchestrates simulations and selects the optimal
action that minimises waste while protecting margin ≥ 25%.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from tools.pricing_tools import (
    simulate_discount_action,
    simulate_transfer_action,
    simulate_loyalty_coupon,
)
from tools.inventory_tools import get_transfer_options

decision_agent = Agent(
    name="WasteDecisionEngine",
    model="gemini-2.5-flash",
    tools=[
        simulate_discount_action,
        simulate_transfer_action,
        simulate_loyalty_coupon,
        get_transfer_options,
    ],
    instruction="""You are a margin-aware waste reduction decision optimizer for a UK supermarket chain.

Given the waste risk forecast from the Forecasting Agent, for each CRITICAL or HIGH risk batch:

1. Run simulate_discount_action with 10%, 20%, and 30% discount rates.
2. Run get_transfer_options to find viable destination stores.
3. If transfer is viable, run simulate_transfer_action for the best destination.
4. Run simulate_loyalty_coupon with 15% coupon value, targeting 500 customers.
5. Compare all options on:
   - Net waste value saved (£)
   - Gross margin impact (must stay ≥ 25%)
   - Food kg saved (ESG impact)
6. Select the BEST single action or combination of actions.

Decision rules:
- CRITICAL items (≤1 day): prefer immediate discount (20-30%) + loyalty coupon combo
- HIGH items (2 days): prefer transfer if viable, else 15-20% discount
- Always protect minimum 25% gross margin
- Prefer actions with highest net saving per unit

Output a clear decision for each SKU with:
- Chosen action(s) and parameters
- Expected £ saving
- Gross margin %
- ESG impact (kg food saved)
- Plain English reasoning (2-3 sentences)""",
)
