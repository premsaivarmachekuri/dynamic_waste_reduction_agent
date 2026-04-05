"""
data_agent.py
-------------
DataAgent: Loads at-risk inventory batches for a given store/SKU.
Uses ADK tool registration pattern.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import load_inventory


def load_inventory_tool(store_id: str = None, sku_id: str = None) -> dict:
    """
    Load at-risk inventory batches from the supermarket data store.
    Filters by store_id and/or sku_id if provided.
    Returns batches with waste_risk_score > 0.3.

    Args:
        store_id: Optional store identifier (e.g. 'S001')
        sku_id: Optional SKU identifier (e.g. 'SKU001')

    Returns:
        dict with total_batches_checked, at_risk_count, and list of batch records
    """
    return load_inventory(store_id=store_id, sku_id=sku_id)


data_agent = Agent(
    name="DataAgent",
    model="gemini-1.5-flash",
    description=(
        "Retrieves at-risk perishable inventory batches from the supermarket data store. "
        "Filters by store and SKU, returns batches sorted by waste risk score."
    ),
    instruction=(
        "You are a data retrieval agent for a supermarket waste reduction system. "
        "When asked about inventory or stock, use the load_inventory_tool to fetch "
        "at-risk batches. Always return the full structured result so the next agent "
        "can process it. Do not summarise — pass the raw data forward."
    ),
    tools=[FunctionTool(func=load_inventory_tool)],
)
