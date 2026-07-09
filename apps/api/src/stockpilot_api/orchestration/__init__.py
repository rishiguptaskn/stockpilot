"""LangGraph research orchestration (ARCHITECTURE.md §10-11).

Graph shape:  quant → [agent fan-out] → risk gate (deterministic, veto)
              → decision (deterministic) → chief analyst (synthesis)
              → explainability → END

Deterministic modules are nodes/tools, never LLM calls. Agents exist only
where natural-language reasoning is required, and only where real data
exists — no fake agents emitting fabricated findings.
"""

from stockpilot_api.orchestration.graph import build_research_graph, run_research
from stockpilot_api.orchestration.state import ResearchState

__all__ = ["ResearchState", "build_research_graph", "run_research"]
