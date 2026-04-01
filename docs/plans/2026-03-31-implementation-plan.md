# Implementation Plan — Waste Reduction Engine
## 2-Day Hackathon Sprint
**Date:** 2026-03-31 | **Builder:** Varma

---

## Pre-Flight Checklist (Do This First)

```bash
# 1. Authenticate with GCP
gcloud auth application-default login
gcloud config set project YOUR_HACKATHON_PROJECT_ID

# 2. Enable required APIs
gcloud services enable aiplatform.googleapis.com run.googleapis.com

# 3. Set environment variables
export GOOGLE_CLOUD_PROJECT=YOUR_HACKATHON_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Generate synthetic data
python generate_data.py
```

---

## DAY 1 ACTION POINTS

### ✅ Step 1 — Environment Setup (09:00–10:00)

```bash
# Verify ADK is installed
python -c "import google.adk; print('ADK OK')"

# Verify Vertex AI auth
python -c "import google.cloud.aiplatform as aiplatform; aiplatform.init(project='YOUR_PROJECT_ID', location='us-central1'); print('Vertex AI OK')"
```

**What to check:** Both prints succeed. If not, re-run gcloud auth.

---

### ✅ Step 2 — Generate Synthetic Data (10:00–11:00)

```bash
python generate_data.py
```

**Expected output:**
```
✅ stores.csv: 5 stores
✅ skus.csv: 27 SKUs
✅ inventory.csv: ~400 batch records
✅ sales_history.csv: ~4050 sales records
🎯 Hero demo scenario (chicken at Store S001): [table of batches]
```

Verify the `data/` folder has all 4 CSVs.

---

### ✅ Step 3 — Test Tools Independently (11:00–12:00)

```python
# Run in Python REPL or Jupyter cell
from tools import load_inventory, score_spoilage_risk, simulate_actions

# Test 1: Load inventory
result = load_inventory(store_id="S001", sku_id="SKU001")
print(f"At-risk batches: {result['at_risk_count']}")
print(result['batches'][0])

# Test 2: Score risk
batch = result['batches'][0]
risk = score_spoilage_risk(batch)
print(f"Risk score: {risk['adjusted_risk_score']} | Level: {risk['risk_level']}")

# Test 3: Simulate actions
decision = simulate_actions(batch, risk_score=risk['adjusted_risk_score'])
print(f"Best action: {decision['recommended_action']['label']}")
print(f"Units saved: {decision['waste_prevented_units']}")
```

All 3 should run without errors before touching ADK agents.

---

### ✅ Step 4 — Test DataAgent (12:00–13:00)

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from agents.data_agent import data_agent
import asyncio

