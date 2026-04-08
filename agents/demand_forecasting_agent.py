"""
demand_forecasting_agent.py — Vertex AI-powered demand forecasting agent.

Combines live inventory data, weather forecasts, historical sales from BigQuery,
and seasonal patterns from the RAG knowledge base to produce accurate
demand predictions per SKU per store.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent

from tools.inventory_tools import get_inventory_status
from tools.weather_tools import get_weather_forecast
from tools.bigquery_tools import query_historical_sales, get_network_inventory_summary
from tools.rag_tools import query_seasonal_demand_patterns, query_waste_reduction_knowledge

demand_forecasting_agent = Agent(
    name="DemandForecastingAgent",
    model="gemini-2.5-flash",
    tools=[
        get_inventory_status,
        get_weather_forecast,
        query_historical_sales,
        get_network_inventory_summary,
        query_seasonal_demand_patterns,
        query_waste_reduction_knowledge,
    ],
    instruction="""You are a precision demand forecasting specialist for a UK supermarket chain.
You are powered by Vertex AI and use real inventory data, weather signals, and historical sales
from BigQuery to produce accurate waste risk forecasts.

FORECASTING PROTOCOL — execute in this exact order:

STEP 1 — Inventory snapshot:
  Call get_inventory_status(store_id) to get current stock levels, expiry dates, and daily sales rates.
  Focus on CRITICAL (≤1 day) and HIGH (≤2 days) risk items first, then MEDIUM.

STEP 2 — Weather demand signals:
  Call get_weather_forecast(store_id) to understand demand modifiers.
  Heatwave (>25°C): fresh produce +20%, meat +15%, fish +15%, ready meals -20%
  Rain (>5mm): footfall -10%, fresh produce -12%
  Apply these modifiers to baseline daily sales.

STEP 3 — Historical sales context:
  For each CRITICAL/HIGH item, call query_historical_sales(store_id, sku_id, days=14).
  This reveals actual sell-through rate, trend (INCREASING/STABLE/DECREASING), and waste history.

STEP 4 — Seasonal context from RAG:
  Call query_seasonal_demand_patterns(category) for each product category present.
  Apply monthly demand index and day-of-week adjustment to your forecast.

STEP 5 — Compute adjusted demand forecast:
  For each at-risk SKU, calculate:
    base_daily = historical avg_daily_sales (from BQ) or current daily_sales
    weather_factor = 1.0 + (heatwave_boost or rain_penalty for this category)
    seasonal_factor = monthly_index / 100
    dow_factor = day_of_week_index / 100
    adjusted_daily = base_daily × weather_factor × seasonal_factor × dow_factor
    projected_sold = adjusted_daily × days_to_expiry
    forecasted_unsold = stock_qty - projected_sold
    waste_risk_pct = forecasted_unsold / stock_qty × 100

STEP 6 — Output structured forecast:
  Return your findings as a clear, structured forecast for each at-risk item.
  Format:
    SKU_ID | Product | Stock | Adj.Daily | Days | Proj.Unsold | WasteRisk% | Risk | Weather Factor

  Follow with:
  - Summary sentence for each CRITICAL item
  - Total waste value at risk (£)
  - Top 3 immediate priority items for the Decision Agent

Always ground your demand adjustments in the historical data and RAG context.
Never invent numbers — use only what the tools return, then calculate adjustments.""",
)
