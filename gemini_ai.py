"""
gemini_ai.py — Real Gemini AI integration for the Waste Reduction Engine.

Replaces the rule-based mock analysis with a genuine Gemini 2.0 Flash call
that reasons over live inventory + weather data and returns structured decisions.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(override=True)   # always prefer .env values over stale shell env vars

from google import genai
from google.genai import types

from tools.inventory_tools import get_inventory_status, get_transfer_options, log_decision_to_store
from tools.weather_tools import get_weather_forecast
from tools.pricing_tools import (
    simulate_discount_action,
    simulate_transfer_action,
    simulate_loyalty_coupon,
    calculate_esg_metrics,
)

# ── Client ────────────────────────────────────────────────────────────────────

_API_KEY = os.getenv("GOOGLE_API_KEY")
_MODEL   = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    if not _API_KEY:
        raise EnvironmentError("GOOGLE_API_KEY is not set in .env")
    return genai.Client(api_key=_API_KEY)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_analysis_prompt(store_id: str, inv: dict, weather: dict, simulations: list[dict]) -> str:
    """Build a rich prompt containing all tool data for Gemini to reason over."""

    critical_high = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]

    inv_summary = "\n".join(
        f"  - {i['name']} (SKU {i['sku_id']}): {i['stock_qty']} units, "
        f"expires in {i['days_to_expiry']}d, risk={i['risk_level']}, "
        f"waste value=£{i['potential_waste_value_gbp']:.2f}"
        for i in critical_high
    )

    weather_summary = (
        f"City: {weather['city']}, "
        f"Max temp: {weather['demand_impact']['avg_temp_max']}°C, "
        f"Heatwave: {weather['demand_impact']['heatwave']}, "
        f"Overall demand impact: {weather['demand_impact']['overall']}"
    )

    sims_json = json.dumps(simulations, indent=2)

    return f"""You are an AI waste-reduction decision engine for a UK supermarket chain.

STORE: {store_id}
TODAY'S DATE: {__import__('datetime').date.today()}

=== AT-RISK INVENTORY (CRITICAL & HIGH only) ===
{inv_summary}

=== WEATHER & DEMAND FORECAST ===
{weather_summary}

=== PRE-COMPUTED SIMULATIONS (use these numbers — do NOT invent figures) ===
{sims_json}

=== YOUR TASK ===
For EACH item above, select the single best action (or a combo if synergistic)
based strictly on the simulation results. Decision rules:
- CRITICAL (≤1 day): prefer 30% DISCOUNT + LOYALTY_COUPON if margin ≥ 25%; else DONATE.
- HIGH (2 days): prefer TRANSFER if net_saving_gbp > best discount saving; else 20% DISCOUNT.
- Always protect gross margin ≥ 25%.
- Factor in weather: if heatwave=true, accelerate action urgency.

