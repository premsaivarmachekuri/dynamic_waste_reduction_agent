"""
tools.py
--------
Shared tool functions used by ADK agents.
Pure Python functions — no ADK imports here, keeping them testable independently.
"""

import pandas as pd
import numpy as np
import os
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ─────────────────────────────────────────
# Data loading helpers
# ─────────────────────────────────────────

def _load_inventory() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/inventory.csv", parse_dates=["expiry_date"])

def _load_sales_history() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/sales_history.csv", parse_dates=["date"])

def _load_stores() -> pd.DataFrame:
    return pd.read_csv(f"{DATA_DIR}/stores.csv")


# ─────────────────────────────────────────
# Tool: load_inventory
# ─────────────────────────────────────────

def load_inventory(store_id: Optional[str] = None, sku_id: Optional[str] = None) -> dict:
    """
    Loads at-risk inventory batches. Optionally filter by store and/or SKU.
    Returns batches with waste_risk_score > 0.3 sorted by risk descending.
    """
    df = _load_inventory()

    if store_id:
        df = df[df["store_id"] == store_id]
    if sku_id:
        df = df[df["sku_id"] == sku_id]

    at_risk = df[df["waste_risk_score"] > 0.3].sort_values(
        "waste_risk_score", ascending=False
    ).head(20)

    return {
        "total_batches_checked": len(df),
        "at_risk_count": len(at_risk),
        "batches": at_risk.to_dict(orient="records"),
    }


# ─────────────────────────────────────────
# Tool: score_spoilage_risk (rule-based pre-score for Gemini context)
# ─────────────────────────────────────────

def score_spoilage_risk(batch: dict) -> dict:
    """
    Computes a detailed spoilage risk breakdown for a single batch.
    Returns structured data that ForecastAgent will pass to Gemini.
    """
    days_left = batch.get("days_to_expiry", 0)
    quantity = batch.get("quantity", 0)
    velocity = batch.get("current_velocity", 1)
    projected_unsold = batch.get("projected_unsold", 0)
    weather = batch.get("weather_tag", "normal")
    category = batch.get("category", "produce")

    # Velocity trend factor
    projected_sold = velocity * days_left
    sell_through_rate = min(1.0, projected_sold / max(quantity, 1))

    # Weather risk modifier
    weather_risk = {
        "hot":    {"produce": -0.1, "meat": 0.15, "dairy": 0.1,  "bakery": 0.0, "ready_meal": 0.05},
        "cold":   {"produce": 0.1,  "meat": 0.0,  "dairy": 0.05, "bakery": 0.1, "ready_meal": 0.05},
        "rainy":  {"produce": 0.05, "meat": 0.0,  "dairy": 0.0,  "bakery": -0.05,"ready_meal": -0.05},
        "normal": {"produce": 0.0,  "meat": 0.0,  "dairy": 0.0,  "bakery": 0.0, "ready_meal": 0.0},
    }
    weather_adj = weather_risk.get(weather, {}).get(category, 0.0)

    # Final risk score
    base_risk = 1 - sell_through_rate
    adjusted_risk = min(1.0, max(0.0, base_risk + weather_adj))

    return {
        "batch_id":          batch.get("batch_id"),
        "sku_name":          batch.get("sku_name"),
        "store_id":          batch.get("store_id"),
        "days_to_expiry":    days_left,
        "quantity":          quantity,
        "projected_unsold":  round(projected_unsold, 1),
        "sell_through_rate": round(sell_through_rate, 2),
        "adjusted_risk_score": round(adjusted_risk, 2),
        "weather_context":   weather,
        "risk_level":        "HIGH" if adjusted_risk > 0.6 else "MEDIUM" if adjusted_risk > 0.3 else "LOW",
    }


# ─────────────────────────────────────────
# Tool: simulate_actions
# ─────────────────────────────────────────

