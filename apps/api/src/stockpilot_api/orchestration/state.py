"""Graph state — the single typed object every node reads from and writes to.

``findings``/``stats``/``errors`` use additive reducers so parallel agent
nodes can append concurrently without clobbering each other (LangGraph merges
their partial updates).
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class ResearchState(TypedDict, total=False):
    # inputs
    ticker: str
    as_of: str  # ISO date

    # deterministic quant results (rule engine — never LLM)
    quant: dict[str, Any]  # CandidateOutput fields + module_details

    # agent outputs (parallel fan-out safe)
    findings: Annotated[list[dict[str, Any]], operator.add]  # AgentFinding dicts
    stats: Annotated[list[dict[str, Any]], operator.add]  # per-agent RunStats dicts
    errors: Annotated[list[str], operator.add]

    # deterministic gates & decision
    risk: dict[str, Any]  # {"verdict": "ok"|"veto", "reasons": [...], "plan": {...}}
    decision: dict[str, Any]  # {"action", "aggregate_score", "verdict", ...}

    # synthesis + final assembly
    synthesis: dict[str, Any]  # MasterSynthesis dict (or degraded placeholder)
    report: dict[str, Any]  # final explainable report
