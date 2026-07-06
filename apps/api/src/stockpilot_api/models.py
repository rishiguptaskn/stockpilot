"""Pydantic models — mirror the shared TypeScript types in packages/types."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RuleEvaluation(BaseModel):
    """One rule evaluated for one stock on one date."""

    rule_id: str = Field(description='e.g. "M1.1", "M4.18", "P1"')
    module_id: str = Field(description='"M1".."M10" or "P" for patterns')
    passed: bool
    score: float | None = Field(None, ge=0, le=100)
    actual_value: str | float | None = None
    threshold: str | float | None = None
    is_hard_gate: bool = False
    source_citation: str = Field(description='e.g. "[O] O\'Neil, CAN SLIM"')


class ModuleScore(BaseModel):
    module_id: str
    module_name: str
    score: float = Field(ge=0, le=100)
    weight_in_aggregate: float = Field(ge=0, le=100)
    rule_evaluations: list[RuleEvaluation]
    hard_gates_passed: bool


Verdict = Literal["candidate", "watch", "reject"]


class TradeCandidate(BaseModel):
    ticker: str
    candidate_date: date
    aggregate_score: float = Field(ge=0, le=100)
    module_scores: list[ModuleScore]
    hard_gates_all_passed: bool
    verdict: Verdict
    suggested_entry: float | None = None
    suggested_stop: float | None = None
    suggested_target: float | None = None
    suggested_shares: int | None = None
    detected_patterns: list[str] = Field(default_factory=list)
