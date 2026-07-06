"""Tests for Module 1 — Market Environment (15 rules)."""

from __future__ import annotations

import pandas as pd

from stockpilot_api.engine import evaluate_market_environment
from stockpilot_api.engine.module_1_market import MarketContext


def _make_ctx(
    nifty: pd.DataFrame,
    *,
    midcap: pd.DataFrame | None = None,
    smallcap: pd.DataFrame | None = None,
    vix: float = 15.0,
    fii: float = 1000.0,
    dii: float = 800.0,
    usdinr_20d: float = 0.005,
    in10y_bp_20d: float = 10.0,
    adv: int = 1200,
    dec: int = 800,
    ftd_ago: int = 10,
) -> MarketContext:
    return MarketContext(
        nifty=nifty,
        nifty_midcap=midcap if midcap is not None else nifty,
        nifty_smallcap=smallcap if smallcap is not None else nifty,
        india_vix=vix,
        fii_net_10d=fii,
        dii_net_10d=dii,
        usd_inr_change_20d=usdinr_20d,
        in10y_bp_change_20d=in10y_bp_20d,
        advance_count=adv,
        decline_count=dec,
        days_since_follow_through=ftd_ago,
    )


def test_module_1_bullish_market_passes_all_hard_gates(uptrend_ohlcv: pd.DataFrame) -> None:
    ctx = _make_ctx(uptrend_ohlcv)
    result = evaluate_market_environment(ctx)

    assert result.module_id == "M1"
    assert result.hard_gates_passed is True
    assert result.score > 80.0
    # All 15 rules evaluated
    assert len(result.rule_evaluations) == 15
    # Weight in aggregate = 15
    assert result.weight_in_aggregate == 15


def test_module_1_downtrend_fails_hard_gates(downtrend_ohlcv: pd.DataFrame) -> None:
    ctx = _make_ctx(downtrend_ohlcv, fii=-500.0, dii=-200.0)
    result = evaluate_market_environment(ctx)

    assert result.hard_gates_passed is False
    # M1.1 (close > 200 SMA) should fail
    m1_1 = next(r for r in result.rule_evaluations if r.rule_id == "M1.1")
    assert m1_1.passed is False
    assert m1_1.is_hard_gate is True


def test_module_1_distribution_days_fail_hard_gate(uptrend_ohlcv: pd.DataFrame) -> None:
    """5+ distribution days = M1.5 hard-gate failure."""
    # Force volume spikes on down days near the end
    df = uptrend_ohlcv.copy()
    n = len(df)
    # Force 6 distribution days in the last 20
    for i in range(1, 13, 2):  # every other day → 6 down-days
        idx = n - i
        df.iloc[idx, df.columns.get_loc("close")] = df.iloc[idx - 1]["close"] * 0.99  # -1%
        df.iloc[idx, df.columns.get_loc("volume")] = int(df.iloc[idx - 1]["volume"] * 1.5)

    ctx = _make_ctx(df)
    result = evaluate_market_environment(ctx)

    m1_5 = next(r for r in result.rule_evaluations if r.rule_id == "M1.5")
    assert m1_5.passed is False
    assert m1_5.is_hard_gate is True
    assert result.hard_gates_passed is False


def test_module_1_all_rules_cite_a_source(uptrend_ohlcv: pd.DataFrame) -> None:
    """Every rule must carry a source citation string per PLAN.md governance."""
    ctx = _make_ctx(uptrend_ohlcv)
    result = evaluate_market_environment(ctx)
    for r in result.rule_evaluations:
        assert r.source_citation, f"{r.rule_id} missing source citation"


def test_module_1_score_in_range(uptrend_ohlcv: pd.DataFrame) -> None:
    ctx = _make_ctx(uptrend_ohlcv)
    result = evaluate_market_environment(ctx)
    assert 0 <= result.score <= 100


def test_module_1_hard_gate_rules_ids() -> None:
    """The three hard-gate rules are explicitly M1.1, M1.4, M1.5 per RULEBOOK."""
    # Sanity: a fresh dummy uptrend should have all three passing
    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    close = pd.Series(range(100, 100 + n), index=idx).astype(float)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [1_000_000] * n,
        },
        index=idx,
    )
    ctx = _make_ctx(df)
    result = evaluate_market_environment(ctx)

    hard = {r.rule_id for r in result.rule_evaluations if r.is_hard_gate}
    assert hard == {"M1.1", "M1.4", "M1.5"}
