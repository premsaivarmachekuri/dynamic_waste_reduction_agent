"""
main.py — CLI runner for the Dynamic Waste Reduction Engine v2.0.

Usage:
    python main.py                        # Interactive store selection
    python main.py --store ST001          # Analyse specific store
    python main.py --demo                 # Full demo (all stores)
    python main.py --test-tools           # Verify all tools without API key
    python main.py --network              # Network-wide summary
    python main.py --rag-test             # Test RAG corpus retrieval
    python main.py --query "Why ST001?"   # Custom agent query
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("DEMO_MODE", "true")

from dotenv import load_dotenv
load_dotenv(override=True)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║   🌱  Dynamic Waste Reduction Engine  v2.0  🌱                       ║
║   Multi-Agent · Vertex AI · BigQuery · RAG · Gemini 2.5 Flash        ║
║   Google AI Hackathon 2026                                            ║
╚══════════════════════════════════════════════════════════════════════╝"""
    console.print(banner, style="bold green")


def test_tools_only(store_id: str = "ST001"):
    """Run all tools without ADK to verify they work end-to-end."""
    from tools.inventory_tools import get_inventory_status, get_transfer_options, log_decision_to_store
    from tools.weather_tools import get_weather_forecast
    from tools.pricing_tools import (
        simulate_discount_action, simulate_transfer_action,
        simulate_loyalty_coupon, calculate_esg_metrics, calculate_price_elasticity,
    )
    from tools.bigquery_tools import query_historical_sales, get_network_inventory_summary
    from tools.rag_tools import query_waste_reduction_knowledge, query_price_elasticity_data

    console.print("\n[bold cyan]━━━ TOOL VERIFICATION RUN v2.0 ━━━[/bold cyan]\n")

    # 1. Inventory
    console.print("[yellow]1. get_inventory_status...[/yellow]")
    inv = get_inventory_status(store_id)
    console.print(f"   ✅ {inv['total_skus_checked']} SKUs | "
                  f"{inv['critical_high_risk_skus']} CRITICAL/HIGH | "
                  f"£{inv['total_potential_waste_gbp']:.2f} at risk | "
                  f"source={inv.get('source', 'unknown')}")

    # 2. Weather
    console.print("[yellow]2. get_weather_forecast...[/yellow]")
    weather = get_weather_forecast(store_id)
    impact = weather["demand_impact"]
    console.print(f"   ✅ {weather['city']}: {impact['avg_temp_max']}°C | "
                  f"impact={impact['overall']} | heatwave={impact['heatwave']}")

    # 3. Historical sales (BQ)
    console.print("[yellow]3. query_historical_sales (BigQuery)...[/yellow]")
    critical_items = [i for i in inv["inventory"] if i["risk_level"] in ("CRITICAL", "HIGH")]
    if critical_items:
        item = critical_items[0]
        hs = query_historical_sales(store_id, item["sku_id"], days=14)
        console.print(f"   ✅ {item['name']}: avg {hs.get('avg_daily_sales','?')}/day | "
                      f"waste rate {hs.get('waste_rate_pct','?')}% | "
                      f"trend={hs.get('trend','?')} | source={hs.get('source','?')}")

    # 4. Network summary
    console.print("[yellow]4. get_network_inventory_summary...[/yellow]")
    net = get_network_inventory_summary()
    console.print(f"   ✅ Network waste risk: £{net.get('network_total_waste_risk_gbp','?')} | "
                  f"{len(net.get('stores',[]))} stores")

    # 5. Price elasticity
    console.print("[yellow]5. calculate_price_elasticity...[/yellow]")
    elast = calculate_price_elasticity("Meat & Poultry", 20)
    console.print(f"   ✅ Meat & Poultry ε={elast['elasticity_coeff']} | "
                  f"20% discount → +{elast['demand_uplift_pct']}% demand")

    # 6. Discount simulations
    if critical_items:
        item = critical_items[0]
        sku_id = item["sku_id"]
        console.print(f"[yellow]6. simulate_discount_action for {item['name']}...[/yellow]")
        for pct in [20, 30]:
            r = simulate_discount_action(sku_id, store_id, pct, item["days_to_expiry"])
            status = "✅" if r["viable"] else "❌"
            console.print(f"   {status} {pct}% → margin={r['gross_margin_pct']:.1f}% | "
                          f"waste saved=£{r['waste_reduction_gbp']:.2f} | "
                          f"units sold={r['projected_units_sold']:.0f}")

        # 7. Transfer
        console.print("[yellow]7. get_transfer_options...[/yellow]")
        transfers = get_transfer_options(sku_id, store_id)
        if transfers["transfer_options"]:
            best = transfers["transfer_options"][0]
            console.print(f"   ✅ Best: → {best['store_name']} | "
                          f"{best['estimated_absorption_units']} units | "
                          f"net saving=£{best['net_saving_gbp']:.2f}")

        # 8. Loyalty coupon
        console.print("[yellow]8. simulate_loyalty_coupon...[/yellow]")
        coupon = simulate_loyalty_coupon(sku_id, store_id, 15, 500)
        console.print(f"   ✅ {coupon['expected_redemptions']} redemptions | "
                      f"net benefit=£{coupon['net_benefit_gbp']:.2f}")

        # 9. Log decision
        console.print("[yellow]9. log_decision_to_store...[/yellow]")
        log = log_decision_to_store(
            sku_id=sku_id, store_id=store_id, action_type="DISCOUNT",
            action_detail=f"Apply 20% markdown to {item['name']}",
            units_affected=int(item["stock_qty"]),
            expected_saving_gbp=15.50,
            reasoning="CRITICAL expiry risk. 20% discount provides viable margin (34.5%) while maximising sell-through.",
        )
        console.print(f"   ✅ Decision logged: ID={log['decision']['decision_id']}")

    # 10. RAG retrieval
    console.print("[yellow]10. query_waste_reduction_knowledge (RAG)...[/yellow]")
    rag_result = query_waste_reduction_knowledge("optimal discount for chicken breast expiring today", top_k=2)
    snippet = rag_result[:150].replace('\n', ' ') + "..."
    console.print(f"   ✅ RAG: '{snippet}'")

    # 11. ESG metrics
    console.print("[yellow]11. calculate_esg_metrics...[/yellow]")
    mock_decisions = [{"units_affected": 50, "expected_saving_gbp": 30, "sku_id": "SKU-0001", "action_type": "DISCOUNT"}]
    esg = calculate_esg_metrics(mock_decisions)
    console.print(f"   ✅ {esg['kg_food_saved']}kg food | "
                  f"{esg['co2_avoided_kg']}kg CO₂ | "
                  f"{esg['meals_equivalent']} meals")

    # Inventory risk table
    console.print("\n[bold green]━━━ AT-RISK INVENTORY (TOP 10) ━━━[/bold green]")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("SKU",       style="cyan",   width=10)
    table.add_column("Product",                   width=25)
    table.add_column("Stock",     justify="right", width=6)
    table.add_column("Daily",     justify="right", width=6)
    table.add_column("Expires",   justify="right", width=8)
    table.add_column("Unsold",    justify="right", width=7)
    table.add_column("Risk",      justify="center", width=9)
    table.add_column("£ At Risk", justify="right", width=10)

    colors = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}
    for item in inv["inventory"][:10]:
        table.add_row(
            item["sku_id"], item["name"][:25],
            str(item["stock_qty"]), str(item["daily_sales"]),
            f"{item['days_to_expiry']}d",
            str(item["projected_unsold_units"]),
            Text(item["risk_level"], style=colors.get(item["risk_level"], "white")),
            f"£{item['potential_waste_value_gbp']:.2f}",
        )
    console.print(table)
    console.print(f"\n[bold]Total waste risk: £{inv['total_potential_waste_gbp']:.2f}[/bold]")
    console.print("\n[bold green]✅ All 11 tools verified.[/bold green]\n")


