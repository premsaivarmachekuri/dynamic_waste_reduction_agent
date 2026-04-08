"""
bigquery_schema.py — BigQuery table schemas for the Waste Reduction Engine.

Tables:
  inventory          — Live SKU stock levels and expiry data
  historical_sales   — 90-day rolling sales history per SKU/store
  decisions_log      — All AI decisions with reasoning and outcomes
  transfers          — Inter-store transfer records
  waste_events       — Actual waste recorded (ground truth for model training)
  rag_corpus_meta    — RAG document metadata and embedding status
"""

from google.cloud.bigquery import SchemaField, TimePartitioning, TimePartitioningType

# ── inventory ──────────────────────────────────────────────────────────────────
INVENTORY_SCHEMA = [
    SchemaField("sku_id",           "STRING",    mode="REQUIRED", description="SKU identifier"),
    SchemaField("store_id",         "STRING",    mode="REQUIRED", description="Store identifier"),
    SchemaField("batch_id",         "STRING",    mode="REQUIRED", description="Batch/lot identifier"),
    SchemaField("name",             "STRING",    mode="REQUIRED", description="Product display name"),
    SchemaField("category",         "STRING",    mode="REQUIRED", description="Product category"),
    SchemaField("expiry_date",      "DATE",      mode="REQUIRED", description="Best-before / use-by date"),
    SchemaField("stock_qty",        "INTEGER",   mode="REQUIRED", description="Current stock units"),
    SchemaField("daily_sales",      "FLOAT",     mode="REQUIRED", description="Average daily sales rate"),
    SchemaField("unit_price",       "FLOAT",     mode="REQUIRED", description="Retail price (GBP)"),
    SchemaField("unit_cost",        "FLOAT",     mode="REQUIRED", description="Cost of goods (GBP)"),
    SchemaField("weight_kg",        "FLOAT",     mode="REQUIRED", description="Weight per unit (kg)"),
    SchemaField("supplier_id",      "STRING",    mode="NULLABLE", description="Supplier reference"),
    SchemaField("last_updated",     "TIMESTAMP", mode="REQUIRED", description="Record last modified"),
    SchemaField("source",           "STRING",    mode="NULLABLE", description="Data source: pos/manual/import"),
]

# ── historical_sales ───────────────────────────────────────────────────────────
HISTORICAL_SALES_SCHEMA = [
    SchemaField("sale_date",        "DATE",      mode="REQUIRED", description="Sale date"),
    SchemaField("sku_id",           "STRING",    mode="REQUIRED", description="SKU identifier"),
    SchemaField("store_id",         "STRING",    mode="REQUIRED", description="Store identifier"),
    SchemaField("units_sold",       "INTEGER",   mode="REQUIRED", description="Units sold that day"),
    SchemaField("units_wasted",     "INTEGER",   mode="REQUIRED", description="Units wasted/written off"),
    SchemaField("revenue_gbp",      "FLOAT",     mode="NULLABLE", description="Gross revenue (GBP)"),
    SchemaField("discount_applied", "FLOAT",     mode="NULLABLE", description="Discount % applied (0-100)"),
    SchemaField("weather_temp_max", "FLOAT",     mode="NULLABLE", description="Max temperature that day"),
    SchemaField("weather_rain_mm",  "FLOAT",     mode="NULLABLE", description="Rainfall mm that day"),
    SchemaField("is_promotion",     "BOOLEAN",   mode="NULLABLE", description="Promotion active flag"),
    SchemaField("loaded_at",        "TIMESTAMP", mode="REQUIRED", description="ETL load timestamp"),
]

# ── decisions_log ──────────────────────────────────────────────────────────────
DECISIONS_LOG_SCHEMA = [
    SchemaField("decision_id",          "STRING",    mode="REQUIRED", description="Unique decision ID"),
    SchemaField("timestamp",            "TIMESTAMP", mode="REQUIRED", description="Decision timestamp (UTC)"),
    SchemaField("sku_id",               "STRING",    mode="REQUIRED", description="SKU acted upon"),
    SchemaField("store_id",             "STRING",    mode="REQUIRED", description="Store where action applies"),
    SchemaField("action_type",          "STRING",    mode="REQUIRED", description="DISCOUNT|TRANSFER|LOYALTY_COUPON|DONATE|MONITOR"),
    SchemaField("action_detail",        "STRING",    mode="REQUIRED", description="Human-readable action description"),
    SchemaField("units_affected",       "INTEGER",   mode="REQUIRED", description="Number of units covered"),
    SchemaField("expected_saving_gbp",  "FLOAT",     mode="REQUIRED", description="Predicted waste saving (GBP)"),
    SchemaField("actual_saving_gbp",    "FLOAT",     mode="NULLABLE", description="Actual saving (filled after outcome)"),
    SchemaField("reasoning",            "STRING",    mode="REQUIRED", description="Agent reasoning narrative"),
    SchemaField("rag_context",          "STRING",    mode="NULLABLE", description="RAG snippets used in reasoning"),
    SchemaField("agent_name",           "STRING",    mode="NULLABLE", description="Agent that made the decision"),
    SchemaField("status",               "STRING",    mode="REQUIRED", description="EXECUTED|PENDING|CANCELLED|COMPLETED"),
    SchemaField("risk_level",           "STRING",    mode="NULLABLE", description="CRITICAL|HIGH|MEDIUM|LOW"),
    SchemaField("gross_margin_pct",     "FLOAT",     mode="NULLABLE", description="Gross margin at decision time"),
    SchemaField("co2_avoided_kg",       "FLOAT",     mode="NULLABLE", description="CO2 equivalent avoided (kg)"),
    SchemaField("kg_food_saved",        "FLOAT",     mode="NULLABLE", description="Food mass saved (kg)"),
]

