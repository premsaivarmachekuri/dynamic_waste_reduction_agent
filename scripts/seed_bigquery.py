#!/usr/bin/env python3
"""
seed_bigquery.py — Seed BigQuery tables with initial inventory and historical sales data.
Loads data from mock_inventory.json and generates synthetic historical records.
"""
import json
import os
import sys
import random
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

PROJECT_ID  = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
BQ_DATASET  = os.environ.get("BQ_DATASET", "waste_engine")
SA_KEY_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
)
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", SA_KEY_FILE)

from google.cloud import bigquery

DATA_PATH = Path(__file__).parent.parent / "data" / "mock_inventory.json"


def load_mock_data() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def seed_inventory(client: bigquery.Client, data: dict) -> None:
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.inventory"
    now = datetime.utcnow().isoformat()

    rows = []
    for item in data["inventory"]:
        rows.append({
            "sku_id":       item["sku_id"],
            "store_id":     item["store_id"],
            "batch_id":     item["batch_id"],
            "name":         item["name"],
            "category":     item["category"],
            "expiry_date":  item["expiry_date"],
            "stock_qty":    item["stock_qty"],
            "daily_sales":  float(item["daily_sales"]),
            "unit_price":   float(item["unit_price"]),
            "unit_cost":    float(item["unit_cost"]),
            "weight_kg":    float(item["weight_kg"]),
            "supplier_id":  f"SUP-{item['category'][:3].upper()}",
            "last_updated": now,
            "source":       "seed_script",
        })

    errors = client.insert_rows_json(table_id, rows)
    if errors:
        print(f"[BQ SEED] Inventory errors: {errors}")
    else:
        print(f"[BQ SEED] Inserted {len(rows)} inventory rows.")


def seed_historical_sales(client: bigquery.Client, data: dict) -> None:
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.historical_sales"
    now = datetime.utcnow().isoformat()
    today = date.today()

    rows = []
    for item in data["inventory"]:
        # Generate 90 days of synthetic historical sales
        for days_ago in range(90, 0, -1):
            sale_date = today - timedelta(days=days_ago)
            base_sales = item["daily_sales"]

            # Add day-of-week variation
            dow_factor = {0: 0.9, 1: 0.85, 2: 0.95, 3: 1.0, 4: 1.15, 5: 1.35, 6: 1.25}
            dow = sale_date.weekday()
            seasonal = dow_factor.get(dow, 1.0)

            # Add random noise
            noise = random.gauss(1.0, 0.12)
            units_sold = max(0, int(base_sales * seasonal * noise))

            # Simulate occasional waste
            waste_prob = 0.05 if days_ago > 30 else 0.08
            units_wasted = random.randint(0, 3) if random.random() < waste_prob else 0

            # Weather simulation
            temp_max = random.gauss(16, 6)
            rain_mm  = max(0, random.gauss(2, 4))

            rows.append({
                "sale_date":        sale_date.isoformat(),
                "sku_id":           item["sku_id"],
                "store_id":         item["store_id"],
                "units_sold":       units_sold,
                "units_wasted":     units_wasted,
                "revenue_gbp":      round(units_sold * item["unit_price"], 2),
                "discount_applied": 0.0,
                "weather_temp_max": round(temp_max, 1),
                "weather_rain_mm":  round(rain_mm, 1),
                "is_promotion":     False,
                "loaded_at":        now,
            })

    # Include the mock historical_sales from the file
    for hs in data.get("historical_sales", []):
        rows.append({
            "sale_date":        hs["date"],
            "sku_id":           hs["sku_id"],
            "store_id":         hs["store_id"],
            "units_sold":       hs["units_sold"],
            "units_wasted":     hs["units_wasted"],
            "revenue_gbp":      round(hs["units_sold"] * 4.50, 2),  # approx
            "discount_applied": 0.0,
            "weather_temp_max": None,
            "weather_rain_mm":  None,
            "is_promotion":     False,
            "loaded_at":        now,
        })

    # BQ insert in chunks of 500 (API limit)
    chunk_size = 500
    total_errors = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        errors = client.insert_rows_json(table_id, chunk)
        if errors:
            total_errors += len(errors)

    if total_errors:
        print(f"[BQ SEED] Historical sales: {total_errors} row errors.")
    else:
        print(f"[BQ SEED] Inserted {len(rows)} historical sales rows.")


def seed_sample_decisions(client: bigquery.Client) -> None:
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.decisions_log"
    now = datetime.utcnow()

    sample_decisions = [
        {
            "decision_id":         str(uuid.uuid4())[:8].upper(),
            "timestamp":           (now - timedelta(hours=2)).isoformat() + "Z",
            "sku_id":              "SKU-0001",
            "store_id":            "ST001",
            "action_type":         "DISCOUNT",
            "action_detail":       "Apply 30% discount. Price reduced from £4.50 to £3.15",
            "units_affected":      120,
            "expected_saving_gbp": 48.50,
            "actual_saving_gbp":   None,
            "reasoning":           "CRITICAL: Chicken Breast expires in 1 day. 30% discount boosts demand by 45%. Margin 32.4%.",
            "rag_context":         "Fresh poultry markdown policy: 25-35% on day of expiry to maximise sell-through.",
            "agent_name":          "DecisionOptimizationAgent",
            "status":              "EXECUTED",
            "risk_level":          "CRITICAL",
            "gross_margin_pct":    32.4,
            "co2_avoided_kg":      19.8,
            "kg_food_saved":       60.0,
        },
        {
            "decision_id":         str(uuid.uuid4())[:8].upper(),
            "timestamp":           (now - timedelta(hours=1)).isoformat() + "Z",
            "sku_id":              "SKU-0013",
            "store_id":            "ST002",
            "action_type":         "TRANSFER",
            "action_detail":       "Transfer 20 units Cod Fillet to Metro Central (ST001)",
            "units_affected":      20,
            "expected_saving_gbp": 44.00,
            "actual_saving_gbp":   None,
            "reasoning":           "HIGH risk. ST001 has higher seafood demand (heatwave, +15% uplift). Transfer net saving £44.",
            "rag_context":         "Cross-store transfers for fish optimal within 24h expiry window. logistics £0.18/unit.",
            "agent_name":          "TransferAgent",
            "status":              "EXECUTED",
            "risk_level":          "HIGH",
            "gross_margin_pct":    38.1,
            "co2_avoided_kg":      26.4,
            "kg_food_saved":       8.0,
        },
    ]

    errors = client.insert_rows_json(table_id, sample_decisions)
    if errors:
        print(f"[BQ SEED] Decisions errors: {errors}")
    else:
        print(f"[BQ SEED] Inserted {len(sample_decisions)} sample decisions.")


def main():
    print(f"[BQ SEED] Connecting to BigQuery: {PROJECT_ID}.{BQ_DATASET}")
    client = bigquery.Client(project=PROJECT_ID)
    data = load_mock_data()

    seed_inventory(client, data)
    seed_historical_sales(client, data)
    seed_sample_decisions(client)

    print("\n[BQ SEED] Seeding complete.")


if __name__ == "__main__":
    main()
