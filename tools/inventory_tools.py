"""
inventory_tools.py — ADK FunctionTools for inventory status, transfer options, and decision logging.

Production: reads from BigQuery, writes to BigQuery + local file audit trail.
Demo/offline: reads from mock_inventory.json.
"""

import json
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

_DATA_PATH = Path(__file__).parent.parent / "data" / "mock_inventory.json"
_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
_BQ_DATASET  = os.environ.get("BQ_DATASET", "waste_engine")
_DEMO_MODE   = os.environ.get("DEMO_MODE", "true").lower() == "true"


def _load_data() -> dict:
    with open(_DATA_PATH) as f:
        return json.load(f)


def _bq_client():
    from google.cloud import bigquery
    sa_key = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
    )
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", sa_key)
    return bigquery.Client(project=_PROJECT_ID)


def get_inventory_status(store_id: str, category: Optional[str] = None) -> dict:
    """
    Return current stock levels and expiry risk for a given store.

    Reads from BigQuery in production, falls back to mock JSON in demo mode.
    Results include waste risk scoring, projected unsold units, and value at risk.

    Args:
        store_id: Store identifier (e.g. 'ST001')
        category: Optional category filter (e.g. 'Meat & Poultry', 'Dairy', 'Bakery',
                  'Produce', 'Ready Meals', 'Fish & Seafood')

    Returns:
        Dictionary with at-risk batches, summary statistics, and risk breakdown.
    """
    today = date.today()

    # Try BigQuery first if not in demo mode
    if not _DEMO_MODE:
        try:
            return _get_inventory_from_bq(store_id, category, today)
        except Exception as e:
            print(f"[INV] BQ query failed ({e}), using mock data.")

    # JSON fallback
    return _get_inventory_from_json(store_id, category, today)


def _get_inventory_from_json(store_id: str, category: Optional[str], today: date) -> dict:
    """Read inventory from local JSON file with risk scoring."""
    data = _load_data()
    items = [i for i in data["inventory"] if i["store_id"] == store_id]
    if category:
        items = [i for i in items if i["category"] == category]

    at_risk = []
    for item in items:
        expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
        days_to_expiry = (expiry - today).days
        projected_unsold = item["stock_qty"] - (item["daily_sales"] * max(days_to_expiry, 0))
        waste_risk_pct = round(
            max(projected_unsold / item["stock_qty"], 0) * 100, 1
        ) if item["stock_qty"] > 0 else 0
        risk_level = (
            "CRITICAL" if days_to_expiry <= 1
            else "HIGH"    if days_to_expiry <= 2
            else "MEDIUM"  if days_to_expiry <= 3
            else "LOW"
        )
        at_risk.append({
            **item,
            "days_to_expiry":          days_to_expiry,
            "projected_unsold_units":  max(int(projected_unsold), 0),
            "waste_risk_pct":          waste_risk_pct,
            "risk_level":              risk_level,
            "potential_waste_value_gbp": round(max(projected_unsold, 0) * item["unit_cost"], 2),
        })

    at_risk_sorted = sorted(at_risk, key=lambda x: (x["days_to_expiry"], -x["waste_risk_pct"]))
    store_name = next((s["name"] for s in data["stores"] if s["store_id"] == store_id), store_id)
    total_waste_value = sum(i["potential_waste_value_gbp"] for i in at_risk_sorted)
    critical_count    = sum(1 for i in at_risk_sorted if i["risk_level"] in ("CRITICAL", "HIGH"))

    return {
        "store_id":              store_id,
        "store_name":            store_name,
        "query_date":            today.isoformat(),
        "total_skus_checked":    len(at_risk_sorted),
        "critical_high_risk_skus": critical_count,
        "total_potential_waste_gbp": round(total_waste_value, 2),
        "inventory":             at_risk_sorted,
        "source":                "mock_json",
    }


