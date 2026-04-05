"""
forecast_agent.py
-----------------
ForecastAgent: Scores spoilage risk for each at-risk batch using Gemini.
Takes DataAgent output, enriches each batch with AI risk assessment.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import score_spoilage_risk, build_gemini_forecast_prompt


def score_batch_risk(batch_json: str) -> dict:
    """
    Scores the spoilage risk for a single inventory batch.
    Returns a structured risk assessment with score, drivers, and urgency.

    Args:
        batch_json: JSON string of a single batch record from DataAgent

    Returns:
        dict with adjusted_risk_score, risk_level, risk_drivers, urgency, and gemini_prompt
    """
    if isinstance(batch_json, str):
        batch = json.loads(batch_json)
    else:
        batch = batch_json

    risk_data = score_spoilage_risk(batch)
    gemini_prompt = build_gemini_forecast_prompt(risk_data)

    # Attach the prompt so the agent can call Gemini inline
    risk_data["gemini_prompt"] = gemini_prompt
    return risk_data


forecast_agent = Agent(
    name="ForecastAgent",
    model="gemini-1.5-flash",
    description=(
        "Scores spoilage risk for perishable inventory batches using demand forecasting "
        "and Gemini AI analysis. Returns risk scores, drivers, and urgency levels."
    ),
    instruction=(
        "You are a spoilage risk forecasting agent. For each batch provided, "
        "call score_batch_risk to compute the structured risk data. "
        "Then use your own reasoning (you are Gemini) to assess the risk_drivers, "
        "confirm the risk_score, and assign urgency (IMMEDIATE / TODAY / MONITOR). "
        "Return a list of enriched risk assessments — one per batch — as structured JSON. "
        "Focus on the top 5 highest-risk batches if there are many."
    ),
    tools=[FunctionTool(func=score_batch_risk)],
)
