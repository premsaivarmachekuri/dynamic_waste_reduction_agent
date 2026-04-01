"""
explanation_agent.py
--------------------
ExplanationAgent: Generates plain English explanations for each decision.
Powered by Gemini 1.5 Flash — the "why" layer for store managers and judges.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import build_gemini_explanation_prompt


def format_decision_for_display(decision_json: str, risk_data_json: str = "{}") -> dict:
    """
    Formats a decision for display in the Gradio UI.
    Builds the Gemini explanation prompt and structures the output card.

    Args:
        decision_json: JSON string of a decision from DecisionAgent
        risk_data_json: JSON string of risk data from ForecastAgent (optional)

    Returns:
        dict with display_card, explanation_prompt, and esg_impact fields
    """
    if isinstance(decision_json, str):
        decision = json.loads(decision_json)
    else:
        decision = decision_json

    if isinstance(risk_data_json, str):
        risk_data = json.loads(risk_data_json) if risk_data_json != "{}" else {}
    else:
        risk_data = risk_data_json

    action = decision.get("recommended_action", {})
    explanation_prompt = build_gemini_explanation_prompt(decision, risk_data)

    # ESG impact: 1 kg food waste ≈ 2.5 kg CO2e (WRAP methodology)
    units_saved = decision.get("waste_prevented_units", 0)
    avg_weight_kg = 0.4  # average perishable unit weight
    co2_saved_kg = round(units_saved * avg_weight_kg * 2.5, 1)

    display_card = {
        "sku_name":              decision.get("sku_name", "Unknown"),
        "store_id":              decision.get("store_id", "Unknown"),
        "recommended_action":    action.get("label", "No action"),
        "waste_units_prevented": units_saved,
        "value_protected_gbp":   decision.get("value_protected_gbp", 0),
        "margin_loss_gbp":       action.get("margin_loss_gbp", 0),
        "net_saving_gbp":        round(decision.get("value_protected_gbp", 0) - action.get("margin_loss_gbp", 0), 2),
        "co2_saved_kg":          co2_saved_kg,
        "risk_level":            risk_data.get("risk_level", "HIGH"),
        "urgency":               risk_data.get("urgency", "IMMEDIATE"),
        "all_scenarios":         decision.get("scenarios", []),
    }

    return {
        "display_card":       display_card,
        "explanation_prompt": explanation_prompt,
        "esg_impact": {
            "units_prevented": units_saved,
            "co2_saved_kg":    co2_saved_kg,
            "value_gbp":       decision.get("value_protected_gbp", 0),
        }
    }


explanation_agent = Agent(
    name="ExplanationAgent",
    model="gemini-1.5-flash",
    description=(
        "Generates plain English explanations for waste reduction decisions. "
        "Formats decision cards for the Gradio dashboard and calculates ESG impact."
    ),
    instruction=(
        "You are an explanation agent that makes AI decisions transparent to store managers. "
        "For each decision from DecisionAgent, call format_decision_for_display to get "
        "the structured display card and explanation prompt. "
        "Then write a clear, 2-3 sentence explanation of WHY this action was chosen — "
        "use the specific numbers (units saved, £ value, scenarios compared). "
        "Be direct and confident. Your explanation will appear in the store manager dashboard. "
        "Also summarise the total ESG impact across all decisions: "
        "total units prevented from waste, total CO2 saved, total value protected. "
        "Return all display_cards with their explanations as a structured list."
    ),
    tools=[FunctionTool(func=format_decision_for_display)],
)
