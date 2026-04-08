"""
decision_service.py — Decision execution service.

Wraps the Gemini AI analysis with the rule-based fallback,
normalizes output format, and handles the transfer log lifecycle.
"""
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

STORES = {
    "ST001": "Metro Central (London)",
    "ST002": "West End Express (Birmingham)",
    "ST003": "Northgate Fresh (Manchester)",
    "ST004": "Riverside Local (Leeds)",
    "ST005": "Parkview Large (Bristol)",
}


def run_analysis(store_id: str) -> dict:
    """
    Run AI analysis for a store.

    Tries Gemini AI first, falls back to rule-based analysis.
    """
    # Try Gemini AI
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            from gemini_ai import run_gemini_analysis
            result = run_gemini_analysis(store_id)
            result["ai_mode"] = "gemini-2.5-flash"
            return _enrich_decisions(result, store_id)
        except Exception as e:
            result = _run_rule_based(store_id)
            result["ai_mode"] = "rule-based-fallback"
            result["ai_warning"] = str(e)
            return _enrich_decisions(result, store_id)

    # Rule-based fallback
    result = _run_rule_based(store_id)
    result["ai_mode"] = "rule-based-mock"
    return _enrich_decisions(result, store_id)


def _run_rule_based(store_id: str) -> dict:
    """Rule-based waste analysis fallback."""
    from tools.inventory_tools import get_inventory_status, log_decision_to_store, get_transfer_options
    from tools.weather_tools import get_weather_forecast
    from tools.pricing_tools import simulate_discount_action, simulate_loyalty_coupon

    inv = get_inventory_status(store_id)
    weather = get_weather_forecast(store_id)
    weather_impact = weather["demand_impact"]
    time.sleep(0.5)

    critical_high = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM")]
    decisions = []

    for item in critical_high[:5]:
        sku_id = item["sku_id"]
        days   = max(item["days_to_expiry"], 0)

        d20       = simulate_discount_action(sku_id, store_id, 20, days)
        d30       = simulate_discount_action(sku_id, store_id, 30, days)
        transfers = get_transfer_options(sku_id, store_id)
        coupon    = simulate_loyalty_coupon(sku_id, store_id, 15, 500)

        best_transfer = transfers["transfer_options"][0] if transfers["transfer_options"] else None

        if days <= 1:
            if d30["viable"]:
                action        = "DISCOUNT"
                detail        = f"Apply 30% markdown. New price: £{d30['discounted_price_gbp']:.2f}"
                saving        = d30["waste_reduction_gbp"] + coupon["net_benefit_gbp"]
                reasoning     = (
                    f"CRITICAL: {item['name']} expires in {days} day(s). "
                    f"30% discount increases demand by ~45% (elasticity {d30['price_elasticity_used']}). "
                    f"Margin {d30['gross_margin_pct']:.1f}% maintained. Combined with loyalty coupon "
                    f"to maximise sell-through before expiry."
                )
                short_reasoning = f"Expires in {days}d — 30% markdown drives immediate sales before spoilage."
            else:
                action        = "DONATE"
                detail        = f"Donate {item['stock_qty']} units to local food bank"
                saving        = item["potential_waste_value_gbp"] * 0.3
                reasoning     = "Margin too low for any discount. Donation maximises ESG impact and community value."
                short_reasoning = "Margin too thin for pricing — donation maximises community and ESG value."
        elif days <= 2 and best_transfer and best_transfer["net_saving_gbp"] > d20["waste_reduction_gbp"]:
            action        = "TRANSFER"
            detail        = f"Transfer {best_transfer['estimated_absorption_units']} units to {best_transfer['store_name']}"
            saving        = best_transfer["net_saving_gbp"]
            reasoning     = (
                f"HIGH risk: Transfer to {best_transfer['store_name']} yields £{best_transfer['net_saving_gbp']:.2f} net. "
                f"Weather impact: {weather_impact['overall']} — reduced local demand confirms transfer is optimal."
            )
            short_reasoning = f"Local demand is {weather_impact['overall']} — {best_transfer['store_name']} can absorb stock at better margin."
        else:
            if d20["viable"]:
                action        = "DISCOUNT"
                detail        = f"Apply 20% markdown. New price: £{d20['discounted_price_gbp']:.2f}"
                saving        = d20["waste_reduction_gbp"]
                reasoning     = (
                    f"HIGH risk: 20% discount increases daily sales by ~{d20['price_elasticity_used']*20:.0f}%. "
                    f"Margin {d20['gross_margin_pct']:.1f}% is acceptable. "
                    f"{'Heatwave accelerates spoilage urgency.' if weather_impact['heatwave'] else ''}"
                )
                short_reasoning = "20% markdown lifts daily velocity enough to clear stock before expiry."
            else:
                action        = "LOYALTY_COUPON"
                detail        = "Send 15% coupon to 500 loyalty customers"
                saving        = coupon["net_benefit_gbp"]
                reasoning     = "Targeted loyalty coupon activates high-intent customers safely within margin floor."
                short_reasoning = "Targeted loyalty coupon activates high-intent customers to clear stock fast."

        log_result = log_decision_to_store(
            sku_id=sku_id, store_id=store_id, action_type=action,
            action_detail=detail, units_affected=item["stock_qty"],
            expected_saving_gbp=saving, reasoning=reasoning,
        )

        transfer_meta = None
        if action == "TRANSFER" and best_transfer:
            transfer_meta = {
                "to_store_id":   best_transfer["store_id"],
                "to_store_name": best_transfer["store_name"],
                "units":         best_transfer["estimated_absorption_units"],
            }

        decisions.append({
            "product":      item["name"],
            "sku_id":       sku_id,
            "risk_level":   item["risk_level"],
            "action":       action,
            "detail":       detail,
            "units":        item["stock_qty"],
            "saving_gbp":   round(saving, 2),
            "kg_saved":     round(item["stock_qty"] * item["weight_kg"], 2),
            "decision_id":  log_result["decision"]["decision_id"],
            "reasoning":    reasoning,
            "short_reasoning": short_reasoning,
            "stock":        item["stock_qty"],
            "transfer_meta": transfer_meta,
        })

    total_saving = sum(d["saving_gbp"] for d in decisions)
    total_kg     = sum(d["kg_saved"]   for d in decisions)
    return {
        "decisions":        decisions,
        "total_saving_gbp": round(total_saving, 2),
        "total_kg_saved":   round(total_kg, 2),
        "co2_avoided_kg":   round(total_kg * 3.3, 2),
        "meals_equivalent": int(total_kg / 0.3),
    }


