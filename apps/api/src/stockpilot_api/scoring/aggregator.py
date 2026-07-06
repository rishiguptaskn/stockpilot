"""Aggregate module scores into a single verdict."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from stockpilot_api.models import ModuleScore


Verdict = Literal["candidate", "watch", "reject"]


@dataclass(frozen=True)
class ScoreVerdict:
    aggregate_score: float  # 0-100
    verdict: Verdict
    hard_gates_all_passed: bool
    module_score_map: dict[str, float]  # M1 -> 82.4, ...
    weights_used: dict[str, int]  # M1 -> 15, ...


def aggregate_scores(module_scores: list[ModuleScore]) -> ScoreVerdict:
    """
    Combine per-module scores into an aggregate score + verdict.

    - Aggregate = sum(score × weight) / sum(weights).
    - If ANY module reports hard_gates_passed=False → aggregate forced to 0 → verdict=reject.
    - Verdict thresholds: ≥ 90 candidate; 85-89 watch; else reject.

    An empty input returns verdict=reject with score 0.
    """
    if not module_scores:
        return ScoreVerdict(
            aggregate_score=0.0,
            verdict="reject",
            hard_gates_all_passed=False,
            module_score_map={},
            weights_used={},
        )

    hard_gates_ok = all(m.hard_gates_passed for m in module_scores)
    score_map = {m.module_id: m.score for m in module_scores}
    weight_map = {m.module_id: int(m.weight_in_aggregate) for m in module_scores}

    if not hard_gates_ok:
        return ScoreVerdict(
            aggregate_score=0.0,
            verdict="reject",
            hard_gates_all_passed=False,
            module_score_map=score_map,
            weights_used=weight_map,
        )

    total_weight = sum(weight_map.values())
    if total_weight == 0:
        return ScoreVerdict(
            aggregate_score=0.0,
            verdict="reject",
            hard_gates_all_passed=True,
            module_score_map=score_map,
            weights_used=weight_map,
        )

    weighted_sum = sum(m.score * m.weight_in_aggregate for m in module_scores)
    aggregate = weighted_sum / total_weight

    verdict: Verdict
    if aggregate >= 90:
        verdict = "candidate"
    elif aggregate >= 85:
        verdict = "watch"
    else:
        verdict = "reject"

    return ScoreVerdict(
        aggregate_score=round(aggregate, 2),
        verdict=verdict,
        hard_gates_all_passed=True,
        module_score_map=score_map,
        weights_used=weight_map,
    )
