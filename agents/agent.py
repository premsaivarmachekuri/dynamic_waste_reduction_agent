# ADK entry point — must be named agent.py for adk CLI to discover root_agent
from agents.orchestrator import root_agent

__all__ = ["root_agent"]
