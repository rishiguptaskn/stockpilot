"""Module 9 — Risk Management (25 rules).

Weight in aggregate: 10/100. HARD GATES: M9.1, M9.2, M9.4, M9.5, M9.7, M9.11, M9.16, M9.18, M9.19.

Elder-first risk management: 2% per trade, 6% total open risk, tighten-only stops.

See docs/RULEBOOK.md § Module 9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M9"
MODULE_NAME = "Risk Management"
MODULE_WEIGHT = 10
HARD_GATE_RULE_IDS = frozenset(
    {"M9.1", "M9.2", "M9.4", "M9.5", "M9.7", "M9.11", "M9.16", "M9.18", "M9.19"}
)


@dataclass(frozen=True)
class RiskContext:
    """
    A specific proposed trade + current portfolio state.

    All amounts in ₹.
    """

    # Proposed trade
    entry_price: float
    stop_price: float
    target_price: float | None
    shares: int
    atr_14: float | None = None

    # Portfolio state
    capital_inr: float = 500_000.0
    risk_per_trade_pct: float = 2.0
    max_open_risk_pct: float = 6.0
    max_open_positions: int = 5
    current_open_positions_count: int = 0
    current_open_risk_inr: float = 0.0

    # Rolling loss/DD state
    last_month_pnl_pct: float = 0.0
    consecutive_losses: int = 0
    drawdown_from_peak_pct: float = 0.0

    # Position lifecycle
    is_add_to_losing_position: bool = False
    is_widening_existing_stop: bool = False

    # Trade meta
    stock_already_open: bool = False
    days_since_stock_last_stopout: int | None = None  # None = never stopped out
    sector_open_count: int = 0
    same_stock_slippage_pct: float = 0.0


def _rule_m9_1(ctx: RiskContext) -> tuple[bool, str]:
    """Trade risk ≤ 2% of capital."""
    risk = (ctx.entry_price - ctx.stop_price) * ctx.shares
    cap = ctx.capital_inr * ctx.risk_per_trade_pct / 100.0
    return risk <= cap, f"risk=₹{risk:.0f}, cap=₹{cap:.0f}"


def _rule_m9_2(ctx: RiskContext) -> tuple[bool, str]:
    """Shares auto-calculated to fit 2% risk (floor)."""
    stop_distance = ctx.entry_price - ctx.stop_price
    if stop_distance <= 0:
        return False, "invalid stop distance"
    expected_shares = int((ctx.capital_inr * ctx.risk_per_trade_pct / 100.0) // stop_distance)
    # Trade must not have MORE shares than the auto-calc allows
    return ctx.shares <= expected_shares, f"shares={ctx.shares}, max={expected_shares}"


def _rule_m9_3(ctx: RiskContext) -> tuple[bool, str]:
    """Notional ≤ 30% of capital in a single stock."""
    notional = ctx.entry_price * ctx.shares
    cap = ctx.capital_inr * 0.30
    return notional <= cap, f"notional=₹{notional:.0f}, cap=₹{cap:.0f}"


def _rule_m9_4(ctx: RiskContext) -> tuple[bool, str]:
    """Total open risk ≤ 6% of capital."""
    new_trade_risk = (ctx.entry_price - ctx.stop_price) * ctx.shares
    total = ctx.current_open_risk_inr + new_trade_risk
    cap = ctx.capital_inr * ctx.max_open_risk_pct / 100.0
    return total <= cap, f"total risk=₹{total:.0f}, cap=₹{cap:.0f}"


def _rule_m9_5(ctx: RiskContext) -> tuple[bool, str]:
    """After adding this trade, open risk still ≤ 6%."""
    return _rule_m9_4(ctx)  # same check


def _rule_m9_6(ctx: RiskContext) -> tuple[bool, str]:
    """No new positions in month if last month lost > 4%."""
    return ctx.last_month_pnl_pct >= -4.0, f"last_month_pnl={ctx.last_month_pnl_pct:.2f}%"


def _rule_m9_7(ctx: RiskContext) -> tuple[bool, str]:
    """Stop-loss ≤ 8% below entry (O'Neil hard cap)."""
    stop_pct = (ctx.entry_price - ctx.stop_price) / ctx.entry_price * 100.0
    return stop_pct <= 8.0, f"stop={stop_pct:.2f}% below entry"


def _rule_m9_8(ctx: RiskContext) -> tuple[bool, str]:
    """Stop placed below a technical level. (Placeholder — needs technical context)."""
    # In production, we'd check against recent swing_low, sma_50, ema_20 - ATR, etc.
    # For now, ensure stop distance is at least "meaningful" (> 1% below entry)
    stop_pct = (ctx.entry_price - ctx.stop_price) / ctx.entry_price * 100.0
    return stop_pct >= 1.0, f"stop={stop_pct:.2f}% below entry (needs technical anchor)"


def _rule_m9_9(ctx: RiskContext) -> tuple[bool, str]:
    """Stop ≥ 1× ATR below entry."""
    if ctx.atr_14 is None or ctx.atr_14 <= 0:
        return True, "no ATR provided (skipped)"
    dist = ctx.entry_price - ctx.stop_price
    return dist >= ctx.atr_14, f"stop distance={dist:.2f}, ATR={ctx.atr_14:.2f}"


def _rule_m9_10(ctx: RiskContext) -> tuple[bool, str]:
    """Stop ≤ 3× ATR below entry."""
    if ctx.atr_14 is None or ctx.atr_14 <= 0:
        return True, "no ATR provided (skipped)"
    dist = ctx.entry_price - ctx.stop_price
    return dist <= 3.0 * ctx.atr_14, f"stop distance={dist:.2f}, 3×ATR={3*ctx.atr_14:.2f}"


def _rule_m9_11(ctx: RiskContext) -> tuple[bool, str]:
    """R:R >= 2:1."""
    if ctx.target_price is None:
        return False, "no target set"
    rr = (ctx.target_price - ctx.entry_price) / (ctx.entry_price - ctx.stop_price)
    return rr >= 2.0, f"R:R=1:{rr:.2f}"


def _rule_m9_12(ctx: RiskContext) -> tuple[bool, str]:
    """R:R >= 3:1 preferred (bonus)."""
    if ctx.target_price is None:
        return False, "no target set"
    rr = (ctx.target_price - ctx.entry_price) / (ctx.entry_price - ctx.stop_price)
    return rr >= 3.0, f"R:R=1:{rr:.2f}"


def _rule_m9_13(ctx: RiskContext) -> tuple[bool, str]:
    """Not already 3+ stocks in same sector."""
    return ctx.sector_open_count < 3, f"sector open count={ctx.sector_open_count}"


def _rule_m9_14(ctx: RiskContext) -> tuple[bool, str]:
    """Correlation < 0.85 with any current holding. (Placeholder — needs price data.)"""
    return True, "correlation check not yet implemented"


def _rule_m9_15(ctx: RiskContext) -> tuple[bool, str]:
    """Drawdown from peak ≤ 10%, else halve risk."""
    return ctx.drawdown_from_peak_pct <= 10.0, f"drawdown={ctx.drawdown_from_peak_pct:.2f}%"


def _rule_m9_16(ctx: RiskContext) -> tuple[bool, str]:
    """Drawdown > 20% → HALT (hard gate)."""
    return ctx.drawdown_from_peak_pct <= 20.0, f"drawdown={ctx.drawdown_from_peak_pct:.2f}%"


def _rule_m9_17(ctx: RiskContext) -> tuple[bool, str]:
    """Max 3 losing trades in a row (else force review)."""
    return ctx.consecutive_losses < 3, f"consecutive_losses={ctx.consecutive_losses}"


def _rule_m9_18(ctx: RiskContext) -> tuple[bool, str]:
    """Never add to a losing position."""
    return not ctx.is_add_to_losing_position, "no averaging down" if not ctx.is_add_to_losing_position else "averaging down blocked"


def _rule_m9_19(ctx: RiskContext) -> tuple[bool, str]:
    """Never widen a stop."""
    return not ctx.is_widening_existing_stop, "not widening" if not ctx.is_widening_existing_stop else "widening blocked"


def _rule_m9_20(ctx: RiskContext) -> tuple[bool, str]:
    """Booked partial at 2R (advisory)."""
    return True, "advisory — not gating"


def _rule_m9_21(ctx: RiskContext) -> tuple[bool, str]:
    """Trail stop to breakeven after 1R (advisory)."""
    return True, "advisory — not gating"


def _rule_m9_22(ctx: RiskContext) -> tuple[bool, str]:
    """Sizing modifier for borderline candidates (advisory)."""
    return True, "advisory — not gating"


def _rule_m9_23(ctx: RiskContext) -> tuple[bool, str]:
    """Slippage ≤ 0.5% of entry."""
    return ctx.same_stock_slippage_pct <= 0.5, f"slippage={ctx.same_stock_slippage_pct:.2f}%"


def _rule_m9_24(ctx: RiskContext) -> tuple[bool, str]:
    """Shares floored to fit risk budget (checked via M9.2 already, always passes if M9.2 does)."""
    return True, "handled by shares calculation"


def _rule_m9_25(ctx: RiskContext) -> tuple[bool, str]:
    """Position >= 10 shares."""
    return ctx.shares >= 10, f"shares={ctx.shares}"


RULES: list[tuple[str, str, str, int, Callable[[RiskContext], tuple[bool, str]]]] = [
    ("M9.1",  "Risk ≤ 2% of capital (Elder)",             "[E] 2% rule",          15, _rule_m9_1),
    ("M9.2",  "Shares fit 2% risk (floor)",                "[E] position sizing",  10, _rule_m9_2),
    ("M9.3",  "Notional ≤ 30% of capital",                 "[E] concentration",     6, _rule_m9_3),
    ("M9.4",  "Total open risk ≤ 6%",                       "[E] 6% rule",          15, _rule_m9_4),
    ("M9.5",  "Open risk after add ≤ 6%",                   "[E] 6% rule",          10, _rule_m9_5),
    ("M9.6",  "No new trades if last month < -4%",          "[E] cooling-off",       6, _rule_m9_6),
    ("M9.7",  "Stop ≤ 8% below entry",                      "[O] 7-8% max",         10, _rule_m9_7),
    ("M9.8",  "Stop below a technical level",               "[Mu][Mv]",              6, _rule_m9_8),
    ("M9.9",  "Stop ≥ 1× ATR",                              "[E][Mv]",               5, _rule_m9_9),
    ("M9.10", "Stop ≤ 3× ATR",                              "[E]",                   4, _rule_m9_10),
    ("M9.11", "R:R ≥ 2:1",                                   "[E][O]",              12, _rule_m9_11),
    ("M9.12", "R:R ≥ 3:1 (bonus)",                          "[O] preferred",         6, _rule_m9_12),
    ("M9.13", "Sector concentration < 3 positions",         "[O]",                   5, _rule_m9_13),
    ("M9.14", "Correlation < 0.85 (placeholder)",           "[E]",                   4, _rule_m9_14),
    ("M9.15", "Drawdown ≤ 10% (else halve)",                "[E] drawdown-aware",    5, _rule_m9_15),
    ("M9.16", "Drawdown ≤ 20% (else HALT)",                 "[E] escalation gate",   6, _rule_m9_16),
    ("M9.17", "< 3 consecutive losses (else review)",       "[E][Dg]",               4, _rule_m9_17),
    ("M9.18", "No averaging down",                          "[E][O]",               10, _rule_m9_18),
    ("M9.19", "No widening of stop",                        "[E]",                  10, _rule_m9_19),
    ("M9.20", "Partial booked at 2R (advisory)",            "[Mv]",                  3, _rule_m9_20),
    ("M9.21", "Trail to breakeven at 1R (advisory)",        "[E][Mv]",               4, _rule_m9_21),
    ("M9.22", "Size modifier for borderline (advisory)",    "[Mv][E]",               3, _rule_m9_22),
    ("M9.23", "Slippage ≤ 0.5%",                             "[E]",                   4, _rule_m9_23),
    ("M9.24", "Shares floored (never rounded up)",          "[E]",                   3, _rule_m9_24),
    ("M9.25", "Shares ≥ 10 (cost floor)",                   "[E]",                   2, _rule_m9_25),
]


def evaluate_risk_management(ctx: RiskContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    hard_gate_ok = True

    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
        is_hard = rule_id in HARD_GATE_RULE_IDS
        if is_hard and not passed:
            hard_gate_ok = False
        total_weight += weight
        if passed:
            weighted_pass += weight
        evaluations.append(
            RuleEvaluation(
                rule_id=rule_id,
                module_id=MODULE_ID,
                passed=passed,
                actual_value=actual,
                threshold=name,
                is_hard_gate=is_hard,
                source_citation=source,
            )
        )

    score = 100.0 * weighted_pass / total_weight if total_weight else 0.0
    return ModuleScore(
        module_id=MODULE_ID,
        module_name=MODULE_NAME,
        score=round(score, 2),
        weight_in_aggregate=MODULE_WEIGHT,
        rule_evaluations=evaluations,
        hard_gates_passed=hard_gate_ok,
    )
