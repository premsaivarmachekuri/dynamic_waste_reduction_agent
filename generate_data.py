"""
generate_data.py
----------------
Generates realistic synthetic supermarket data for the Waste Reduction Engine demo.
Run once on Day 1 morning: python generate_data.py
Outputs 4 CSVs to the /data directory.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

random.seed(42)
np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

TODAY = datetime.today().date()

# ─────────────────────────────────────────
# 1. STORES
# ─────────────────────────────────────────
stores = pd.DataFrame([
    {"store_id": "S001", "name": "Central Metro",   "location": "London Central",  "region": "London",    "size": "large"},
    {"store_id": "S002", "name": "East Village",    "location": "London East",     "region": "London",    "size": "medium"},
    {"store_id": "S003", "name": "North Park",      "location": "Manchester North", "region": "Manchester","size": "medium"},
    {"store_id": "S004", "name": "Riverside",       "location": "Bristol South",   "region": "Bristol",   "size": "small"},
    {"store_id": "S005", "name": "Airport Express", "location": "London Heathrow", "region": "London",    "size": "small"},
])
stores.to_csv(f"{DATA_DIR}/stores.csv", index=False)
print(f"✅ stores.csv: {len(stores)} stores")

# ─────────────────────────────────────────
# 2. SKUs
# ─────────────────────────────────────────
sku_data = [
    # Meat
    ("SKU001", "Chicken Breast 500g",       "meat",    3,  4.5,  6.99),
    ("SKU002", "Beef Mince 400g",           "meat",    4,  3.8,  5.49),
    ("SKU003", "Pork Sausages 400g",        "meat",    5,  2.9,  4.29),
    ("SKU004", "Salmon Fillet 300g",        "meat",    3,  5.5,  8.99),
    ("SKU005", "Turkey Slices 200g",        "meat",    5,  2.1,  3.49),
    # Dairy
    ("SKU006", "Whole Milk 2L",             "dairy",   7,  0.9,  1.65),
    ("SKU007", "Greek Yoghurt 500g",        "dairy",   10, 1.2,  2.10),
    ("SKU008", "Cheddar Cheese 400g",       "dairy",   14, 2.8,  4.50),
    ("SKU009", "Butter 250g",               "dairy",   21, 1.5,  2.75),
    ("SKU010", "Double Cream 300ml",        "dairy",   7,  1.8,  2.99),
    # Produce
    ("SKU011", "Baby Spinach 200g",         "produce", 5,  0.8,  1.80),
    ("SKU012", "Mixed Salad Leaves 150g",   "produce", 4,  0.9,  1.60),
    ("SKU013", "Strawberries 400g",         "produce", 4,  1.5,  2.99),
    ("SKU014", "Cherry Tomatoes 300g",      "produce", 6,  1.1,  2.20),
    ("SKU015", "Avocado (2 pack)",          "produce", 5,  1.3,  2.50),
    ("SKU016", "Broccoli Head",             "produce", 7,  0.7,  1.29),
    ("SKU017", "Blueberries 150g",          "produce", 5,  1.8,  3.00),
    # Bakery
    ("SKU018", "Sourdough Loaf",            "bakery",  2,  1.2,  2.80),
    ("SKU019", "Croissants 4 pack",         "bakery",  2,  1.5,  3.20),
    ("SKU020", "Seeded Baguette",           "bakery",  2,  0.8,  1.75),
    ("SKU021", "Cinnamon Swirls 4 pack",    "bakery",  2,  1.8,  3.50),
    ("SKU022", "Whole Wheat Loaf",          "bakery",  3,  1.0,  2.20),
    # Ready Meals
    ("SKU023", "Chicken Tikka Masala",      "ready_meal", 4, 2.5, 4.99),
    ("SKU024", "Mac & Cheese",              "ready_meal", 4, 2.0, 3.99),
    ("SKU025", "Beef Lasagne",              "ready_meal", 5, 2.8, 5.49),
    ("SKU026", "Sushi Selection",           "ready_meal", 2, 4.0, 7.50),
    ("SKU027", "Prawn Stir Fry",            "ready_meal", 3, 3.0, 5.99),
]

skus = pd.DataFrame(sku_data, columns=[
    "sku_id", "name", "category", "shelf_life_days",
    "cost_price", "sell_price"
])
# avg_daily_velocity: estimated units sold per day per store
skus["avg_daily_velocity"] = [
    18, 12, 10, 8,  6,   # meat
    30, 15, 12, 10, 8,   # dairy
    14, 16, 10, 12, 8,   # produce (more)
    9,  7,               # produce (less)
    20, 18, 15, 10, 12,  # bakery
    12, 10, 9,  8,  7,   # ready meals
]
skus.to_csv(f"{DATA_DIR}/skus.csv", index=False)
print(f"✅ skus.csv: {len(skus)} SKUs")

# ─────────────────────────────────────────
# 3. INVENTORY (with batches)
# ─────────────────────────────────────────
WEATHER_TAGS = ["normal", "hot", "cold", "rainy"]

inventory_rows = []
batch_counter = 1

for store in stores["store_id"]:
    for _, sku in skus.iterrows():
        # Each SKU has 1–3 batches per store
        n_batches = random.randint(1, 3)
        for b in range(n_batches):
            days_to_expiry = random.randint(1, sku["shelf_life_days"])
            expiry_date = TODAY + timedelta(days=days_to_expiry)

            # Quantity: lower for near-expiry batches
            if days_to_expiry <= 2:
                quantity = random.randint(5, 40)
                sales_velocity_factor = random.uniform(0.3, 0.7)  # declining
            elif days_to_expiry <= int(sku["shelf_life_days"] * 0.5):
                quantity = random.randint(20, 80)
                sales_velocity_factor = random.uniform(0.6, 1.0)
            else:
                quantity = random.randint(40, 150)
                sales_velocity_factor = random.uniform(0.8, 1.2)

            current_velocity = round(sku["avg_daily_velocity"] * sales_velocity_factor, 1)
            projected_unsold = max(0, quantity - (current_velocity * days_to_expiry))
            waste_risk_score = min(1.0, round(projected_unsold / max(quantity, 1), 2))

            inventory_rows.append({
                "batch_id":            f"B{str(batch_counter).zfill(4)}",
                "store_id":            store,
                "sku_id":              sku["sku_id"],
                "sku_name":            sku["name"],
                "category":            sku["category"],
                "quantity":            quantity,
                "expiry_date":         expiry_date.isoformat(),
                "days_to_expiry":      days_to_expiry,
                "cost_price":          sku["cost_price"],
                "sell_price":          sku["sell_price"],
                "current_velocity":    current_velocity,
                "projected_unsold":    round(projected_unsold, 1),
                "waste_risk_score":    waste_risk_score,
                "weather_tag":         random.choice(WEATHER_TAGS),
            })
            batch_counter += 1

inventory = pd.DataFrame(inventory_rows)
inventory.to_csv(f"{DATA_DIR}/inventory.csv", index=False)
print(f"✅ inventory.csv: {len(inventory)} batch records")

# ─────────────────────────────────────────
# 4. SALES HISTORY (last 30 days)
# ─────────────────────────────────────────
sales_rows = []
for store in stores["store_id"]:
    for _, sku in skus.iterrows():
        for day_offset in range(30):
            date = TODAY - timedelta(days=day_offset)
            weather = random.choice(WEATHER_TAGS)

            # Weather effect on velocity
            weather_multiplier = {
                "hot":    1.3 if sku["category"] in ["produce"] else 0.9,
                "cold":   0.8 if sku["category"] in ["produce"] else 1.1,
                "rainy":  0.9 if sku["category"] in ["bakery", "ready_meal"] else 1.0,
                "normal": 1.0,
            }[weather]

            # Weekend boost
            day_multiplier = 1.3 if date.weekday() >= 5 else 1.0

            base_velocity = sku["avg_daily_velocity"]
            units_sold = max(0, round(
                base_velocity * weather_multiplier * day_multiplier * random.uniform(0.7, 1.3)
            ))

            sales_rows.append({
                "store_id":    store,
                "sku_id":      sku["sku_id"],
                "date":        date.isoformat(),
                "day_of_week": date.strftime("%A"),
                "weather_tag": weather,
                "units_sold":  units_sold,
            })

sales_history = pd.DataFrame(sales_rows)
sales_history.to_csv(f"{DATA_DIR}/sales_history.csv", index=False)
print(f"✅ sales_history.csv: {len(sales_history)} sales records")

print("\n🎯 Hero demo scenario (chicken at Store S001):")
hero = inventory[
    (inventory["store_id"] == "S001") &
    (inventory["sku_id"] == "SKU001")
].sort_values("days_to_expiry")
print(hero[["batch_id","quantity","days_to_expiry","projected_unsold","waste_risk_score"]].to_string(index=False))
print("\n✅ All data generated successfully.")
