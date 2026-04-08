"""
agents package — Multi-agent system for the Dynamic Waste Reduction Engine.

Agents:
  DemandForecastingAgent    — Vertex AI demand forecasting with historical + weather signals
  WasteRiskAgent            — Multi-factor composite risk scoring
  PricingAgent              — Elasticity-driven optimal discount finder
  TransferAgent             — Cross-store transfer coordination
  DecisionOptimizationAgent — Multi-constraint action optimizer
  ActionExecutor            — Execution logging and audit
  ExplanationAgent          — RAG-grounded decision explanations
  WasteReductionOrchestrator — Central coordinator (root_agent)
"""


def _load_root():
    from agents.orchestrator import root_agent
    return root_agent


__all__ = ["_load_root"]
