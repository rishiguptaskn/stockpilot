"""Tests for Module 5 — Moving Averages."""

from __future__ import annotations

import pandas as pd

from stockpilot_api.engine import evaluate_moving_averages
from stockpilot_api.engine.module_5_moving_averages import MovingAveragesContext


def test_module_5_strong_uptrend_scores_high(uptrend_ohlcv: pd.DataFrame) -> None:
    ctx = MovingAveragesContext(daily=uptrend_ohlcv, rs_rank_252=85.0)
    result = evaluate_moving_averages(ctx)

    assert result.module_id == "M5"
    assert result.module_name == "Moving Averages"
    assert result.weight_in_aggregate == 10
    assert len(result.rule_evaluations) == 20
    assert result.score > 70  # a healthy uptrend should pass most rules
    assert result.hard_gates_passed is True  # M5 has no hard gates


def test_module_5_downtrend_scores_low(downtrend_ohlcv: pd.DataFrame) -> None:
    ctx = MovingAveragesContext(daily=downtrend_ohlcv, rs_rank_252=20.0)
    result = evaluate_moving_averages(ctx)

    # Multiple Trend Template checks should fail
    tt1 = next(r for r in result.rule_evaluations if r.rule_id == "M5.1")
    assert tt1.passed is False


def test_module_5_all_rules_cite_source(uptrend_ohlcv: pd.DataFrame) -> None:
    ctx = MovingAveragesContext(daily=uptrend_ohlcv, rs_rank_252=85.0)
    result = evaluate_moving_averages(ctx)
    for r in result.rule_evaluations:
        assert r.source_citation, f"{r.rule_id} missing citation"


def test_module_5_low_rs_rank_fails_tt8(uptrend_ohlcv: pd.DataFrame) -> None:
    ctx = MovingAveragesContext(daily=uptrend_ohlcv, rs_rank_252=50.0)
    result = evaluate_moving_averages(ctx)
    tt8 = next(r for r in result.rule_evaluations if r.rule_id == "M5.8")
    assert tt8.passed is False