def simulate_actions(batch: dict, risk_score: float) -> dict:
    """
    Simulates 4 possible actions for a batch and selects the optimal one.
    Optimization goal: minimise waste × protect margin.
    """
    quantity = batch.get("quantity", 0)
    sell_price = batch.get("sell_price", 5.0)
    cost_price = batch.get("cost_price", 2.5)
    projected_unsold = batch.get("projected_unsold", 0)

    def waste_value(units): return round(units * cost_price, 2)
    def margin_impact(units_sold, discount_pct):
        discounted_price = sell_price * (1 - discount_pct)
        normal_revenue = units_sold * sell_price
        discounted_revenue = units_sold * discounted_price
        return round(normal_revenue - discounted_revenue, 2)

    # Discount uplift model: empirical elasticity
    def uplift(discount_pct, base_risk):
        elasticity = 1.5 + (base_risk * 0.5)  # higher risk = more elastic
        return min(projected_unsold, projected_unsold * discount_pct * elasticity * 2)

    # Scenario 1: No change
    s1_waste = round(projected_unsold, 1)
    s1 = {
        "action": "no_change",
        "label": "No Action",
        "units_saved": 0,
        "waste_units": s1_waste,
        "waste_value_gbp": waste_value(s1_waste),
        "margin_loss_gbp": 0,
        "net_impact_gbp": -waste_value(s1_waste),
    }

    # Scenario 2: 10% discount
    saved_10 = round(uplift(0.10, risk_score), 1)
    waste_10 = max(0, projected_unsold - saved_10)
    s2 = {
        "action": "discount_10",
        "label": "10% Discount",
        "units_saved": saved_10,
        "waste_units": waste_10,
        "waste_value_gbp": waste_value(waste_10),
        "margin_loss_gbp": margin_impact(saved_10, 0.10),
        "net_impact_gbp": round(-(waste_value(waste_10) + margin_impact(saved_10, 0.10)), 2),
    }

    # Scenario 3: 25% discount
    saved_25 = round(uplift(0.25, risk_score), 1)
    waste_25 = max(0, projected_unsold - saved_25)
    s3 = {
        "action": "discount_25",
        "label": "25% Discount",
        "units_saved": saved_25,
        "waste_units": waste_25,
        "waste_value_gbp": waste_value(waste_25),
        "margin_loss_gbp": margin_impact(saved_25, 0.25),
        "net_impact_gbp": round(-(waste_value(waste_25) + margin_impact(saved_25, 0.25)), 2),
    }

    # Scenario 4: Inter-store transfer (transfer up to 40% of projected waste to nearby store)
    transfer_units = min(int(projected_unsold * 0.8), int(quantity * 0.3))
    transfer_cost = round(transfer_units * 0.15, 2)  # £0.15 logistics cost per unit
    waste_transfer = max(0, projected_unsold - transfer_units)
    s4 = {
        "action": "transfer",
        "label": f"Transfer {transfer_units} units to nearby store",
        "units_saved": transfer_units,
        "waste_units": waste_transfer,
        "waste_value_gbp": waste_value(waste_transfer),
        "margin_loss_gbp": transfer_cost,
        "net_impact_gbp": round(-(waste_value(waste_transfer) + transfer_cost), 2),
    }

    scenarios = [s1, s2, s3, s4]

    # Select best action: highest net_impact (least negative = best)
    best = max(scenarios, key=lambda x: x["net_impact_gbp"])

    return {
        "batch_id": batch.get("batch_id"),
        "sku_name": batch.get("sku_name"),
        "store_id": batch.get("store_id"),
        "scenarios": scenarios,
        "recommended_action": best,
        "waste_prevented_units": round(best["units_saved"], 1),
        "value_protected_gbp": round(waste_value(best["units_saved"]), 2),
    }


# ─────────────────────────────────────────
# Tool: build_gemini_forecast_prompt
# ─────────────────────────────────────────

def build_gemini_forecast_prompt(risk_data: dict) -> str:
    """Builds the structured prompt for ForecastAgent to send to Gemini."""
    return f"""You are an expert retail inventory analyst for a supermarket chain.

Analyze this perishable inventory batch and provide a spoilage risk assessment.

Batch Details:
- Product: {risk_data['sku_name']}
- Store: {risk_data['store_id']}
- Days to expiry: {risk_data['days_to_expiry']}
- Current quantity: {risk_data['quantity']} units
- Projected unsold: {risk_data['projected_unsold']} units
- Current sell-through rate: {risk_data['sell_through_rate'] * 100:.0f}%
- Weather context: {risk_data['weather_context']}
- Pre-computed risk level: {risk_data['risk_level']} ({risk_data['adjusted_risk_score']:.0%})

Respond in this exact JSON format:
{{
  "confirmed_risk_score": <float 0-1>,
  "risk_drivers": ["<driver 1>", "<driver 2>", "<driver 3>"],
  "demand_outlook": "<one sentence on expected demand>",
  "urgency": "<IMMEDIATE | TODAY | MONITOR>"
}}"""


def build_gemini_explanation_prompt(decision: dict, risk_data: dict) -> str:
    """Builds the natural language explanation prompt for ExplanationAgent."""
    action = decision["recommended_action"]
    return f"""You are an AI retail operations assistant explaining a waste reduction decision to a store manager.

Product: {decision['sku_name']} at Store {decision['store_id']}
Recommended action: {action['label']}
Units that will be saved from waste: {decision['waste_prevented_units']}
Value protected: £{decision['value_protected_gbp']}
Risk level: {risk_data.get('risk_level', 'HIGH')}

All options considered:
{chr(10).join([f"- {s['label']}: saves {s['units_saved']} units, net impact £{s['net_impact_gbp']}" for s in decision['scenarios']])}

Write a 2-3 sentence plain English explanation of why this action was chosen over the alternatives.
Be specific, confident, and use the numbers. Do not use jargon."""
