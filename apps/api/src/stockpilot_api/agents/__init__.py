"""Agent runtime — Master orchestrator + domain specialists.

Every agent is a bounded Claude tool-use loop (``BaseAgent``) that reasons only
over data returned by MCP tools and emits a schema-validated structured output.
"""

from stockpilot_api.agents.base import AgentError, AgentResult, BaseAgent, RunStats
from stockpilot_api.agents.master import MasterAgent
from stockpilot_api.agents.schemas import (
    DISCLAIMER,
    AgentFinding,
    Evidence,
    ResearchReport,
)
from stockpilot_api.agents.technical import TechnicalAnalysisAgent

__all__ = [
    "BaseAgent",
    "AgentError",
    "AgentResult",
    "RunStats",
    "MasterAgent",
    "TechnicalAnalysisAgent",
    "AgentFinding",
    "Evidence",
    "ResearchReport",
    "DISCLAIMER",
]
