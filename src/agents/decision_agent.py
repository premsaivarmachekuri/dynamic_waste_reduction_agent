"""
decision_agent.py
-----------------
DecisionAgent: Runs multi-scenario optimization for each at-risk batch.
Simulates no_change / discount_10 / discount_25 / transfer and selects optimal action.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import simulate_actions


def run_action_simulation(batch_json: str, risk_score: float = 0.5) -> dict:
    """
    Simulates 4 possible waste reduction actions for a batch and selects the optimal one.
    Actions: no_change, 10% discount, 25% discount, inter-store transfer.
    Optimization: minimise waste value lost + margin erosion.

    Args:
        batch_json: JSON string of a batch record (from DataAgent/ForecastAgent)
        risk_score: Float 0-1 from ForecastAgent (default 0.5 if not provided)

    Returns:
        dict with all 4 scenarios and the recommended_action
    """
    if isinstance(batch_json, str):
        batch = json.loads(batch_json)
    else:
        batch = batch_json

    return simulate_actions(batch, risk_score=risk_score)


decision_agent = Agent(
    name="DecisionAgent",
    model="gemini-1.5-flash",
    description=(
        "Runs multi-scenario optimization for perishable inventory batches. "
        "Simulates discount, transfer, and no-action scenarios. "
        "Selects the optimal action to maximise waste reduction while protecting margin."
    ),
    instruction=(
        "You are a decision optimization agent for supermarket waste reduction. "
        "For each at-risk batch from ForecastAgent, call run_action_simulation "
        "with the batch data and its risk_score. "
        "Review the 4 scenarios returned (no_change, discount_10, discount_25, transfer). "
        "The recommended_action field already contains the optimal selection. "
        "Return a structured list of decisions — one per batch — including: "
        "batch_id, sku_name, store_id, recommended_action, waste_prevented_units, value_protected_gbp, "
        "and all 4 scenarios for transparency. "
        "If transfer is selected, note which nearby store should receive the stock."
    ),
    tools=[FunctionTool(func=run_action_simulation)],
)
