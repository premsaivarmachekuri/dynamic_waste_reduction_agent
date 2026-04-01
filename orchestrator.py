"""
orchestrator.py
---------------
OrchestratorAgent: Wires the 4 agents into a SequentialAgent pipeline.
This is the entry point for the ADK runtime and Vertex AI Agent Engine deployment.

Usage (local):
    python orchestrator.py

Usage (ADK CLI):
    adk run orchestrator.py
    adk deploy orchestrator.py --project YOUR_PROJECT_ID --region us-central1
"""

from google.adk.agents import SequentialAgent
from agents.data_agent import data_agent
from agents.forecast_agent import forecast_agent
from agents.decision_agent import decision_agent
from agents.explanation_agent import explanation_agent

# ─────────────────────────────────────────
# The main orchestrator pipeline
# ─────────────────────────────────────────

root_agent = SequentialAgent(
    name="WasteReductionOrchestrator",
    description=(
        "Autonomous perishable waste reduction engine for supermarkets. "
        "Orchestrates 4 specialized agents: data retrieval → spoilage forecasting → "
        "decision optimization → natural language explanation. "
        "Input: store_id and/or sku_id query. "
        "Output: prioritized action recommendations with ESG impact metrics."
    ),
    sub_agents=[
        data_agent,
        forecast_agent,
        decision_agent,
        explanation_agent,
    ],
)

# ─────────────────────────────────────────
# Local test runner
# ─────────────────────────────────────────

if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part
    import asyncio

    async def run_demo():
        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            app_name="waste_reduction_engine",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="waste_reduction_engine",
            user_id="demo_user",
        )

        # Hero demo query — the chicken scenario
        query = (
            "Analyse the at-risk inventory at store S001 for chicken breast (SKU001). "
            "What actions should we take to minimise waste today?"
        )

        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print(f"{'='*60}\n")

        async for event in runner.run_async(
            user_id="demo_user",
            session_id=session.id,
            new_message=Content(parts=[Part(text=query)]),
        ):
            if event.is_final_response():
                print("\n🤖 AGENT RESPONSE:")
                print(event.content.parts[0].text)

    asyncio.run(run_demo())
