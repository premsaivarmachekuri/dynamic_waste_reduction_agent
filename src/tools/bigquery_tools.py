"""
bigquery_tools.py — BigQuery-backed ADK tools for inventory, decisions, and analytics.

All functions are designed as ADK FunctionTools (plain Python functions with
descriptive docstrings and type hints). They use BigQuery in production and
fall back to JSON files in DEMO_MODE.
"""

import json
import os
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
_BQ_DATASET  = os.environ.get("BQ_DATASET", "waste_engine")
_DEMO_MODE   = os.environ.get("DEMO_MODE", "true").lower() == "true"
_DATA_PATH   = Path(__file__).parent.parent / "data" / "mock_inventory.json"


def _bq_client():
    """Return a BigQuery client, authenticating via GOOGLE_APPLICATION_CREDENTIALS."""
    from google.cloud import bigquery
    sa_key = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
    )
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", sa_key)
    return bigquery.Client(project=_PROJECT_ID)


def _load_mock() -> dict:
    with open(_DATA_PATH) as f:
        return json.load(f)


def query_historical_sales(store_id: str, sku_id: str, days: int = 30) -> dict:
    """
    Query historical sales data for a SKU/store from BigQuery.

    Args:
        store_id: Store identifier (e.g. 'ST001')
        sku_id: Product SKU identifier (e.g. 'SKU-0001')
        days: Number of historical days to retrieve (default 30)

    Returns:
        Dictionary with sales statistics and trend data.
    """
    if _DEMO_MODE:
        # Synthesize from mock data
        mock = _load_mock()
        item = next(
            (i for i in mock["inventory"] if i["sku_id"] == sku_id and i["store_id"] == store_id),
            None,
        )
        if not item:
            return {"error": f"SKU {sku_id} not found in {store_id}"}

        base_sales = item["daily_sales"]
        import random
        daily_records = []
        for d in range(days, 0, -1):
            noise = random.gauss(1.0, 0.1)
            dow = (date.today() - timedelta(days=d)).weekday()
            dow_factor = {0: 0.9, 1: 0.85, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.35, 6: 1.25}[dow]
            units = max(0, int(base_sales * dow_factor * noise))
            wasted = max(0, int(units * 0.03)) if random.random() < 0.1 else 0
            daily_records.append({
                "date": (date.today() - timedelta(days=d)).isoformat(),
                "units_sold": units,
                "units_wasted": wasted,
                "revenue_gbp": round(units * item["unit_price"], 2),
            })

        total_sold   = sum(r["units_sold"] for r in daily_records)
        total_wasted = sum(r["units_wasted"] for r in daily_records)
        avg_daily    = round(total_sold / days, 1)
        waste_rate   = round(total_wasted / max(total_sold + total_wasted, 1) * 100, 2)

        return {
            "store_id":          store_id,
            "sku_id":            sku_id,
            "product_name":      item["name"],
            "period_days":       days,
            "total_units_sold":  total_sold,
            "total_units_wasted": total_wasted,
            "avg_daily_sales":   avg_daily,
            "waste_rate_pct":    waste_rate,
            "trend": "STABLE",  # simplified
            "daily_records":     daily_records[-7:],  # last 7 days for context
            "source":            "mock_data",
        }

    # BigQuery path
    try:
        client = _bq_client()
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        query = f"""
            SELECT
                sale_date,
                SUM(units_sold)   AS units_sold,
                SUM(units_wasted) AS units_wasted,
                SUM(revenue_gbp)  AS revenue_gbp
            FROM `{_PROJECT_ID}.{_BQ_DATASET}.historical_sales`
            WHERE store_id = @store_id
              AND sku_id   = @sku_id
              AND sale_date >= @cutoff
            GROUP BY sale_date
            ORDER BY sale_date ASC
        """
        from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter
        job_config = QueryJobConfig(query_parameters=[
            ScalarQueryParameter("store_id", "STRING", store_id),
            ScalarQueryParameter("sku_id",   "STRING", sku_id),
            ScalarQueryParameter("cutoff",   "STRING", cutoff),
        ])
        rows = list(client.query(query, job_config=job_config).result())

        if not rows:
            return {"error": "No historical data found", "store_id": store_id, "sku_id": sku_id}

        total_sold   = sum(r["units_sold"]   for r in rows)
        total_wasted = sum(r["units_wasted"] for r in rows)
        avg_daily    = round(total_sold / len(rows), 1) if rows else 0
        waste_rate   = round(total_wasted / max(total_sold + total_wasted, 1) * 100, 2)

        # Simple trend: compare first half vs second half
        mid = len(rows) // 2
        first_avg  = sum(r["units_sold"] for r in rows[:mid]) / max(mid, 1)
        second_avg = sum(r["units_sold"] for r in rows[mid:]) / max(len(rows) - mid, 1)
        trend = "INCREASING" if second_avg > first_avg * 1.05 else (
                "DECREASING" if second_avg < first_avg * 0.95 else "STABLE")

        return {
            "store_id":           store_id,
            "sku_id":             sku_id,
            "period_days":        days,
            "total_units_sold":   total_sold,
            "total_units_wasted": total_wasted,
            "avg_daily_sales":    avg_daily,
            "waste_rate_pct":     waste_rate,
            "trend":              trend,
            "daily_records":      [dict(r) for r in rows[-7:]],
            "source":             "bigquery",
        }
    except Exception as e:
        return {"error": str(e), "store_id": store_id, "sku_id": sku_id}


