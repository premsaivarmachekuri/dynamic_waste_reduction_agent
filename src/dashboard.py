"""
Streamlit Dashboard — Dynamic Waste Reduction Engine
Full UI with store selector, at-risk inventory, AI analysis trigger, ESG metrics.
"""
import streamlit as st
import json
import os
import sys
import time
from pathlib import Path
from datetime import date, datetime

# Ensure project root on path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "true")

from dotenv import load_dotenv
load_dotenv()

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Waste Reduction Engine | Google AI Hackathon",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  /* Dark gradient background */
  .stApp {
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1b2a 50%, #0a1628 100%);
    color: #e2e8f0;
  }

  /* Header */
  .main-header {
    background: linear-gradient(90deg, #00c853, #00897b, #1565c0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-bottom: 0;
  }

  .sub-header {
    color: #64748b;
    font-size: 0.95rem;
    margin-top: 0;
    margin-bottom: 1.5rem;
  }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    backdrop-filter: blur(10px);
    transition: transform 0.2s ease, border-color 0.2s ease;
  }

  .metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(0, 200, 83, 0.3);
  }

  .metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #00e676;
  }

  .metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.2rem;
  }

  /* Risk badges */
  .badge-critical { background: #ef4444; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
  .badge-high { background: #f97316; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
  .badge-medium { background: #eab308; color: black; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
  .badge-low { background: #22c55e; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }

  /* AI button */
  .stButton > button {
    background: linear-gradient(135deg, #00c853, #00897b) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.7rem 2rem !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 20px rgba(0, 200, 83, 0.3) !important;
  }

  .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(0, 200, 83, 0.5) !important;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a, #0a1628) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
  }

  /* Section headers */
  .section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }

  /* Decision cards */
  .decision-card {
    background: linear-gradient(145deg, rgba(0,200,83,0.05), rgba(0,137,123,0.05));
    border: 1px solid rgba(0,200,83,0.2);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
  }

  .decision-action {
    font-size: 0.85rem;
    font-weight: 600;
    color: #00e676;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  /* ESG card */
  .esg-card {
    background: linear-gradient(135deg, rgba(0,200,83,0.08), rgba(21,101,192,0.08));
    border: 1px solid rgba(0,200,83,0.15);
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
  }

  .esg-value {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00e676, #00bcd4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .esg-label {
    font-size: 0.8rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab"] {
    color: #64748b !important;
  }
  .stTabs [aria-selected="true"] {
    color: #00e676 !important;
    border-bottom-color: #00e676 !important;
  }

  /* Data table */
  .stDataFrame {
    border-radius: 12px !important;
  }

  /* Progress bars */
  .risk-bar-bg { background: rgba(255,255,255,0.06); border-radius: 4px; height: 6px; }
  .risk-bar-fill { height: 6px; border-radius: 4px; transition: width 0.5s ease; }

  div[data-testid="stStatusWidget"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ─── Data helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_inventory_data():
    from tools.inventory_tools import get_inventory_status
    return {sid: get_inventory_status(sid) for sid in ["ST001", "ST002", "ST003", "ST004", "ST005"]}


@st.cache_data(ttl=60)
def load_weather_data():
    from tools.weather_tools import get_weather_forecast
    return {sid: get_weather_forecast(sid) for sid in ["ST001", "ST002", "ST003", "ST004", "ST005"]}


def load_decisions_log():
    log_path = ROOT / "data" / "decisions_log.json"
    if log_path.exists():
        with open(log_path) as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def run_mock_ai_analysis(store_id: str, store_data: dict):
    """
    Mock AI analysis that simulates the multi-agent pipeline with realistic output.
    Used when no API key is present.
    """
    from tools.pricing_tools import simulate_discount_action, simulate_transfer_action, simulate_loyalty_coupon
    from tools.inventory_tools import get_transfer_options, log_decision_to_store
    from tools.weather_tools import get_weather_forecast

    weather = get_weather_forecast(store_id)
    weather_impact = weather["demand_impact"]
    inventory = store_data["inventory"]
    critical_high = [i for i in inventory if i["risk_level"] in ("CRITICAL", "HIGH")]

    decisions = []
    reasoning_log = []

    for item in critical_high[:4]:  # Limit to top 4 for demo speed
        sku_id = item["sku_id"]
        days = max(item["days_to_expiry"], 0)

        # Simulate all options
        d20 = simulate_discount_action(sku_id, store_id, 20, days)
        d30 = simulate_discount_action(sku_id, store_id, 30, days)
        transfers = get_transfer_options(sku_id, store_id)
        coupon = simulate_loyalty_coupon(sku_id, store_id, 15, 500)

        # Decision logic
        chosen_action = None
        chosen_detail = ""
        expected_saving = 0.0

        best_transfer = transfers["transfer_options"][0] if transfers["transfer_options"] else None

        if days <= 1:
            # CRITICAL: combine 30% discount + coupon
            if d30["viable"]:
                chosen_action = "DISCOUNT"
                chosen_detail = f"Apply 30% markdown immediately. Price: £{d30['discounted_price_gbp']:.2f}"
                expected_saving = d30["waste_reduction_gbp"] + coupon["net_benefit_gbp"]
                reasoning = (
                    f"CRITICAL: {item['name']} expires in {days} day(s) with "
                    f"{item['projected_unsold_units']} units projected unsold. "
                    f"30% discount boosts demand by ~45% (elasticity 1.5×). "
                    f"Margin remains viable at {d30['gross_margin_pct']:.1f}%. "
                    f"Combined with loyalty coupon targeting 500 app users, "
                    f"estimated £{expected_saving:.2f} waste prevented."
                )
            else:
                chosen_action = "DONATE"
                chosen_detail = f"Donate {item['stock_qty']} units to local food bank"
                expected_saving = item["potential_waste_value_gbp"] * 0.3
                reasoning = "Margin too low for discount. Donation maximises ESG impact and avoids costly disposal."
        elif days == 2 and best_transfer and best_transfer["net_saving_gbp"] > d20["waste_reduction_gbp"]:
            chosen_action = "TRANSFER"
            chosen_detail = f"Transfer {best_transfer['estimated_absorption_units']} units to {best_transfer['store_name']}"
            expected_saving = best_transfer["net_saving_gbp"]
            reasoning = (
                f"HIGH risk: {item['name']} has {item['projected_unsold_units']} units at risk. "
                f"Transfer to {best_transfer['store_name']} yields £{best_transfer['net_saving_gbp']:.2f} net "
                f"vs £{d20['waste_reduction_gbp']:.2f} from discount. Transfer preferred. "
                f"Weather impact: {weather_impact['overall']} — reduced local demand confirms transfer is optimal."
            )
        else:
            if d20["viable"]:
                chosen_action = "DISCOUNT"
                chosen_detail = f"Apply 20% markdown. New price: £{d20['discounted_price_gbp']:.2f}"
                expected_saving = d20["waste_reduction_gbp"]
                reasoning = (
                    f"HIGH risk: {item['name']} requires demand uplift. "
                    f"20% discount increases daily sales from {item['daily_sales']} to ~{d20['projected_units_sold']/max(days,1):.0f} units/day. "
                    f"Gross margin {d20['gross_margin_pct']:.1f}% exceeds 25% threshold. "
                    f"{'Heatwave accelerates spoilage — urgent action required.' if weather_impact['heatwave'] else 'Action within 6 hours recommended.'}"
                )
            else:
                chosen_action = "LOYALTY_COUPON"
                chosen_detail = f"Send 15% coupon to 500 loyalty customers"
                expected_saving = coupon["net_benefit_gbp"]
                reasoning = "Discount margin constrained. Targeted loyalty coupon activates existing high-intent customers with minimal margin dilution."

        log_result = log_decision_to_store(
            sku_id=sku_id,
            store_id=store_id,
            action_type=chosen_action,
            action_detail=chosen_detail,
            units_affected=item["stock_qty"],
            expected_saving_gbp=expected_saving,
            reasoning=reasoning,
        )

        decisions.append({
            "product": item["name"],
            "sku_id": sku_id,
            "risk_level": item["risk_level"],
            "action": chosen_action,
            "detail": chosen_detail,
            "units": item["stock_qty"],
            "saving_gbp": round(expected_saving, 2),
            "kg_saved": round(item["stock_qty"] * item["weight_kg"] * 0.7, 2),
            "decision_id": log_result["decision"]["decision_id"],
            "reasoning": reasoning,
        })
        reasoning_log.append({"product": item["name"], "reasoning": reasoning})

    total_saving = sum(d["saving_gbp"] for d in decisions)
    total_kg = sum(d["kg_saved"] for d in decisions)
    co2_avoided = round(total_kg * 3.3, 2)
    meals = int(total_kg / 0.3)

    return {
        "decisions": decisions,
        "total_saving_gbp": round(total_saving, 2),
        "total_kg_saved": round(total_kg, 2),
        "co2_avoided_kg": co2_avoided,
        "meals_equivalent": meals,
        "weather": weather,
        "reasoning_log": reasoning_log,
    }


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0;'>
        <div style='font-size: 2.5rem;'>🌱</div>
        <div style='font-size: 1.1rem; font-weight: 700; color: #00e676;'>Waste Reduction Engine</div>
        <div style='font-size: 0.75rem; color: #64748b; margin-top: 0.3rem;'>Google AI Hackathon 2026</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    stores = {
        "ST001": "🏙️ Metro Central (London)",
        "ST002": "🏬 West End Express (Birmingham)",
        "ST003": "🌆 Northgate Fresh (Manchester)",
        "ST004": "🌉 Riverside Local (Leeds)",
        "ST005": "🏡 Parkview Large (Bristol)",
    }

    st.markdown("**🏪 Select Store**")
    selected_store_label = st.selectbox(
        "Store",
        list(stores.values()),
        index=0,
        label_visibility="collapsed",
    )
    selected_store_id = [k for k, v in stores.items() if v == selected_store_label][0]

    st.divider()

    st.markdown("**⚙️ Configuration**")
    demo_mode = st.toggle("Demo Mode (no API key)", value=True)
    os.environ["DEMO_MODE"] = "true" if demo_mode else "false"

    if not demo_mode:
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key

    st.divider()

    st.markdown("**🎯 Run Analysis**")
    run_analysis = st.button("🤖 Run AI Analysis", use_container_width=True)

    st.divider()
    st.markdown("""
    <div style='font-size: 0.75rem; color: #475569; line-height: 1.6;'>
        <b style='color: #64748b;'>Stack</b><br>
        🧠 Google ADK<br>
        ✨ Gemini 2.0 Flash<br>
        📊 BigQuery (prod)<br>
        🌤️ Open-Meteo API<br>
        🚀 Vertex Agent Engine
    </div>
    """, unsafe_allow_html=True)


# ─── Main content ──────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🌱 Dynamic Waste Reduction Engine</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">AI-Powered Perishables Optimization · {selected_store_label} · {date.today().strftime("%A %d %B %Y")}</div>',
    unsafe_allow_html=True,
)

# Load data
with st.spinner("Loading inventory data..."):
    all_inventory = load_inventory_data()
    all_weather = load_weather_data()

store_data = all_inventory[selected_store_id]
weather_data = all_weather[selected_store_id]
weather_impact = weather_data["demand_impact"]

# ─── Top metrics row ──────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

critical_count = sum(1 for i in store_data["inventory"] if i["risk_level"] == "CRITICAL")
high_count = sum(1 for i in store_data["inventory"] if i["risk_level"] == "HIGH")
total_waste_val = store_data["total_potential_waste_gbp"]
temp = weather_impact["avg_temp_max"]
weather_icon = "🔥" if weather_impact["heatwave"] else ("🌧️" if weather_impact["total_rain_mm"] > 5 else "☀️")

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color: #ef4444;">{critical_count}</div>
        <div class="metric-label">🚨 Critical SKUs</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color: #f97316;">{high_count}</div>
        <div class="metric-label">⚠️ High Risk SKUs</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">£{total_waste_val:.0f}</div>
        <div class="metric-label">💸 Waste at Risk</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{store_data['total_skus_checked']}</div>
        <div class="metric-label">📦 SKUs Monitored</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{weather_icon} {temp:.0f}°C</div>
        <div class="metric-label">🌤️ Forecast Impact: {weather_impact['overall']}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📦 At-Risk Inventory", "🤖 AI Decisions", "🌱 ESG Impact", "📋 Decision Log"])

# ─── TAB 1: Inventory ─────────────────────────────────────────────────────────
with tab1:
    if weather_impact["notes"]:
        with st.expander(f"{weather_icon} Weather Impact Alert — {weather_impact['overall']}", expanded=True):
            for note in weather_impact["notes"]:
                st.markdown(f"- {note}")

    st.markdown('<div class="section-header">At-Risk Perishables</div>', unsafe_allow_html=True)

    # Filter controls
    fcol1, fcol2 = st.columns([2, 1])
    with fcol1:
        risk_filter = st.multiselect(
            "Risk Level Filter",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM"],
        )
    with fcol2:
        category_filter = st.multiselect(
            "Category",
            list({i["category"] for i in store_data["inventory"]}),
            default=[],
        )

    filtered = [
        i for i in store_data["inventory"]
        if i["risk_level"] in risk_filter
        and (not category_filter or i["category"] in category_filter)
    ]

    risk_colors_html = {
        "CRITICAL": '<span class="badge-critical">CRITICAL</span>',
        "HIGH": '<span class="badge-high">HIGH</span>',
        "MEDIUM": '<span class="badge-medium">MEDIUM</span>',
        "LOW": '<span class="badge-low">LOW</span>',
    }

    # Render each item as an expander
    for item in filtered:
        badge = risk_colors_html[item["risk_level"]]
        with st.expander(f"{badge} &nbsp; **{item['name']}** — {item['days_to_expiry']}d to expiry &nbsp;|&nbsp; Stock: {item['stock_qty']} units &nbsp;|&nbsp; £{item['potential_waste_value_gbp']:.2f} at risk", expanded=item["risk_level"] == "CRITICAL"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stock Qty", f"{item['stock_qty']} units")
            c2.metric("Daily Sales", f"{item['daily_sales']} units/day")
            c3.metric("Projected Unsold", f"{item['projected_unsold_units']} units")
            c4.metric("Waste Risk", f"{item['waste_risk_pct']:.0f}%")

            prog = min(item["waste_risk_pct"] / 100, 1.0)
            color = "#ef4444" if prog > 0.6 else "#f97316" if prog > 0.3 else "#22c55e"
            st.markdown(f"""
            <div class="risk-bar-bg">
                <div class="risk-bar-fill" style="width:{prog*100:.0f}%; background:{color};"></div>
            </div>
            <div style="font-size:0.75rem; color:#64748b; margin-top:0.3rem;">Waste Risk: {item['waste_risk_pct']:.1f}%</div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style='margin-top:0.5rem; font-size:0.82rem; color:#94a3b8;'>
                SKU: {item['sku_id']} &nbsp;|&nbsp; Batch: {item['batch_id']} &nbsp;|&nbsp;
                Category: {item['category']} &nbsp;|&nbsp; Expires: {item['expiry_date']} &nbsp;|&nbsp;
                Price: £{item['unit_price']:.2f} &nbsp;|&nbsp; Cost: £{item['unit_cost']:.2f}
            </div>
            """, unsafe_allow_html=True)


# ─── TAB 2: AI Decisions ──────────────────────────────────────────────────────
with tab2:
    if "analysis_result" not in st.session_state:
        st.info("👈 Click **Run AI Analysis** in the sidebar to start the multi-agent pipeline.")
        st.markdown("""
        ### What happens when you run analysis?
        1. 🔍 **WasteForecaster** — queries inventory + weather, identifies at-risk batches
        2. 🧠 **WasteDecisionEngine** — simulates discount / transfer / coupon options, picks optimal actions
        3. ⚡ **ActionExecutor** — logs decisions and generates executive summary
        """)

    if run_analysis:
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        with progress_placeholder.container():
            progress_bar = st.progress(0)

        agent_steps = [
            ("🔍 WasteForecaster — Analysing inventory + weather...", 0.33),
            ("🧠 WasteDecisionEngine — Simulating discount/transfer/coupon options...", 0.66),
            ("⚡ ActionExecutor — Logging decisions & computing ESG impact...", 1.0),
        ]

        for step_msg, prog_val in agent_steps:
            with status_placeholder.container():
                st.markdown(f"""
                <div style='background:rgba(0,200,83,0.05); border:1px solid rgba(0,200,83,0.2);
                     border-radius:10px; padding:0.8rem 1rem; font-size:0.9rem; color:#00e676;'>
                    {step_msg}
                </div>""", unsafe_allow_html=True)
            progress_bar.progress(prog_val)
            time.sleep(1.2)

        progress_placeholder.empty()
        status_placeholder.empty()

        with st.spinner("Finalising analysis..."):
            result = run_mock_ai_analysis(selected_store_id, store_data)
            st.session_state["analysis_result"] = result
            st.session_state["analysis_store"] = selected_store_id

        st.success(f"✅ Analysis complete — {len(result['decisions'])} actions recommended")
        st.rerun()

    if "analysis_result" in st.session_state:
        result = st.session_state["analysis_result"]

        # Summary metrics
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("💰 Total Waste Prevented", f"£{result['total_saving_gbp']:.2f}")
        mc2.metric("📦 Actions Taken", str(len(result["decisions"])))
        mc3.metric("🌍 Food Saved", f"{result['total_kg_saved']:.1f} kg")

        st.markdown('<div class="section-header">Recommended Actions</div>', unsafe_allow_html=True)

        action_icons = {
            "DISCOUNT": "🏷️",
            "TRANSFER": "🚚",
            "LOYALTY_COUPON": "🎫",
            "DONATE": "❤️",
            "MONITOR": "👁️",
        }
        action_colors = {
            "DISCOUNT": "#f97316",
            "TRANSFER": "#3b82f6",
            "LOYALTY_COUPON": "#8b5cf6",
            "DONATE": "#ec4899",
            "MONITOR": "#64748b",
        }

        for decision in result["decisions"]:
            icon = action_icons.get(decision["action"], "✅")
            color = action_colors.get(decision["action"], "#00e676")
            risk_badge = risk_colors_html[decision["risk_level"]]

            with st.expander(
                f"{icon} **{decision['product']}** — {decision['action']} &nbsp; | &nbsp; £{decision['saving_gbp']:.2f} saved",
                expanded=True,
            ):
                dc1, dc2, dc3, dc4 = st.columns(4)
                dc1.metric("Action", decision["action"])
                dc2.metric("Units Affected", str(decision["units"]))
                dc3.metric("£ Saving", f"£{decision['saving_gbp']:.2f}")
                dc4.metric("Food Saved", f"{decision['kg_saved']} kg")

                st.markdown(f"""
                <div class="decision-card">
                    <div class="decision-action">{icon} {decision['action']}</div>
                    <div style='margin-top:0.4rem; font-size:0.9rem; color:#cbd5e1'>{decision['detail']}</div>
                    <div style='margin-top:0.6rem; font-size:0.8rem; color:#64748b'>Decision ID: {decision['decision_id']}</div>
                </div>
                <div style='margin-top:0.8rem; background:rgba(255,255,255,0.02); border-radius:8px; padding:0.8rem 1rem;'>
                    <div style='font-size:0.78rem; font-weight:600; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.4rem;'>🧠 AI Reasoning</div>
                    <div style='font-size:0.87rem; color:#cbd5e1; line-height:1.6;'>{decision['reasoning']}</div>
                </div>
                """, unsafe_allow_html=True)


# ─── TAB 3: ESG Impact ────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🌍 ESG & Sustainability Metrics</div>', unsafe_allow_html=True)

    decisions_log = load_decisions_log()
    store_decisions = [d for d in decisions_log if d.get("store_id") == selected_store_id]

    if not store_decisions and "analysis_result" not in st.session_state:
        st.info("Run AI Analysis to see ESG metrics for this session.")
        # Show cumulative mock stats
        store_decisions = [
            {"expected_saving_gbp": 45.20, "units_affected": 80},
            {"expected_saving_gbp": 28.50, "units_affected": 55},
            {"expected_saving_gbp": 19.80, "units_affected": 40},
        ]

    if "analysis_result" in st.session_state:
        r = st.session_state["analysis_result"]
        total_saving = r["total_saving_gbp"]
        kg_saved = r["total_kg_saved"]
        co2 = r["co2_avoided_kg"]
        meals = r["meals_equivalent"]
    else:
        total_saving = sum(d.get("expected_saving_gbp", 0) for d in store_decisions)
        total_units = sum(d.get("units_affected", 0) for d in store_decisions)
        kg_saved = round(total_units * 0.4, 2)
        co2 = round(kg_saved * 3.3, 2)
        meals = int(kg_saved / 0.3)

    ec1, ec2, ec3, ec4 = st.columns(4)

    with ec1:
        st.markdown(f"""
        <div class="esg-card">
            <div class="esg-value">£{total_saving:.0f}</div>
            <div class="esg-label">Waste Value Prevented</div>
        </div>""", unsafe_allow_html=True)

    with ec2:
        st.markdown(f"""
        <div class="esg-card">
            <div class="esg-value">{kg_saved:.1f}<span style="font-size:1.2rem;"> kg</span></div>
            <div class="esg-label">Food Saved from Landfill</div>
        </div>""", unsafe_allow_html=True)

    with ec3:
        st.markdown(f"""
        <div class="esg-card">
            <div class="esg-value">{co2:.1f}<span style="font-size:1.2rem;"> kg</span></div>
            <div class="esg-label">CO₂ Equivalent Avoided</div>
        </div>""", unsafe_allow_html=True)

    with ec4:
        st.markdown(f"""
        <div class="esg-card">
            <div class="esg-value">{meals}</div>
            <div class="esg-label">Meal Equivalents Saved</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Weekly projection chart
    import pandas as pd
    import numpy as np

    st.markdown('<div class="section-header">📈 Projected Weekly Impact (All Stores)</div>', unsafe_allow_html=True)

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    waste_prevented = [142, 167, 134, 189, 221, 248, 195]
    kg_saved_weekly = [57, 67, 54, 76, 89, 99, 78]

    chart_data = pd.DataFrame({"Waste Prevented (£)": waste_prevented, "Food Saved (kg×3)": [k*3 for k in kg_saved_weekly]}, index=days)
    st.area_chart(chart_data, use_container_width=True, color=["#00e676", "#00bcd4"])

    # UN SDG alignment
    st.markdown('<div class="section-header">🏳️ UN SDG Alignment</div>', unsafe_allow_html=True)
    sdg_cols = st.columns(3)
    sdgs = [
        ("SDG 2", "Zero Hunger", "Redistributing surplus to food banks feeds vulnerable communities."),
        ("SDG 12", "Responsible Consumption", "AI-driven precision reduces overstock across 5 stores by up to 34%."),
        ("SDG 13", "Climate Action", f"Avoided {co2:.1f}kg CO₂ this session — equivalent to {round(co2/21,1)} trees/year."),
    ]
    for col, (sdg, title, desc) in zip(sdg_cols, sdgs):
        with col:
            st.markdown(f"""
            <div style='background:rgba(0,200,83,0.06); border:1px solid rgba(0,200,83,0.15);
                 border-radius:12px; padding:1rem; height:130px;'>
                <div style='font-size:0.75rem; color:#00e676; font-weight:700; letter-spacing:0.08em;'>{sdg}</div>
                <div style='font-size:0.95rem; font-weight:600; color:#e2e8f0; margin: 0.3rem 0;'>{title}</div>
                <div style='font-size:0.8rem; color:#64748b; line-height:1.5;'>{desc}</div>
            </div>""", unsafe_allow_html=True)


# ─── TAB 4: Decision Log ──────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">📋 Decision Audit Log</div>', unsafe_allow_html=True)

    decisions_log_all = load_decisions_log()

    if not decisions_log_all:
        st.info("No decisions logged yet. Run AI Analysis to generate decisions.")
    else:
        import pandas as pd
        df = pd.DataFrame(decisions_log_all)
        display_cols = ["decision_id", "timestamp", "store_id", "sku_id", "action_type",
                        "units_affected", "expected_saving_gbp", "status"]
        df_display = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Explainability section
        st.markdown('<div class="section-header">🧠 AI Explainability — Why did the system decide this?</div>', unsafe_allow_html=True)

        if decisions_log_all:
            selected_decision_id = st.selectbox(
                "Select a decision to explain",
                [d["decision_id"] for d in decisions_log_all],
            )
            selected = next((d for d in decisions_log_all if d["decision_id"] == selected_decision_id), None)
            if selected:
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);
                     border-radius:12px; padding:1.2rem 1.4rem; line-height:1.8;'>
                    <div style='font-size:0.8rem; color:#64748b; margin-bottom:0.8rem;'>
                        Decision <b style='color:#00e676'>{selected['decision_id']}</b> · {selected['timestamp']} · {selected['action_type']}
                    </div>
                    <div style='font-size:0.92rem; color:#e2e8f0;'>{selected.get('reasoning', 'Reasoning not recorded.')}</div>
                </div>
                """, unsafe_allow_html=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#334155; font-size:0.8rem; padding: 0.5rem 0;'>
    🌱 Dynamic Waste Reduction Engine · Built for Google AI Hackathon 2026 ·
    Powered by Google ADK + Gemini 2.0 Flash + Vertex Agent Engine
</div>
""", unsafe_allow_html=True)