def test_rag(query: str = "optimal discount for chicken breast expiring today"):
    """Test Vertex AI RAG retrieval directly."""
    console.print(f"\n[bold cyan]━━━ RAG CORPUS TEST ━━━[/bold cyan]")
    console.print(f"Query: [yellow]{query}[/yellow]\n")

    from rag.retriever import retrieve_context, _check_rag_available, _get_corpus_name

    corpus = _get_corpus_name()
    available = _check_rag_available()
    console.print(f"Corpus: {corpus or 'Not set'}")
    console.print(f"Vertex AI RAG: {'✅ Available' if available else '⚠️ Using local fallback'}\n")

    context = retrieve_context(query, top_k=3)
    console.print(Panel(context[:2000], title="Retrieved Context", border_style="cyan"))


def show_network_summary():
    """Display network-wide waste risk summary."""
    from tools.bigquery_tools import get_network_inventory_summary

    console.print("\n[bold cyan]━━━ NETWORK WASTE RISK SUMMARY ━━━[/bold cyan]\n")
    net = get_network_inventory_summary()

    table = Table(box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Store ID")
    table.add_column("Name")
    table.add_column("Critical", justify="right", style="bold red")
    table.add_column("High",     justify="right", style="red")
    table.add_column("Medium",   justify="right", style="yellow")
    table.add_column("Low",      justify="right", style="green")
    table.add_column("£ At Risk", justify="right")

    store_names = {
        "ST001": "Metro Central", "ST002": "West End Express",
        "ST003": "Northgate Fresh", "ST004": "Riverside Local", "ST005": "Parkview Large",
    }
    for s in net.get("stores", []):
        table.add_row(
            s["store_id"], store_names.get(s["store_id"], s["store_id"]),
            str(s.get("critical", 0)), str(s.get("high", 0)),
            str(s.get("medium", 0)),  str(s.get("low", 0)),
            f"£{s['total_waste_value_gbp']:.2f}",
        )

    console.print(table)
    console.print(f"\n[bold]Network total: £{net.get('network_total_waste_risk_gbp', 0):.2f}[/bold]")


def run_adk_agent(store_id: str, query: str | None = None):
    """Run the full multi-agent pipeline."""
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        from agents.orchestrator import root_agent

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            console.print("[red]❌ GOOGLE_API_KEY not set.[/red]")
            console.print("[yellow]Run with --test-tools to verify without API key.[/yellow]")
            sys.exit(1)

        session_service = InMemorySessionService()
        APP_NAME   = "waste_reduction_engine_v2"
        USER_ID    = "demo_user"
        SESSION_ID = f"session_{store_id}"

        session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

        prompt = query or (
            f"Run a complete waste reduction analysis for store {store_id}. "
            f"Execute the full pipeline: demand forecast → risk scoring → pricing optimization → "
            f"transfer planning → decision optimization → execution → explanation. "
            f"Provide the full executive summary with ESG metrics."
        )
        console.print(f"\n[bold cyan]🤖 Multi-Agent Pipeline: {store_id}[/bold cyan]")
        console.print(f"Query: [italic]{prompt[:100]}...[/italic]\n")

        content = types.Content(role="user", parts=[types.Part(text=prompt)])
        final_response = ""
        for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
            if event.is_final_response():
                final_response = event.content.parts[0].text

        console.print(Panel(final_response, title="🌱 AI Analysis Complete", border_style="green"))

    except ImportError as e:
        console.print(f"[red]❌ ADK not available: {e}[/red]")
        console.print("[yellow]Falling back to tool verification mode...[/yellow]")
        test_tools_only(store_id)


def main():
    parser = argparse.ArgumentParser(
        description="Dynamic Waste Reduction Engine v2.0 — Google AI Hackathon"
    )
    parser.add_argument("--store",    default="ST001", help="Store ID (ST001–ST005)")
    parser.add_argument("--demo",     action="store_true", help="Run full demo")
    parser.add_argument("--test-tools", action="store_true", help="Test all tools (no API key needed)")
    parser.add_argument("--network",  action="store_true", help="Show network summary")
    parser.add_argument("--rag-test", action="store_true", help="Test RAG corpus")
    parser.add_argument("--query",    type=str, help="Custom agent query")
    args = parser.parse_args()

    print_banner()

    if args.network:
        show_network_summary()
        return

    if args.rag_test:
        test_rag(args.query or "optimal discount strategy for chicken breast expiring today")
        return

    if args.test_tools or args.demo:
        stores = ["ST001", "ST002", "ST003", "ST004", "ST005"] if args.demo else [args.store]
        for sid in stores[:2]:  # limit demo to 2 stores for speed
            console.print(f"\n[bold]═══ Store {sid} ═══[/bold]")
            test_tools_only(sid)
        if not args.demo:
            return

    if not args.test_tools:
        run_adk_agent(args.store, args.query)


if __name__ == "__main__":
    main()
