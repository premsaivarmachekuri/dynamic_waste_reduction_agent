# 🌱 Dynamic Waste Reduction Engine

> **Google AI Hackathon 2026** — AI-Powered Perishables Optimization using Google ADK + Gemini 2.0 Flash + Vertex AI Agent Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Google ADK](https://img.shields.io/badge/Google-ADK-orange.svg)](https://google.github.io/adk-docs/)
[![Gemini 2.0](https://img.shields.io/badge/Gemini-2.0%20Flash-green.svg)](https://deepmind.google/gemini/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What It Does

A multi-agent AI system that predicts food waste before it happens and autonomously executes optimal reduction actions:

```
📦 Inventory + 🌤️ Weather → 🔍 Forecast Risk → 🧠 Simulate Actions → ⚡ Execute & Log → 🌍 ESG Report
```

**Key capabilities:**
- **Real-time waste forecasting** per SKU across 5 stores
- **Multi-action simulation**: discount, stock transfer, loyalty coupon
- **Margin-aware decisions** (always protects ≥25% gross margin)
- **ESG metrics**: kg food saved, CO₂ avoided, meals equivalent
- **AI explainability**: "Why did the system decide this?"

---

## 🏗️ Architecture

```
waste-reduction-engine/
├── agents/
│   ├── forecasting_agent.py    ← WasteForecaster (inventory + weather)
│   ├── decision_agent.py       ← WasteDecisionEngine (simulate + optimize)
│   ├── execution_agent.py      ← ActionExecutor (log + explain)
│   └── orchestrator.py         ← Root orchestrator (multi-agent pipeline)
├── tools/
│   ├── inventory_tools.py      ← BigQuery / mock inventory queries
│   ├── weather_tools.py        ← Open-Meteo API (free, no key needed)
│   └── pricing_tools.py        ← Discount / transfer / coupon simulations
├── data/
│   ├── mock_inventory.json     ← Synthetic Sainsbury's-style data (5 stores)
│   └── decisions_log.json      ← AI decision audit log (auto-generated)
├── tests/
│   └── test_engine.py          ← Full pytest suite
├── dashboard.py                ← Streamlit UI
├── main.py                     ← CLI runner
└── agent_engine_deploy.py      ← Vertex AI deployment
```

### Agent Flow

```
User Query
    ↓
WasteReductionOrchestrator (root_agent)
    ├── WasteForecaster
    │     ├── get_inventory_status()   → At-risk batches
    │     ├── get_weather_forecast()   → Demand modifiers
    │     └── get_transfer_options()   → Possible destinations
    ├── WasteDecisionEngine
    │     ├── simulate_discount_action(10/20/30%)
    │     ├── simulate_transfer_action()
    │     └── simulate_loyalty_coupon()
    └── ActionExecutor
          ├── log_decision_to_store()  → Persist decisions
          └── calculate_esg_metrics()  → ESG summary
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
# or
pip install streamlit google-adk google-cloud-bigquery google-cloud-aiplatform \
            requests pandas numpy python-dotenv rich faker
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY for full ADK mode
# Leave DEMO_MODE=true to run without any API keys
```

### 3. Run tests (no API key needed)
```bash
pytest tests/ -v
```

### 4. CLI tool test
```bash
python main.py --test-tools --store ST001
```

### 5. Launch dashboard
```bash
streamlit run dashboard.py
```

### 6. Full ADK agent run (requires GOOGLE_API_KEY)
```bash
python main.py --store ST001
# or custom query:
python main.py --query "Why is Metro Central wasting so much salmon this week?"
```

---

## 🚀 Deploy to Vertex AI Agent Engine

```bash
# Set up GCP
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Deploy
python agent_engine_deploy.py --project YOUR_PROJECT_ID --location us-central1

# Test deployed engine
python agent_engine_deploy.py --test --project YOUR_PROJECT_ID \
    --engine-id projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/ENGINE_ID
```

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| Agent Framework | Google ADK (`google-adk`) |
| Agent Hosting | Vertex AI Agent Engine (Reasoning Engine) |
| LLM | Gemini 2.0 Flash |
| Data | BigQuery + Synthetic JSON |
| Weather | Open-Meteo API (free, no key) |
| Forecasting | Rule-based Python + Gemini heuristics |
| Dashboard | Streamlit |
| Observability | ADK tracing + Cloud Logging |

---

## 📊 Demo Scenario

> **"Store A — 120 chicken packs, expiry in 2 days, heatwave incoming"**

1. 🔍 WasteForecaster detects: 80 units projected unsold (67% waste risk), heatwave accelerates spoilage
2. 🧠 WasteDecisionEngine simulates:
   - 20% discount → margin 38.2%, saves £67.20
   - Transfer 40 units to ST003 → net saving £48.80
   - Loyalty coupon → 60 redemptions, £12.40 net benefit
3. ⚡ ActionExecutor selects: **20% discount + loyalty coupon combo** → £79.60 total saving
4. 🌍 ESG: 24kg food saved, 79.2kg CO₂ avoided, 80 meals equivalent

---

## 🌍 ESG Impact Model

- **Food saved**: `unsold_units_prevented × weight_kg`
- **CO₂ avoided**: `kg_food × 3.3` (WRAP methodology: 3.3kg CO₂eq per kg food waste)
- **Meals equivalent**: `kg_food / 0.3` (300g per meal)

---

## ⚠️ Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Vertex AI Forecasting setup | Gemini-based heuristic prediction as fallback |
| Agent Engine deployment fails | Local ADK runner + `--test-tools` mode |
| BQ latency in demo | Cached mock JSON for instant demo response |
| Multi-agent handoff breaks | Each agent independently testable |
| No API key | Full demo mode with realistic mock AI analysis |

---

## 📄 License

MIT — built for Google AI Hackathon 2026.
Made by Premsai Varma