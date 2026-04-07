"""
app.py
------
Gradio UI for the Waste Reduction Engine.
3-panel layout: Inventory Explorer | Risk Heatmap | Agent Decisions

Run locally:  python app.py
Deploy:       gcloud run deploy waste-engine-ui --source . --port 7860
"""

import gradio as gr
import pandas as pd
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from src.orchestrator import root_agent
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ─────────────────────────────────────────
# ADK Runner setup
# ─────────────────────────────────────────

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="waste_reduction_engine",
    session_service=session_service,
)

async def run_agent(query: str) -> str:
    session = await session_service.create_session(
        app_name="waste_reduction_engine",
        user_id="gradio_user",
    )
    result = ""
    async for event in runner.run_async(
        user_id="gradio_user",
        session_id=session.id,
        new_message=Content(parts=[Part(text=query)]),
    ):
        if event.is_final_response():
            result = event.content.parts[0].text
    return result

def run_agent_sync(query: str) -> str:
    return asyncio.run(run_agent(query))


# ─────────────────────────────────────────
# Data helpers for UI
# ─────────────────────────────────────────

def load_inventory_table(store_id: str) -> pd.DataFrame:
    df = pd.read_csv(f"{DATA_DIR}/inventory.csv")
    if store_id != "All Stores":
        df = df[df["store_id"] == store_id]
    df = df[["sku_name", "category", "batch_id", "quantity",
             "days_to_expiry", "projected_unsold", "waste_risk_score", "weather_tag"]]
    df = df.sort_values("waste_risk_score", ascending=False)
    df.columns = ["Product", "Category", "Batch", "Qty", "Days Left",
                  "Projected Waste", "Risk Score", "Weather"]
    return df.head(30)

def load_risk_chart_data(store_id: str) -> pd.DataFrame:
    df = pd.read_csv(f"{DATA_DIR}/inventory.csv")
    if store_id != "All Stores":
        df = df[df["store_id"] == store_id]
    chart = df.groupby("sku_name")["waste_risk_score"].mean().reset_index()
    chart.columns = ["Product", "Avg Risk Score"]
    chart = chart.sort_values("Avg Risk Score", ascending=False).head(15)
    return chart

def get_store_options():
    stores = pd.read_csv(f"{DATA_DIR}/stores.csv")
    return ["All Stores"] + stores["store_id"].tolist()

def get_sku_options():
    skus = pd.read_csv(f"{DATA_DIR}/skus.csv")
    return ["All SKUs"] + skus["sku_id"].tolist()

def get_esg_summary(store_id: str) -> str:
    df = pd.read_csv(f"{DATA_DIR}/inventory.csv")
    if store_id != "All Stores":
        df = df[df["store_id"] == store_id]
    at_risk = df[df["waste_risk_score"] > 0.3]
    total_waste_units = at_risk["projected_unsold"].sum()
    total_waste_value = (at_risk["projected_unsold"] * at_risk["cost_price"]).sum()
    co2_at_risk = total_waste_units * 0.4 * 2.5  # kg CO2e
    return (
        f"⚠️ **{int(total_waste_units)} units** at risk of waste  |  "
        f"💷 **£{total_waste_value:.0f}** value at risk  |  "
        f"🌿 **{co2_at_risk:.0f} kg CO₂e** preventable emissions"
    )


# ─────────────────────────────────────────
# Gradio UI
# ─────────────────────────────────────────

with gr.Blocks(
    title="AI Waste Reduction Engine",
    theme=gr.themes.Soft(primary_hue="green"),
    css="""
        .risk-high { color: #dc2626; font-weight: bold; }
        .risk-med  { color: #d97706; }
        .risk-low  { color: #16a34a; }
        h1 { text-align: center; }
    """
) as demo:

    gr.Markdown("""
    # 🌿 AI-Powered Dynamic Waste Reduction Engine
    ### Autonomous Perishable Optimization · Powered by Google ADK + Gemini
    """)

    with gr.Row():
        store_selector = gr.Dropdown(
            choices=get_store_options(),
            value="S001",
            label="🏪 Select Store",
            scale=2,
        )
        sku_selector = gr.Dropdown(
            choices=get_sku_options(),
            value="SKU001",
            label="📦 Select SKU (for deep analysis)",
            scale=2,
        )
        run_btn = gr.Button("🤖 Run AI Optimization", variant="primary", scale=1)

    esg_banner = gr.Markdown(value="*Select a store to see waste risk summary*")

    with gr.Tabs():

        # ── Tab 1: Inventory Explorer ──
        with gr.Tab("📋 Inventory Risk"):
            inventory_table = gr.DataFrame(
                label="At-Risk Inventory Batches (sorted by risk score)",
                interactive=False,
                wrap=True,
            )

        # ── Tab 2: Risk Heatmap ──
        with gr.Tab("📊 Risk Heatmap"):
            risk_chart = gr.BarPlot(
                x="Product",
                y="Avg Risk Score",
                title="Average Waste Risk Score by Product",
                color="Avg Risk Score",
                height=400,
            )

        # ── Tab 3: Agent Decision Output ──
        with gr.Tab("🤖 Agent Decisions"):
            agent_output = gr.Markdown(
                value="*Click 'Run AI Optimization' to see agent recommendations*"
            )

        # ── Tab 4: Gemini Chat ──
        with gr.Tab("💬 Ask the AI"):
            gr.Markdown("Ask the AI to explain any decision or analyse a specific product.")
            chat_input = gr.Textbox(
                placeholder="e.g. Why did you choose transfer over discount for chicken?",
                label="Your question",
            )
            chat_btn = gr.Button("Ask Gemini", variant="secondary")
            chat_output = gr.Markdown()

    # ── Event handlers ──

    def on_store_change(store_id):
        table = load_inventory_table(store_id)
        chart = load_risk_chart_data(store_id)
        esg = get_esg_summary(store_id)
        return table, chart, esg

    def on_run_optimization(store_id, sku_id):
        sku_part = f" for {sku_id}" if sku_id != "All SKUs" else ""
        store_part = f" at store {store_id}" if store_id != "All Stores" else " across all stores"
        query = (
            f"Analyse the at-risk perishable inventory{sku_part}{store_part}. "
            f"Run the full optimization pipeline: identify high-risk batches, "
            f"forecast spoilage risk, simulate all action scenarios, and recommend "
            f"the optimal actions with clear explanations. "
            f"Include total ESG impact summary at the end."
        )
        result = run_agent_sync(query)
        return f"### 🤖 Agent Recommendations\n\n{result}"

    def on_chat(question, store_id, sku_id):
        context = f"[Context: Store {store_id}, SKU {sku_id}]\n\n"
        result = run_agent_sync(context + question)
        return result

    store_selector.change(
        fn=on_store_change,
        inputs=[store_selector],
        outputs=[inventory_table, risk_chart, esg_banner],
    )

    run_btn.click(
        fn=on_run_optimization,
        inputs=[store_selector, sku_selector],
        outputs=[agent_output],
    )

    chat_btn.click(
        fn=on_chat,
        inputs=[chat_input, store_selector, sku_selector],
        outputs=[chat_output],
    )

    # Load initial data
    demo.load(
        fn=on_store_change,
        inputs=[store_selector],
        outputs=[inventory_table, risk_chart, esg_banner],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
    )