async def test_data_agent():
    svc = InMemorySessionService()
    runner = Runner(agent=data_agent, app_name="test", session_service=svc)
    session = await svc.create_session(app_name="test", user_id="test")

    async for event in runner.run_async(
        user_id="test",
        session_id=session.id,
        new_message=Content(parts=[Part(text="Load at-risk inventory for store S001")]),
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

asyncio.run(test_data_agent())
```

---

### ✅ Step 5 — Test Full Pipeline (13:00–16:00)

```bash
# Run the full orchestrator locally
python orchestrator.py
```

Watch the 4 agents run in sequence. Check that:
- DataAgent returns batches
- ForecastAgent adds risk scores
- DecisionAgent selects actions
- ExplanationAgent gives plain English output

**If an agent fails:** Check the error message. 90% of issues are:
- Missing `GOOGLE_CLOUD_PROJECT` env var
- ADK version mismatch (check `pip show google-adk`)
- JSON parsing (add `print(batch_json)` before `json.loads()`)

---

### ✅ Step 6 — Launch Gradio UI (16:00–20:00)

```bash
python app.py
```

Open `http://localhost:7860` in your browser. Test:
1. Store selector → inventory table populates
2. Risk heatmap tab → bar chart shows
3. Run AI Optimization button → agent response appears (takes 10–30 seconds)
4. Ask Gemini tab → chat works

---

## DAY 2 ACTION POINTS

### ✅ Step 7 — Deploy Agents to Vertex AI Agent Engine (09:00–11:00)

```bash
# Check ADK CLI is available
adk --version

# Deploy the orchestrator agent
adk deploy orchestrator.py \
  --project $GOOGLE_CLOUD_PROJECT \
  --region us-central1 \
  --display-name "WasteReductionEngine"
```

Note the deployed agent resource name — you'll need it if you want to call Agent Engine from the UI directly. For the hackathon demo, local runner is fine.

---

### ✅ Step 8 — Deploy Gradio UI to Cloud Run (11:00–13:00)

```bash
# Build and deploy
gcloud run deploy waste-engine-ui \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 7860 \
  --memory 2Gi \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=us-central1
```

Your public demo URL will be printed at the end:
`Service URL: https://waste-engine-ui-XXXX-uc.a.run.app`

---

### ✅ Step 9 — Hero Demo Scenario Polish (13:00–15:00)

Make sure this query produces a compelling output:

```
"Analyse the at-risk inventory at store S001 for chicken breast (SKU001).
What actions should we take to minimise waste today?"
```

Expected agent output structure:
```
📦 Batch B0001 — Chicken Breast 500g (Store S001)
Risk Level: HIGH (0.78)
Days to Expiry: 2
Projected Waste: 34 units

Scenario Analysis:
┌─────────────────────┬────────────┬──────────────┬──────────────┐
│ Action              │ Waste Units│ Waste Value  │ Net Impact   │
├─────────────────────┼────────────┼──────────────┼──────────────┤
│ No Action           │ 34         │ -£153        │ -£153        │
│ 10% Discount        │ 18         │ -£81         │ -£96         │
│ 25% Discount        │ 5          │ -£23         │ -£64         │
│ Transfer 27 units   │ 2          │ -£9          │ -£13 ✅      │
└─────────────────────┴────────────┴──────────────┴──────────────┘

✅ Recommended: Transfer 27 units to Store S002
💷 Value protected: £144 | 🌿 CO₂ prevented: 13.6 kg
```

---

### ✅ Step 10 — Add Second Demo Scenario (15:00–16:00)

Second scenario for variety — use this query:
```
"What actions should we take for bakery items at store S003 given the rainy weather forecast?"
```

---

### ✅ Step 11 — Demo Prep (16:00–19:00)

**Judge demo script (5 minutes):**

1. **(1 min)** Show ESG banner — "£X,XXX at risk of waste across 5 stores today"
2. **(1 min)** Show risk heatmap — "This is the AI scanning all 27 SKUs in real time"
3. **(2 min)** Run hero scenario — show the 4-scenario table, explain the optimization
4. **(30 sec)** Show Gemini explanation — "This is the 'why' — auditable AI decisions"
5. **(30 sec)** Show ESG impact — "32 units saved, 13.6 kg CO₂ prevented, £144 protected"

**Key judge soundbites:**
- "This is not rule-based markdown. This is intelligent orchestration."
- "Even a 2% improvement at Tesco scale = millions saved annually."
- "Every decision is explainable — store managers know exactly why."

---

## Troubleshooting Quick Reference

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: google.adk` | `pip install google-adk` |
| `DefaultCredentialsError` | `gcloud auth application-default login` |
| Agent returns empty response | Check Gemini API quota in GCP console |
| Gradio UI blank on Cloud Run | Check `--port 7860` and `server_name="0.0.0.0"` |
| `json.JSONDecodeError` in tools | Add `print(batch_json)` to debug input |
| Cloud Run out of memory | Increase `--memory` to 4Gi |

---

## File Reference

```
waste_engine/
├── generate_data.py     ← RUN FIRST. Generates all synthetic data.
├── tools.py             ← Pure Python tool functions. Test these first.
├── agents/
│   ├── data_agent.py    ← Step 4: Test in isolation
│   ├── forecast_agent.py
│   ├── decision_agent.py
│   └── explanation_agent.py
├── orchestrator.py      ← Step 5: Full pipeline test
├── app.py               ← Step 6: Gradio UI
├── Dockerfile           ← Step 8: Cloud Run deployment
└── requirements.txt
```
