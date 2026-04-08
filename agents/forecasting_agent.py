"""
Forecasting Agent — predicts waste risk for a store's perishables
using inventory status + weather forecast data.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from tools.inventory_tools import get_inventory_status, get_transfer_options
from tools.weather_tools import get_weather_forecast

forecasting_agent = Agent(
    name="WasteForecaster",
    model="gemini-2.5-flash",
    tools=[get_inventory_status, get_weather_forecast, get_transfer_options],
    instruction="""You are an expert demand forecasting specialist for a major UK supermarket chain.

Your role:
1. Call get_inventory_status for the given store to retrieve current stock levels and expiry risk.
2. Call get_weather_forecast for the same store to understand upcoming demand modifiers.
3. Based on the combined data, produce a precise waste risk forecast for each HIGH or CRITICAL batch.

For each at-risk batch, output:
- SKU ID and product name
- Current stock, daily sales rate, days to expiry
- Projected unsold units in 48 hours
- Risk level (CRITICAL/HIGH/MEDIUM/LOW)
- Weather impact on demand
- Recommended immediate action type (DISCOUNT / TRANSFER / COUPON / MONITOR)

Be specific with numbers. Format your response as structured JSON-style output that the Decision Agent can parse.
Do NOT make up data — use only what the tools return.
Always prioritise CRITICAL items (≤1 day to expiry) first.""",
)