def _enrich_decisions(result: dict, store_id: str = None) -> dict:
    """Normalize decisions — ensure short_reasoning and transfer_meta are always present."""
    from tools.inventory_tools import get_transfer_options

    _action_short = {
        "DISCOUNT":      "Markdown drives faster sales to clear stock before expiry.",
        "TRANSFER":      "Sending to a store with higher demand reduces waste risk.",
        "DONATE":        "Margin too thin for pricing — donation maximises ESG value.",
        "LOYALTY_COUPON": "Targeted loyalty offer activates high-intent customers fast.",
    }
    for d in result.get("decisions", []):
        if not d.get("short_reasoning"):
            full = d.get("reasoning", "")
            first_sentence = full.split(".")[0].strip() + "." if full else ""
            d["short_reasoning"] = (
                first_sentence[:120] if len(first_sentence) > 10
                else _action_short.get(d.get("action", ""), "Action recommended to prevent waste.")
            )
        if not d.get("transfer_meta"):
            if d.get("action") == "TRANSFER" and store_id and d.get("sku_id"):
                try:
                    opts = get_transfer_options(d["sku_id"], store_id)
                    best = opts["transfer_options"][0] if opts.get("transfer_options") else None
                    d["transfer_meta"] = {
                        "to_store_id":   best["store_id"],
                        "to_store_name": best["store_name"],
                        "units":         best["estimated_absorption_units"],
                    } if best else None
                except Exception:
                    d["transfer_meta"] = None
            else:
                d["transfer_meta"] = None
    return result


# ── Transfer log management ────────────────────────────────────────────────────

TRANSFERS_PATH = ROOT / "data" / "transfers_log.json"


def load_transfers() -> list:
    if TRANSFERS_PATH.exists():
        with open(TRANSFERS_PATH) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_transfers(records: list) -> None:
    with open(TRANSFERS_PATH, "w") as f:
        json.dump(records, f, indent=2)


def create_transfer(body: dict) -> dict:
    """Create a new inter-store transfer record."""
    required = ["from_store_id", "to_store_id", "sku_id", "product_name", "units"]
    for field in required:
        if field not in body:
            raise ValueError(f"Missing required field: {field}")

    from_id = body["from_store_id"]
    to_id   = body["to_store_id"]

    transfer = {
        "transfer_id":         "TRF-" + str(uuid.uuid4())[:8].upper(),
        "created_at":          datetime.utcnow().isoformat() + "Z",
        "from_store_id":       from_id,
        "from_store_name":     STORES.get(from_id, from_id),
        "to_store_id":         to_id,
        "to_store_name":       STORES.get(to_id, to_id),
        "sku_id":              body["sku_id"],
        "product_name":        body["product_name"],
        "units":               int(body["units"]),
        "expected_saving_gbp": round(float(body.get("expected_saving_gbp", 0)), 2),
        "decision_id":         body.get("decision_id", ""),
        "status":              "PENDING",
        "notes":               body.get("notes", "AI-initiated transfer to prevent waste"),
    }

    records = load_transfers()
    records.append(transfer)
    save_transfers(records)
    return transfer


def update_transfer_status(transfer_id: str, new_status: str) -> dict:
    """Update a transfer's status (ACCEPTED, REJECTED, COMPLETED, etc.)."""
    records = load_transfers()
    matched = None
    for t in records:
        if t["transfer_id"] == transfer_id:
            t["status"]      = new_status
            t["actioned_at"] = datetime.utcnow().isoformat() + "Z"
            matched = t
            break
    if not matched:
        raise ValueError(f"Transfer {transfer_id} not found")
    save_transfers(records)
    return matched


def get_transfer_impact(store_id: str = None) -> dict:
    """Compute aggregate ESG impact from all active transfers."""
    all_t = load_transfers()
    active = [
        t for t in all_t
        if t["status"] != "REJECTED"
        and (store_id is None or t["from_store_id"] == store_id or t["to_store_id"] == store_id)
    ]
    total_gbp  = round(sum(t["expected_saving_gbp"] for t in active), 2)
    total_units = sum(t["units"] for t in active)
    total_kg   = round(total_units * 0.45, 2)
    co2_avoided = round(total_kg * 3.3, 2)
    meals       = int(total_kg / 0.3)
    return {
        "active_transfers": len(active),
        "total_saving_gbp": total_gbp,
        "total_kg_saved":   total_kg,
        "co2_avoided_kg":   co2_avoided,
        "meals_equivalent": meals,
    }
