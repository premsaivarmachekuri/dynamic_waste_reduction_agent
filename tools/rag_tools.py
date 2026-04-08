"""
rag_tools.py — ADK FunctionTools that query the Vertex AI RAG corpus
for domain knowledge to ground agent decisions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import (
    retrieve_context,
    retrieve_waste_strategy,
    retrieve_pricing_strategy,
    retrieve_esg_benchmarks,
    retrieve_logistics_guidance,
    retrieve_seasonal_context,
    retrieve_food_safety_rules,
)


def query_waste_reduction_knowledge(query: str, top_k: int = 5) -> str:
    """
    Query the RAG knowledge base for waste reduction strategies and best practices.

    Use this tool to get domain knowledge on:
    - Optimal discount levels by product category and days-to-expiry
    - Transfer vs discount decision criteria
    - Donation guidelines
    - Network-level optimization strategies

    Args:
        query: The question or context needed (e.g. "optimal action for chicken breast expiring tomorrow")
        top_k: Number of context chunks to retrieve (default 5)

    Returns:
        Relevant domain knowledge text from the knowledge base.
    """
    return retrieve_context(query, top_k=top_k)


def query_price_elasticity_data(product_category: str, discount_scenario: str) -> str:
    """
    Retrieve price elasticity coefficients and demand response data for a product category.

    Use this to understand how demand will respond to different discount levels.
    Essential input for accurate P&L simulation.

    Args:
        product_category: Category name (e.g. "Meat & Poultry", "Fish & Seafood", "Dairy")
        discount_scenario: Description of discount being considered (e.g. "30% discount on chicken breast")

    Returns:
        Price elasticity data and expected demand uplift percentages.
    """
    return retrieve_pricing_strategy(product_category, discount_scenario)


def query_esg_calculation_standards(metric_type: str) -> str:
    """
    Retrieve ESG metric calculation standards and emission factors.

    Use this to accurately calculate CO2 avoided, meals equivalent, and social value
    for reporting and decision justification.

    Args:
        metric_type: The metric to look up (e.g. "CO2 emission factors", "waste value social impact",
                     "WRAP Courtauld targets", "food saved meals equivalent")

    Returns:
        ESG calculation methodology and benchmark values.
    """
    return retrieve_esg_benchmarks(metric_type)


def query_transfer_logistics_rules(from_store: str, to_store: str, product_category: str) -> str:
    """
    Retrieve logistics guidance for inter-store product transfers.

    Provides cold chain requirements, cost per unit, viability thresholds,
    and compliance rules for safe food transfer.

    Args:
        from_store: Source store name or ID (e.g. "ST001", "Metro Central London")
        to_store: Destination store name or ID (e.g. "ST002", "West End Express Birmingham")
        product_category: Product category being transferred (e.g. "Fish & Seafood", "Meat & Poultry")

    Returns:
        Logistics guidance including max distance, transit time, and cost structure.
    """
    return retrieve_logistics_guidance(from_store, to_store, product_category)


def query_seasonal_demand_patterns(product_category: str) -> str:
    """
    Retrieve seasonal and day-of-week demand patterns for a product category.

    Essential for accurate demand forecasting and understanding whether
    current inventory levels are normal or elevated given the time of year.

    Args:
        product_category: Category name (e.g. "Produce", "Bakery", "Ready Meals")

    Returns:
        Monthly demand indices, day-of-week patterns, and event uplift data.
    """
    return retrieve_seasonal_context(product_category)


def query_food_safety_compliance(product_category: str, action_type: str) -> str:
    """
    Retrieve food safety and regulatory compliance rules for a given action.

    ALWAYS call this before recommending discounts, transfers, or donations
    to ensure the recommended action is legally compliant.

    Args:
        product_category: Product category (e.g. "Fish & Seafood", "Dairy", "Meat & Poultry")
        action_type: Planned action (e.g. "DISCOUNT", "TRANSFER", "DONATE")

    Returns:
        Relevant food safety regulations and compliance requirements.
    """
    return retrieve_food_safety_rules(product_category, action_type)


def explain_decision_with_rag_context(
    sku_id: str,
    product_name: str,
    action_taken: str,
    key_factors: str,
) -> str:
    """
    Generate a RAG-grounded explanation for an AI decision.

    Retrieves relevant domain knowledge to provide a detailed, evidence-based
    explanation of why a particular waste reduction action was chosen.
    Used by the Explanation Agent to produce board-level narrative.

    Args:
        sku_id: The SKU that was actioned
        product_name: Human-readable product name
        action_taken: The action chosen (e.g. "30% discount", "transfer to ST003")
        key_factors: Key decision factors (e.g. "1 day to expiry, heatwave, margin 32%")

    Returns:
        Evidence-based explanation grounded in domain knowledge.
    """
    query = (
        f"Why would a supermarket apply {action_taken} to {product_name}? "
        f"Factors: {key_factors}. "
        f"Provide evidence from waste reduction best practices, pricing elasticity, "
        f"and ESG impact standards."
    )
    context = retrieve_context(query, top_k=4)
    return (
        f"Decision: {action_taken} for {product_name} (SKU: {sku_id})\n"
        f"Key factors: {key_factors}\n\n"
        f"Knowledge base context:\n{context}"
    )