# ── transfers ──────────────────────────────────────────────────────────────────
TRANSFERS_SCHEMA = [
    SchemaField("transfer_id",          "STRING",    mode="REQUIRED", description="Unique transfer ID"),
    SchemaField("created_at",           "TIMESTAMP", mode="REQUIRED", description="Creation timestamp"),
    SchemaField("from_store_id",        "STRING",    mode="REQUIRED", description="Source store"),
    SchemaField("from_store_name",      "STRING",    mode="REQUIRED", description="Source store name"),
    SchemaField("to_store_id",          "STRING",    mode="REQUIRED", description="Destination store"),
    SchemaField("to_store_name",        "STRING",    mode="REQUIRED", description="Destination store name"),
    SchemaField("sku_id",               "STRING",    mode="REQUIRED", description="SKU being transferred"),
    SchemaField("product_name",         "STRING",    mode="REQUIRED", description="Product name"),
    SchemaField("units",                "INTEGER",   mode="REQUIRED", description="Units transferred"),
    SchemaField("expected_saving_gbp",  "FLOAT",     mode="REQUIRED", description="Expected waste saving (GBP)"),
    SchemaField("logistics_cost_gbp",   "FLOAT",     mode="NULLABLE", description="Logistics cost (GBP)"),
    SchemaField("decision_id",          "STRING",    mode="NULLABLE", description="Linked decision ID"),
    SchemaField("status",               "STRING",    mode="REQUIRED", description="PENDING|ACCEPTED|IN_TRANSIT|COMPLETED|REJECTED"),
    SchemaField("actioned_at",          "TIMESTAMP", mode="NULLABLE", description="When receiving store actioned"),
    SchemaField("notes",                "STRING",    mode="NULLABLE", description="Free-text notes"),
]

# ── waste_events ───────────────────────────────────────────────────────────────
WASTE_EVENTS_SCHEMA = [
    SchemaField("event_id",        "STRING",    mode="REQUIRED", description="Unique waste event ID"),
    SchemaField("recorded_at",     "TIMESTAMP", mode="REQUIRED", description="When waste was recorded"),
    SchemaField("store_id",        "STRING",    mode="REQUIRED", description="Store"),
    SchemaField("sku_id",          "STRING",    mode="REQUIRED", description="SKU written off"),
    SchemaField("batch_id",        "STRING",    mode="NULLABLE", description="Batch reference"),
    SchemaField("units_wasted",    "INTEGER",   mode="REQUIRED", description="Units written off"),
    SchemaField("waste_value_gbp", "FLOAT",     mode="REQUIRED", description="Cost of wasted stock (GBP)"),
    SchemaField("waste_kg",        "FLOAT",     mode="REQUIRED", description="Weight wasted (kg)"),
    SchemaField("co2_kg",          "FLOAT",     mode="NULLABLE", description="CO2 equivalent (kg)"),
    SchemaField("reason",          "STRING",    mode="NULLABLE", description="Expiry|Damage|Overstock|Other"),
    SchemaField("decision_id",     "STRING",    mode="NULLABLE", description="AI decision that attempted to prevent this"),
]

# ── Partitioning configs ───────────────────────────────────────────────────────
DECISIONS_PARTITIONING = TimePartitioning(
    type_=TimePartitioningType.DAY,
    field="timestamp",
)

HISTORICAL_SALES_PARTITIONING = TimePartitioning(
    type_=TimePartitioningType.DAY,
    field="sale_date",
)

WASTE_EVENTS_PARTITIONING = TimePartitioning(
    type_=TimePartitioningType.DAY,
    field="recorded_at",
)

# ── Table registry for programmatic access ─────────────────────────────────────
TABLE_REGISTRY = {
    "inventory": {
        "schema": INVENTORY_SCHEMA,
        "partitioning": None,
        "clustering_fields": ["store_id", "category"],
        "description": "Live perishable inventory — refreshed hourly from POS",
    },
    "historical_sales": {
        "schema": HISTORICAL_SALES_SCHEMA,
        "partitioning": HISTORICAL_SALES_PARTITIONING,
        "clustering_fields": ["store_id", "sku_id"],
        "description": "90-day rolling sales history used for demand forecasting",
    },
    "decisions_log": {
        "schema": DECISIONS_LOG_SCHEMA,
        "partitioning": DECISIONS_PARTITIONING,
        "clustering_fields": ["store_id", "action_type"],
        "description": "All AI decisions with full reasoning and ESG impact",
    },
    "transfers": {
        "schema": TRANSFERS_SCHEMA,
        "partitioning": None,
        "clustering_fields": ["from_store_id", "to_store_id"],
        "description": "Inter-store transfer records",
    },
    "waste_events": {
        "schema": WASTE_EVENTS_SCHEMA,
        "partitioning": WASTE_EVENTS_PARTITIONING,
        "clustering_fields": ["store_id"],
        "description": "Actual waste events — ground truth for model evaluation",
    },
}