Return a JSON object with this EXACT structure (no markdown, no commentary outside the JSON):
{{
  "decisions": [
    {{
      "sku_id": "...",
      "product": "...",
      "risk_level": "CRITICAL|HIGH",
      "action": "DISCOUNT|TRANSFER|LOYALTY_COUPON|DONATE",
      "detail": "Human-readable action description",
      "units": <int>,
      "saving_gbp": <float>,
      "kg_saved": <float>,
      "reasoning": "2-3 sentence plain-English explanation of why this action was chosen"
    }}
  ],
  "total_saving_gbp": <float>,
  "total_kg_saved": <float>,
  "co2_avoided_kg": <float>,
  "meals_equivalent": <int>,
  "executive_summary": "3-4 sentence board-level overview of all actions and their combined impact"
}}"""


# ── Simulation runner (pre-computes all options for Gemini to reason over) ────

def _run_simulations(store_id: str, critical_high: list[dict], weather: dict) -> list[dict]:
    """Run all simulation tools for every at-risk item and return raw data."""
    results = []
    for item in critical_high[:5]:  # cap at 5 items for prompt length
        sku_id = item["sku_id"]
        days   = max(item["days_to_expiry"], 0)

        d10 = simulate_discount_action(sku_id, store_id, 10, days)
        d20 = simulate_discount_action(sku_id, store_id, 20, days)
        d30 = simulate_discount_action(sku_id, store_id, 30, days)
        transfers = get_transfer_options(sku_id, store_id)
        coupon = simulate_loyalty_coupon(sku_id, store_id, 15, 500)

        best_transfer = transfers["transfer_options"][0] if transfers["transfer_options"] else None
        transfer_sim = None
        if best_transfer:
            transfer_sim = simulate_transfer_action(
                sku_id, store_id,
                best_transfer["store_id"],
                best_transfer["estimated_absorption_units"],
            )

        results.append({
            "sku_id": sku_id,
            "product": item["name"],
            "risk_level": item["risk_level"],
            "stock_qty": item["stock_qty"],
            "days_to_expiry": days,
            "weight_kg": item.get("weight_kg", 0.5),
            "potential_waste_value_gbp": item["potential_waste_value_gbp"],
            "discount_10pct": {
                "viable": d10["viable"],
                "margin_pct": d10["gross_margin_pct"],
                "waste_saved_gbp": d10["waste_reduction_gbp"],
                "discounted_price": d10["discounted_price_gbp"],
            },
            "discount_20pct": {
                "viable": d20["viable"],
                "margin_pct": d20["gross_margin_pct"],
                "waste_saved_gbp": d20["waste_reduction_gbp"],
                "discounted_price": d20["discounted_price_gbp"],
            },
            "discount_30pct": {
                "viable": d30["viable"],
                "margin_pct": d30["gross_margin_pct"],
                "waste_saved_gbp": d30["waste_reduction_gbp"],
                "discounted_price": d30["discounted_price_gbp"],
            },
            "loyalty_coupon_15pct": {
                "expected_redemptions": coupon["expected_redemptions"],
                "net_benefit_gbp": coupon["net_benefit_gbp"],
            },
            "best_transfer": {
                "store_name": best_transfer["store_name"],
                "units": best_transfer["estimated_absorption_units"],
                "net_saving_gbp": best_transfer["net_saving_gbp"],
                "transfer_sim_viable": transfer_sim["viable"] if transfer_sim else False,
                "transfer_sim_saving_gbp": transfer_sim["net_saving_gbp"] if transfer_sim else 0,
            } if best_transfer else None,
        })
    return results


# ── Main public function ──────────────────────────────────────────────────────

def run_gemini_analysis(store_id: str) -> dict:
    """
    Run a full Gemini-powered waste analysis for the given store.

    Returns a dict compatible with the existing Flask /api/run_analysis response shape.
    Raises on API error so the caller can fall back to mock if desired.
    """
    # 1. Gather live data
    inv     = get_inventory_status(store_id)
    weather = get_weather_forecast(store_id)

    critical_high = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]
    if not critical_high:
        return {
            "decisions": [],
            "total_saving_gbp": 0.0,
            "total_kg_saved": 0.0,
            "co2_avoided_kg": 0.0,
            "meals_equivalent": 0,
            "executive_summary": "No CRITICAL or HIGH risk items found for this store today.",
            "ai_powered": True,
        }

    # 2. Pre-compute all simulations
    simulations = _run_simulations(store_id, critical_high, weather)

    # 3. Build prompt and call Gemini
    prompt = _build_analysis_prompt(store_id, inv, weather, simulations)
    client = _get_client()

    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,                              # low temp for consistent decisions
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(
                thinking_budget=0                         # disable thinking for clean JSON output
            ),
        ),
    )

    raw_text = response.text.strip()

    # Robustly strip markdown fences (```json ... ``` or ``` ... ```)
    if "```" in raw_text:
        # Extract content between the first ``` and the last ```
        inner = raw_text.split("```")[1]          # after opening fence
        if inner.startswith("json"):
            inner = inner[4:]                     # strip "json" language tag
        raw_text = inner.strip()
        # Remove any trailing ``` that may have been left
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    ai_result = json.loads(raw_text)

    # 4. Log every decision to the store's decision log
    sku_map = {i["sku_id"]: i for i in critical_high}
    logged_decisions = []

    for d in ai_result.get("decisions", []):
        sku_id = d["sku_id"]
        item   = sku_map.get(sku_id, {})

        log_result = log_decision_to_store(
            sku_id=sku_id,
            store_id=store_id,
            action_type=d["action"],
            action_detail=d["detail"],
            units_affected=d["units"],
            expected_saving_gbp=d["saving_gbp"],
            reasoning=d["reasoning"],
        )

        logged_decisions.append({
            **d,
            "decision_id": log_result["decision"]["decision_id"],
            "stock": item.get("stock_qty", d["units"]),
        })

    ai_result["decisions"] = logged_decisions
    ai_result["ai_powered"] = True
    return ai_result


# ── Quick CLI test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    store = sys.argv[1] if len(sys.argv) > 1 else "ST001"
    print(f"\n🤖 Running Gemini analysis for store {store}...\n")
    try:
        result = run_gemini_analysis(store)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"❌ Error: {e}")
