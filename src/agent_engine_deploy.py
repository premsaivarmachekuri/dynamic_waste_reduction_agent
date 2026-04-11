"""
Agent Engine deployment script — deploys the root_agent to Vertex AI Reasoning Engine.
Run AFTER local testing is confirmed working.

Usage:
    python agent_engine_deploy.py --project YOUR_PROJECT --location us-central1
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def deploy(project: str, location: str = "us-central1"):
    try:
        import vertexai
        from vertexai.preview import reasoning_engines
    except ImportError:
        print("❌ vertexai not installed. Run: pip install google-cloud-aiplatform")
        sys.exit(1)

    print(f"🚀 Deploying WasteReductionEngine to Vertex AI Agent Engine...")
    print(f"   Project: {project} | Location: {location}")

    vertexai.init(project=project, location=location)

    from agents.orchestrator import root_agent

    app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    deployed = reasoning_engines.ReasoningEngine.create(
        app,
        requirements=[
            "google-adk>=1.0.0",
            "google-cloud-bigquery>=3.0.0",
            "requests>=2.31.0",
            "pandas>=2.0.0",
            "numpy>=1.26.0",
            "python-dotenv>=1.0.0",
            "rich>=13.0.0",
        ],
        display_name="WasteReductionEngine",
        description="AI-Powered Dynamic Waste Reduction Engine for perishables optimization",
    )

    engine_id = deployed.resource_name
    print(f"\n✅ Deployed successfully!")
    print(f"   Resource name: {engine_id}")
    print(f"\nTest with:")
    print(f"   python agent_engine_deploy.py --test --engine-id {engine_id}")

    # Save the engine ID
    with open(".env", "a") as f:
        f.write(f"\nREASONING_ENGINE_ID={engine_id}\n")

    return engine_id


def test_deployed(engine_id: str, project: str, location: str = "us-central1"):
    try:
        import vertexai
        from vertexai.preview import reasoning_engines
    except ImportError:
        print("❌ vertexai not installed.")
        sys.exit(1)

    vertexai.init(project=project, location=location)
    engine = reasoning_engines.ReasoningEngine(engine_id)

    print(f"🧪 Testing deployed engine: {engine_id}")
    response = engine.query(
        input="Analyse store ST001 — forecast waste risk and execute optimal actions."
    )
    print(f"\n📊 Response:\n{response}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=False, help="GCP project ID")
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--test", action="store_true", help="Test deployed engine")
    parser.add_argument("--engine-id", help="Deployed engine resource name (for --test)")
    args = parser.parse_args()

    project = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("❌ Provide --project or set GOOGLE_CLOUD_PROJECT env var")
        sys.exit(1)

    if args.test and args.engine_id:
        test_deployed(args.engine_id, project, args.location)
    else:
        deploy(project, args.location)
