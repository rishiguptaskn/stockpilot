"""Research graph assembly (ARCHITECTURE.md §11.1).

    START → quant → [agent fan-out] → risk → decision → chief → explain → END

Adding a future agent (fundamental, news, …) is two lines:
    g.add_edge("quant", "new_agent"); g.add_edge("new_agent", "risk")
``findings`` uses an additive reducer, so parallel branches merge safely.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from langgraph.graph import END, START, StateGraph

from stockpilot_api.llm.client import LLMTransport
from stockpilot_api.llm.config import LLMConfig
from stockpilot_api.orchestration.nodes import (
    make_chief_node,
    make_decision_node,
    make_explain_node,
    make_quant_node,
    make_risk_node,
    make_technical_node,
)
from stockpilot_api.orchestration.state import ResearchState


def build_research_graph(
    transport: LLMTransport,
    config: LLMConfig,
    *,
    period: str = "2y",
    capital_inr: float = 500_000.0,
):
    """Compile the research graph. Deterministic nodes need no transport."""
    g = StateGraph(ResearchState)
    g.add_node("quant", make_quant_node(period=period, capital_inr=capital_inr))
    g.add_node("technical", make_technical_node(transport, config))
    g.add_node("risk", make_risk_node())
    g.add_node("decision", make_decision_node())
    g.add_node("chief", make_chief_node(transport, config))
    g.add_node("explain", make_explain_node())

    g.add_edge(START, "quant")
    # agent fan-out: every analysis agent hangs off "quant" and joins at "risk"
    g.add_edge("quant", "technical")
    g.add_edge("technical", "risk")
    g.add_edge("risk", "decision")
    g.add_edge("decision", "chief")
    g.add_edge("chief", "explain")
    g.add_edge("explain", END)
    return g.compile()


def run_research(
    ticker: str,
    transport: LLMTransport,
    config: LLMConfig,
    *,
    period: str = "2y",
    capital_inr: float = 500_000.0,
) -> dict[str, Any]:
    """Run one full research pass for a ticker and return the final report."""
    graph = build_research_graph(transport, config, period=period, capital_inr=capital_inr)
    final: ResearchState = graph.invoke(
        {"ticker": ticker.upper(), "as_of": date.today().isoformat()}
    )
    return final["report"]
