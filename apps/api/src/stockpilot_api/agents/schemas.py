"""Structured outputs for the agent layer.

These Pydantic models are the *contract* between the LLM and the rest of the
system. Agents don't return free text — they are forced to emit one of these
via a terminal "submit" tool, and the tool-call layer validates before we ever
trust the output. Mirrored in ``packages/types/src/agents.ts``.

Design note — the anti-fabrication invariant: every ``Evidence`` names the
``source_tool`` that produced its data. A finding with claims but no evidence,
or evidence with no source tool, fails validation. This makes "the model made
a number up" structurally hard rather than a matter of prompt discipline.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Stance = Literal["bullish", "neutral", "bearish"]

# Attached server-side to every report (never model-generated) — see FR6.
DISCLAIMER = (
    "StockPilot is a decision-support tool, not investment advice. It does not "
    "predict prices and does not guarantee profits. All analysis is derived from "
    "historical/technical data and carries uncertainty. You make the final trading "
    "decision. Prioritise preserving capital."
)


class Evidence(BaseModel):
    """One factual claim, tied to the tool that produced its data."""

    claim: str = Field(description="A specific, data-backed observation.")
    source_tool: str = Field(
        description="The MCP tool whose output this claim is derived from, e.g. 'detect_patterns'."
    )
    rule_id: str | None = Field(
        default=None, description="Engine rule id when applicable, e.g. 'M5.3'."
    )
    citation: str | None = Field(
        default=None, description="Source citation carried from the rule, e.g. \"[O] O'Neil\"."
    )


class AgentFinding(BaseModel):
    """A single domain agent's verdict on a ticker."""

    agent_name: str
    stance: Stance
    confidence: float = Field(ge=0, le=1, description="0-1 confidence in the stance.")
    summary: str = Field(description="2-4 sentence plain-English read of the setup.")
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Data-backed observations supporting the stance. Empty only if data unavailable.",
    )
    invalidation: str = Field(
        description="The concrete condition that would invalidate this view (e.g. a price level)."
    )
    data_available: bool = Field(
        default=True,
        description="False when tools could not return the data needed to form a view.",
    )


class ResearchReport(BaseModel):
    """The Master agent's synthesis across all domain findings."""

    ticker: str
    as_of: date
    overall_stance: Stance
    confidence: float = Field(ge=0, le=1)
    master_synthesis: str = Field(
        description="Composed narrative across findings. Must NOT introduce new numbers."
    )
    findings: list[AgentFinding]
    uncertainties: list[str] = Field(
        default_factory=list,
        description="What is NOT known/covered — coverage gaps, stale data, low-confidence areas.",
    )
    aggregate_score: float | None = None
    verdict: str | None = None
    disclaimer: str = DISCLAIMER
    generated_at: str | None = None  # set server-side (ISO-8601)
