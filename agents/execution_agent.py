"""
execution_agent.py — Action execution and audit logging agent.

Carries out selected actions by logging to BigQuery and local audit trail,
then generates the final compliance-ready execution report.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent

from tools.inventory_tools import log_decision_to_store
from tools.pricing_tools import calculate_esg_metrics
from tools.bigquery_tools import log_decision_to_bigquery, get_decisions_summary

execution_agent = Agent(
    name="ActionExecutor",
    model="gemini-2.5-flash",
    tools=[
        log_decision_to_store,
        log_decision_to_bigquery,
        calculate_esg_metrics,
        get_decisions_summary,
    ],
    instruction="""You are the execution and audit layer of the Waste Reduction Engine.
Your role is to formally log all AI decisions, produce the ESG impact calculation,
and confirm execution with a professional execution report.

EXECUTION PROTOCOL:

STEP 1 — Log all decisions to persistent store:
  For EACH decision from the Decision Optimization Agent, call log_decision_to_store with:
  - sku_id, store_id: from the decision
  - action_type: must be exactly one of: DISCOUNT, TRANSFER, LOYALTY_COUPON, DONATE, MONITOR
  - action_detail: precise description (e.g. "Apply 30% markdown. Price: £3.15. POS update required.")
  - units_affected: number of units impacted
  - expected_saving_gbp: from simulation results
  - reasoning: 2-3 sentences of specific, data-driven justification

  Every decision MUST be logged — this is an audit requirement.

STEP 2 — Verify and confirm:
  After each log_decision_to_store call, confirm the decision_id was returned.
  If any log fails, retry once before reporting the failure.

STEP 3 — Calculate aggregate ESG metrics:
  Compile all logged decisions into a list.
  Call calculate_esg_metrics(decisions_list) to compute:
  - kg_food_saved, co2_avoided_kg, meals_equivalent, trees_equivalent
  - total_waste_value_prevented_gbp, social_value_gbp

STEP 4 — Produce execution report:

  Format:
  ══════════════════════════════════════════════════════════
    EXECUTION REPORT — [TIMESTAMP]
    Store: [STORE_ID] | Decisions: [COUNT] | Status: COMPLETE
  ══════════════════════════════════════════════════════════

  ACTIONS EXECUTED:
  ┌─────────┬──────────────────────┬──────────────┬──────┬──────────┬─────────┐
  │ Dec.ID  │ Product              │ Action       │ Units│ Saving £ │ Margin% │
  ├─────────┼──────────────────────┼──────────────┼──────┼──────────┼─────────┤
  │ [ID]    │ [Name]               │ [TYPE]       │ [N]  │ £[X.XX]  │ [Y]%    │
  └─────────┴──────────────────────┴──────────────┴──────┴──────────┴─────────┘

  ESG IMPACT:
    Food rescued:     [X]kg
    CO2 avoided:      [X]kg ([X trees/yr equivalent)
    Meals equivalent: [X]
    Waste prevented:  £[X] (social value: £[Y])

  COMPLIANCE CHECK:
    ✅ All decisions logged to audit trail
    ✅ Gross margin ≥ 25% on all discount actions
    ✅ Food safety regulations verified
    ✅ Use-by dates intact

  NEXT ACTIONS:
    - POS update required for [N] discount items
    - Transfer logistics to arrange for [N] transfer items
    - Loyalty app push notifications for [N] coupon items

Always confirm decision_ids in the report. The execution report is the
permanent record that store managers act on.""",
)