def get_network_inventory_summary() -> dict:
    """
    Get a high-level inventory waste risk summary across all stores in the network.

    Returns:
        Network-wide summary of at-risk inventory by store and category.
    """
    if _DEMO_MODE:
        mock = _load_mock()
        today = date.today()
        store_summaries = {}

        for item in mock["inventory"]:
            sid = item["store_id"]
            expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
            days = (expiry - today).days
            risk = "CRITICAL" if days <= 1 else "HIGH" if days <= 2 else "MEDIUM" if days <= 3 else "LOW"
            waste_val = max(item["stock_qty"] - item["daily_sales"] * max(days, 0), 0) * item["unit_cost"]

            if sid not in store_summaries:
                store_summaries[sid] = {
                    "store_id": sid,
                    "store_name": next((s["name"] for s in mock["stores"] if s["store_id"] == sid), sid),
                    "critical": 0, "high": 0, "medium": 0, "low": 0,
                    "total_waste_value_gbp": 0.0,
                }
            store_summaries[sid][risk.lower()] += 1
            store_summaries[sid]["total_waste_value_gbp"] += waste_val

        stores = list(store_summaries.values())
        for s in stores:
            s["total_waste_value_gbp"] = round(s["total_waste_value_gbp"], 2)

        total_waste = sum(s["total_waste_value_gbp"] for s in stores)
        return {
            "as_of": date.today().isoformat(),
            "network_total_waste_risk_gbp": round(total_waste, 2),
            "stores": sorted(stores, key=lambda x: -x["total_waste_value_gbp"]),
            "source": "mock_data",
        }

    try:
        client = _bq_client()
        today = date.today().isoformat()
        query = f"""
            SELECT
                store_id,
                CASE
                    WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 1 THEN 'CRITICAL'
                    WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 2 THEN 'HIGH'
                    WHEN DATE_DIFF(expiry_date, CURRENT_DATE(), DAY) <= 3 THEN 'MEDIUM'
                    ELSE 'LOW'
                END AS risk_level,
                COUNT(*)                                                       AS sku_count,
                SUM(GREATEST(stock_qty - daily_sales * GREATEST(
                    DATE_DIFF(expiry_date, CURRENT_DATE(), DAY), 0), 0) * unit_cost) AS waste_value_gbp
            FROM `{_PROJECT_ID}.{_BQ_DATASET}.inventory`
            GROUP BY store_id, risk_level
            ORDER BY store_id, risk_level
        """
        rows = list(client.query(query).result())

        store_map = {}
        for row in rows:
            sid = row["store_id"]
            if sid not in store_map:
                store_map[sid] = {"store_id": sid, "critical": 0, "high": 0, "medium": 0, "low": 0, "total_waste_value_gbp": 0.0}
            store_map[sid][row["risk_level"].lower()] = row["sku_count"]
            store_map[sid]["total_waste_value_gbp"] += float(row["waste_value_gbp"] or 0)

        stores = list(store_map.values())
        for s in stores:
            s["total_waste_value_gbp"] = round(s["total_waste_value_gbp"], 2)

        total_waste = sum(s["total_waste_value_gbp"] for s in stores)
        return {
            "as_of": today,
            "network_total_waste_risk_gbp": round(total_waste, 2),
            "stores": sorted(stores, key=lambda x: -x["total_waste_value_gbp"]),
            "source": "bigquery",
        }
    except Exception as e:
        return {"error": str(e)}


