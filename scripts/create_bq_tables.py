#!/usr/bin/env python3
"""
create_bq_tables.py — Create all BigQuery tables for the Waste Reduction Engine.
Idempotent: skips tables that already exist.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(override=True)

from google.cloud import bigquery
from google.cloud.bigquery import Table, Dataset
from google.api_core.exceptions import Conflict

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267")
BQ_DATASET  = os.environ.get("BQ_DATASET", "waste_engine")
SA_KEY_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    str(Path(__file__).parent.parent / "tcs-1770741130267-a4a73ebadced.json"),
)
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", SA_KEY_FILE)

from infra.bigquery_schema import TABLE_REGISTRY


def main():
    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = f"{PROJECT_ID}.{BQ_DATASET}"

    # Ensure dataset exists
    try:
        dataset = Dataset(dataset_ref)
        dataset.location = "US"
        dataset.description = "Dynamic Waste Reduction Engine — AI perishable optimization"
        client.create_dataset(dataset, exists_ok=True)
        print(f"[BQ] Dataset {dataset_ref} ready.")
    except Exception as e:
        print(f"[BQ] Dataset error: {e}")
        raise

    # Create each table
    for table_name, config in TABLE_REGISTRY.items():
        table_id = f"{dataset_ref}.{table_name}"
        table = Table(table_id, schema=config["schema"])

        if config.get("partitioning"):
            table.time_partitioning = config["partitioning"]

        if config.get("clustering_fields"):
            table.clustering_fields = config["clustering_fields"]

        if config.get("description"):
            table.description = config["description"]

        try:
            client.create_table(table)
            print(f"[BQ] Created table: {table_id}")
        except Conflict:
            print(f"[BQ] Table already exists (skipping): {table_id}")
        except Exception as e:
            print(f"[BQ] Error creating {table_id}: {e}")
            raise

    print("\n[BQ] All tables ready.")


if __name__ == "__main__":
    main()
