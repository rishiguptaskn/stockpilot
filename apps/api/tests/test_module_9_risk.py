"""Tests for Module 9 — Risk Management."""

from __future__ import annotations

from stockpilot_api.engine import evaluate_risk_management
from stockpilot_api.engine.module_9_risk import RiskContext, HARD_GATE_RULE_IDS


def _healthy_ctx(**overrides) -> RiskContext:
    """A perfectly-sized trade that should pass all hard gates."""
    base = dict(
        entry_price=1000.0,
        stop_price=950.0,    # 5% stop (< 8% cap, passes M9.7)
        target_price=1150.0, # 3:1 R:R
        shares=200,           # risk = 50 * 200 = 10,000 = 2% of 5L
        atr_14=25.0,
        capital_inr=500_000.0,
        risk_per_trade_pct=2.0,
        max_open_risk_pct=6.0,
        current_open_positions_count=0,
        current_open_risk_inr=0.0,
        last_month_pnl_pct=0.0,
        consecutive_losses=0,
        drawdown_from_peak_pct=0.0,
        is_add_to_losing_position=False,
        is_widening_existing_stop=False,
        stock_already_open=False,
        days_since_stock_last_stopout=None,
        sector_open_count=0,
        same_stock_slippage_pct=0.0,
    )
    base.update(overrides)
    return RiskContext(**base)  # type: ignore[arg-type]


def test_healthy_trade_passes_all_hard_gates() -> None:
    result = evaluate_risk_management(_healthy_ctx())
    assert result.hard_gates_passed is True
    assert result.score > 80


def test_over_2pct_risk_fails_hard_gate() -> None:
    # 500 stop distance × 200 shares = 100,000 = 20% of 5L (over 2%)
    ctx = _healthy_ctx(stop_price=500.0)
    result = evaluate_risk_management(ctx)
    m9_1 = next(r for r in result.rule_evaluations if r.rule_id == "M9.1")
    assert m9_1.passed is False
    assert m9_1.is_hard_gate is True
    assert result.hard_gates_passed is False


def test_stop_over_8pct_fails_hard_gate() -> None:
    # 10% stop = fails M9.7
    ctx = _healthy_ctx(stop_price=900.0, shares=50)  # size down to keep 2% risk
    result = evaluate_risk_management(ctx)
    m9_7 = next(r for r in result.rule_evaluations if r.rule_id == "M9.7")
    assert m9_7.passed is False


def test_bad_rr_fails_hard_gate() -> None:
    # target only 1.5R → fails M9.11
    ctx = _healthy_ctx(target_price=1075.0)  # 1.5R
    result = evaluate_risk_management(ctx)
    m9_11 = next(r for r in result.rule_evaluations if r.rule_id == "M9.11")
    assert m9_11.passed is False


def test_averaging_down_blocked() -> None:
    ctx = _healthy_ctx(is_add_to_losing_position=True)
    result = evaluate_risk_management(ctx)
    m9_18 = next(r for r in result.rule_evaluations if r.rule_id == "M9.18")
    assert m9_18.passed is False
    assert result.hard_gates_passed is False


def test_widening_stop_blocked() -> None:
    ctx = _healthy_ctx(is_widening_existing_stop=True)
    result = evaluate_risk_management(ctx)
    m9_19 = next(r for r in result.rule_evaluations if r.rule_id == "M9.19")
    assert m9_19.passed is False
    assert result.hard_gates_passed is False


def test_high_drawdown_halts_trading() -> None:
    ctx = _healthy_ctx(drawdown_from_peak_pct=25.0)
    result = evaluate_risk_management(ctx)
    m9_16 = next(r for r in result.rule_evaluations if r.rule_id == "M9.16")
    assert m9_16.passed is False


def test_open_risk_over_6pct_fails() -> None:
    # Existing 5% + new 2% = 7% > 6% cap
    ctx = _healthy_ctx(current_open_risk_inr=25_000.0)  # 5%
    result = evaluate_risk_management(ctx)
    m9_4 = next(r for r in result.rule_evaluations if r.rule_id == "M9.4")
    assert m9_4.passed is False


def test_hard_gate_rule_ids() -> None:
    """Verify hard-gate rules match spec in RULEBOOK.md."""
    assert HARD_GATE_RULE_IDS == frozenset(
        {"M9.1", "M9.2", "M9.4", "M9.5", "M9.7", "M9.11", "M9.16", "M9.18", "M9.19"}
    )


def test_all_rules_cite_source() -> None:
    result = evaluate_risk_management(_healthy_ctx())
    for r in result.rule_evaluations:
        assert r.source_citation, f"{r.rule_id} missing citation"
