"""Tests for the scoring aggregator."""

from __future__ import annotations

from stockpilot_api.models import ModuleScore
from stockpilot_api.scoring import aggregate_scores


def _mod(id_: str, score: float, weight: int, hard_ok: bool = True) -> ModuleScore:
    return ModuleScore(
        module_id=id_,
        module_name=id_,
        score=score,
        weight_in_aggregate=weight,
        rule_evaluations=[],
        hard_gates_passed=hard_ok,
    )


def test_aggregate_scores_weighted_mean() -> None:
    """Verify weighted mean: two modules 100/50 with weights 60/40 → 80."""
    mods = [
        _mod("M1", 100.0, 60),
        _mod("M2", 50.0, 40),
    ]
    verdict = aggregate_scores(mods)
    assert verdict.aggregate_score == 80.0
    assert verdict.verdict == "reject"  # 80 < 85


def test_candidate_verdict_at_90() -> None:
    mods = [_mod("M1", 92.0, 100)]
    verdict = aggregate_scores(mods)
    assert verdict.aggregate_score == 92.0
    assert verdict.verdict == "candidate"


def test_watch_verdict_between_85_and_89() -> None:
    mods = [_mod("M1", 87.5, 100)]
    verdict = aggregate_scores(mods)
    assert verdict.aggregate_score == 87.5
    assert verdict.verdict == "watch"


def test_hard_gate_failure_forces_reject() -> None:
    """Even score 100, if any module reports hard_gates_passed=False → reject."""
    mods = [
        _mod("M1", 100.0, 50, hard_ok=False),
        _mod("M2", 100.0, 50, hard_ok=True),
    ]
    verdict = aggregate_scores(mods)
    assert verdict.hard_gates_all_passed is False
    assert verdict.aggregate_score == 0.0
    assert verdict.verdict == "reject"


def test_empty_input_rejects() -> None:
    verdict = aggregate_scores([])
    assert verdict.verdict == "reject"
    assert verdict.aggregate_score == 0.0


def test_module_score_map_populated() -> None:
    mods = [_mod("M1", 90, 50), _mod("M9", 85, 50)]
    verdict = aggregate_scores(mods)
    assert verdict.module_score_map == {"M1": 90.0, "M9": 85.0}
    assert verdict.weights_used == {"M1": 50, "M9": 50}
