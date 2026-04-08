"""
waste_risk_agent.py — ML-driven waste risk scoring and prioritization agent.

Takes raw inventory data and demand forecasts, applies a multi-factor risk model,
and outputs a prioritized risk registry that guides the decision agents.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent

from tools.inventory_tools import get_inventory_status, get_transfer_options
from tools.weather_tools import get_weather_forecast
from tools.bigquery_tools import query_historical_sales
from tools.rag_tools import (
    query_waste_reduction_knowledge,
    query_food_safety_compliance,
    query_seasonal_demand_patterns,
)

waste_risk_agent = Agent(
    name="WasteRiskAgent",
    model="gemini-2.5-flash",
    tools=[
        get_inventory_status,
        get_weather_forecast,
        get_transfer_options,
        query_historical_sales,
        query_waste_reduction_knowledge,
        query_food_safety_compliance,
        query_seasonal_demand_patterns,
    ],
    instruction="""You are an expert waste risk assessment specialist. Your role is to produce
a comprehensive, multi-factor risk registry for perishable inventory, going beyond simple
days-to-expiry to incorporate demand signals, historical waste patterns, and seasonal risk.

RISK SCORING PROTOCOL:

STEP 1 — Base risk assessment:
  Call get_inventory_status(store_id) to get current inventory.
  Note stock_qty, daily_sales, days_to_expiry, and risk_level for all items.

STEP 2 — Demand context:
  Call get_weather_forecast(store_id) for weather demand modifiers.

STEP 3 — Historical waste rate:
  For each CRITICAL/HIGH item, call query_historical_sales(store_id, sku_id, days=30).
  High historical waste_rate_pct (>5%) significantly increases current risk.

STEP 4 — Knowledge base context:
  Call query_waste_reduction_knowledge(query) for category-specific risk factors.
  Call query_food_safety_compliance(category, action) to understand legal constraints.

STEP 5 — Transfer feasibility pre-check:
  For HIGH-risk items with ≥2 days, call get_transfer_options(sku_id, store_id).
  Note whether transfer is an option — this affects which action to recommend.

STEP 6 — Compute composite risk score (0-100):

  COMPOSITE_RISK_SCORE = (
    days_risk_score       × 0.40 +   # how close to expiry
    demand_risk_score     × 0.25 +   # will demand cover stock?
    historical_risk_score × 0.20 +   # has this product wasted before?
    weather_risk_score    × 0.10 +   # weather reducing demand?
    stock_velocity_score  × 0.05     # is stock turnover slowing?
  )

  Where:
    days_risk_score:        CRITICAL=100, HIGH=75, MEDIUM=50, LOW=20
    demand_risk_score:      100 if projected_unsold > 50% of stock, scaled linearly
    historical_risk_score:  min(historical_waste_rate_pct × 5, 100)
    weather_risk_score:     heatwave=80 if meat/fish, rain=60 for all fresh categories
    stock_velocity_score:   100 if stock_qty > 3× daily_sales, 0 if stock_qty < daily_sales

STEP 7 — Output prioritized risk registry:

  Format output as:
  ┌─────────────────────────────────────────────────────────────────┐
  │ WASTE RISK REGISTRY — Store [STORE_ID] — [DATE]                │
  ├────────────┬─────────────────────┬──────┬──────────┬───────────┤
  │ Risk Score │ Product             │ SKU  │ Level    │ Action    │
  ├────────────┼─────────────────────┼──────┼──────────┼───────────┤
  │ 97/100     │ Chicken Breast 500g │ SKU-0001 │ CRITICAL │ IMMEDIATE │
  │ ...        │ ...                 │ ...  │ ...      │ ...       │
  └────────────┴─────────────────────┴──────┴──────────┴───────────┘

  For each item include:
  - Composite risk score (0-100)
  - Risk level (CRITICAL/HIGH/MEDIUM/LOW)
  - Primary risk driver (expiry / demand_drop / historical_waste / weather)
  - Recommended action type (DISCOUNT / TRANSFER / LOYALTY_COUPON / DONATE)
  - Transfer available (YES/NO)
  - Constraint flags (FOOD_SAFETY_COMPLIANT / MARGIN_RISK / COLD_CHAIN_REQUIRED)

  End with a paragraph: "Top 3 items requiring immediate action within the next 4 hours:"
  listing the highest-risk items with specific reasoning for urgency.""",
)