def log_decision_to_bigquery(
    sku_id: str,
    store_id: str,
    action_type: str,
    action_detail: str,
    units_affected: int,
    expected_saving_gbp: float,
    reasoning: str,
    agent_name: str = "WasteReductionOrchestrator",
    risk_level: str = "HIGH",
    gross_margin_pct: float = 0.0,
    rag_context: str = "",
) -> dict:
    """
    Persist an AI waste reduction decision to BigQuery decisions_log table.

    Args:
        sku_id: SKU that the action applies to
        store_id: Store where action is taken
        action_type: DISCOUNT, TRANSFER, LOYALTY_COUPON, DONATE, or MONITOR
        action_detail: Human-readable description of the action taken
        units_affected: Number of units covered by this action
        expected_saving_gbp: Estimated pound saving from waste reduction
        reasoning: Agent reasoning narrative for this decision
        agent_name: Name of the agent making the decision
        risk_level: CRITICAL, HIGH, MEDIUM, or LOW
        gross_margin_pct: Gross margin percentage at time of decision
        rag_context: RAG context snippets used in the decision

    Returns:
        Confirmation dict with decision_id.
    """
    decision_id = str(uuid.uuid4())[:8].upper()
    timestamp   = datetime.utcnow().isoformat() + "Z"
    weight_kg   = 0.4  # average weight per unit
    kg_saved    = round(units_affected * weight_kg, 2)
    co2_avoided = round(kg_saved * 3.3, 2)

    decision = {
        "decision_id":         decision_id,
        "timestamp":           timestamp,
        "sku_id":              sku_id,
        "store_id":            store_id,
        "action_type":         action_type,
        "action_detail":       action_detail,
        "units_affected":      units_affected,
        "expected_saving_gbp": round(expected_saving_gbp, 2),
        "actual_saving_gbp":   None,
        "reasoning":           reasoning,
        "rag_context":         rag_context[:1000] if rag_context else "",
        "agent_name":          agent_name,
        "status":              "EXECUTED",
        "risk_level":          risk_level,
        "gross_margin_pct":    round(gross_margin_pct, 1),
        "co2_avoided_kg":      co2_avoided,
        "kg_food_saved":       kg_saved,
    }

    # Always write to local file (audit trail + fallback)
    _persist_decision_to_file(decision)

    if not _DEMO_MODE:
        try:
            client = _bq_client()
            table_id = f"{_PROJECT_ID}.{_BQ_DATASET}.decisions_log"
            errors = client.insert_rows_json(table_id, [decision])
            if errors:
                print(f"[BQ] Decision insert error: {errors}")
                return {"status": "PARTIAL", "decision": decision, "bq_errors": errors}
        except Exception as e:
            print(f"[BQ] Decision log error (file fallback used): {e}")

    return {"status": "SUCCESS", "decision": decision}


def _persist_decision_to_file(decision: dict) -> None:
    """Persist decision to local JSON file (always, as audit trail)."""
    log_path = Path(__file__).parent.parent / "data" / "decisions_log.json"
    existing = []
    if log_path.exists():
        with open(log_path) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(decision)
    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)


def get_decisions_summary(store_id: Optional[str] = None, days: int = 7) -> dict:
    """
    Get a summary of AI decisions over the last N days.

    Args:
        store_id: Filter to specific store, or None for all stores
        days: Number of days to look back (default 7)

    Returns:
        Summary with counts, total savings, and ESG metrics.
    """
    if _DEMO_MODE or True:  # always use file in demo
        log_path = Path(__file__).parent.parent / "data" / "decisions_log.json"
        decisions = []
        if log_path.exists():
            with open(log_path) as f:
                try:
                    decisions = json.load(f)
                except json.JSONDecodeError:
                    decisions = []

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        if store_id:
            decisions = [d for d in decisions if d.get("store_id") == store_id]
        decisions = [d for d in decisions if d.get("timestamp", "") >= cutoff]

        total_saving  = sum(d.get("expected_saving_gbp", 0) for d in decisions)
        total_units   = sum(d.get("units_affected", 0) for d in decisions)
        kg_saved      = round(total_units * 0.4, 2)
        co2_avoided   = round(kg_saved * 3.3, 2)
        meals_equiv   = int(kg_saved / 0.3)

        action_counts = {}
        for d in decisions:
            at = d.get("action_type", "UNKNOWN")
            action_counts[at] = action_counts.get(at, 0) + 1

        return {
            "store_id":            store_id or "ALL",
            "period_days":         days,
            "total_decisions":     len(decisions),
            "action_breakdown":    action_counts,
            "total_saving_gbp":    round(total_saving, 2),
            "total_units_saved":   total_units,
            "kg_food_saved":       kg_saved,
            "co2_avoided_kg":      co2_avoided,
            "meals_equivalent":    meals_equiv,
            "trees_equivalent":    round(co2_avoided / 21, 1),
        }