def _get_inventory_from_bq(store_id: str, category: Optional[str], today: date) -> dict:
    """Read inventory from BigQuery with risk scoring in SQL."""
    client = _bq_client()
    cat_filter = "AND category = @category" if category else ""
    query = f"""
        SELECT
            sku_id, store_id, batch_id, name, category,
            expiry_date, stock_qty, daily_sales, unit_price, unit_cost, weight_kg,
            DATE_DIFF(expiry_date, CURRENT_DATE(), DAY)                    AS days_to_expiry,
            GREATEST(stock_qty - daily_sales *
                GREATEST(DATE_DIFF(expiry_date, CURRENT_DATE(), DAY), 0), 0) AS projected_unsold_units,
            CASE
                WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 1 THEN 'CRITICAL'
                WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 2 THEN 'HIGH'
                WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 3 THEN 'MEDIUM'
                ELSE 'LOW'
            END AS risk_level
        FROM `{_PROJECT_ID}.{_BQ_DATASET}.inventory`
        WHERE store_id = @store_id
        {cat_filter}
        ORDER BY days_to_expiry ASC, projected_unsold_units DESC
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
    params = [ScalarQueryParameter("store_id", "STRING", store_id)]
    if category:
        params.append(ScalarQueryParameter("category", "STRING", category))
    cfg = QueryJobConfig(query_parameters=params)

    rows = list(client.query(query, job_config=cfg).result())
    items = []
    for r in rows:
        d = dict(r)
        d["expiry_date"] = d["expiry_date"].isoformat()
        waste_val = float(d["projected_unsold_units"]) * float(d["unit_cost"])
        d["potential_waste_value_gbp"] = round(waste_val, 2)
        d["waste_risk_pct"] = round(
            float(d["projected_unsold_units"]) / max(int(d["stock_qty"]), 1) * 100, 1
        )
        items.append(d)

    total_waste   = sum(i["potential_waste_value_gbp"] for i in items)
    critical_count = sum(1 for i in items if i["risk_level"] in ("CRITICAL", "HIGH"))
    store_names = {
        "ST001": "Metro Central", "ST002": "West End Express",
        "ST003": "Northgate Fresh", "ST004": "Riverside Local", "ST005": "Parkview Large",
    }
    return {
        "store_id":   store_id,
        "store_name": store_names.get(store_id, store_id),
        "query_date": today.isoformat(),
        "total_skus_checked":    len(items),
        "critical_high_risk_skus": critical_count,
        "total_potential_waste_gbp": round(total_waste, 2),
        "inventory": items,
        "source":    "bigquery",
    }


def get_transfer_options(sku_id: str, from_store_id: str) -> dict:
    """
    Find other stores in the network that could absorb excess stock for a given SKU.

    Calculates absorption capacity, logistics cost, and net saving for each
    viable destination store. Results are sorted by net saving (highest first).

    Args:
        sku_id: Product SKU identifier (e.g. 'SKU-0001')
        from_store_id: The store with excess stock (e.g. 'ST001')

    Returns:
        List of viable transfer destinations with capacity, cost, and net saving estimates.
    """
    data = _load_data()
    source = next(
        (i for i in data["inventory"] if i["sku_id"] == sku_id and i["store_id"] == from_store_id),
        None,
    )
    if not source:
        return {"error": f"SKU {sku_id} not found in store {from_store_id}", "transfer_options": []}

    options = []
    for store in data["stores"]:
        if store["store_id"] == from_store_id:
            continue
        similar = next(
            (i for i in data["inventory"]
             if i["name"] == source["name"] and i["store_id"] == store["store_id"]),
            None,
        )
        if similar:
            headroom = max(similar["daily_sales"] * 3 - similar["stock_qty"], 0)
        else:
            cat_items = [
                i for i in data["inventory"]
                if i["category"] == source["category"] and i["store_id"] == store["store_id"]
            ]
            avg_daily = (
                sum(i["daily_sales"] for i in cat_items) / len(cat_items)
                if cat_items else source["daily_sales"] * 0.7
            )
            headroom = int(avg_daily * 2)

        if headroom >= 8:  # minimum economic transfer
            logistics_cost = round(headroom * 0.18, 2)
            net_saving     = round(headroom * source["unit_cost"] - logistics_cost, 2)
            if net_saving > 0:
                options.append({
                    "store_id":                   store["store_id"],
                    "store_name":                 store["name"],
                    "location":                   store["location"],
                    "estimated_absorption_units": int(headroom),
                    "logistics_cost_per_unit_gbp": 0.18,
                    "logistics_cost_total_gbp":   logistics_cost,
                    "net_saving_gbp":              net_saving,
                })

    excess_units = max(source["stock_qty"] - source["daily_sales"] * 2, 0)
    return {
        "sku_id":         sku_id,
        "product_name":   source["name"],
        "category":       source["category"],
        "from_store":     from_store_id,
        "excess_units":   int(excess_units),
        "transfer_options": sorted(options, key=lambda x: -x["net_saving_gbp"]),
    }


def log_decision_to_store(
    sku_id: str,
    store_id: str,
    action_type: str,
    action_detail: str,
    units_affected: int,
    expected_saving_gbp: float,
    reasoning: str,
) -> dict:
    """
    Persist an AI waste reduction decision to the decision log.

    In production, logs to both BigQuery and local file. In demo mode,
    logs to local file only. Every decision receives a unique decision_id.

    Args:
        sku_id: SKU that the action applies to
        store_id: Store where action is taken
        action_type: One of 'DISCOUNT', 'TRANSFER', 'LOYALTY_COUPON', 'DONATE', 'MONITOR'
        action_detail: Human-readable description of the specific action
        units_affected: Number of units the action covers
        expected_saving_gbp: Estimated pound saving from waste reduction
        reasoning: Agent's reasoning for this decision (2-3 sentences)

    Returns:
        Confirmation dict with decision_id and full decision record.
    """
    # Delegate to BigQuery tool (which handles both BQ + file logging)
    from tools.bigquery_tools import log_decision_to_bigquery
    return log_decision_to_bigquery(
        sku_id=sku_id,
        store_id=store_id,
        action_type=action_type,
        action_detail=action_detail,
        units_affected=units_affected,
        expected_saving_gbp=expected_saving_gbp,
        reasoning=reasoning,
    )
