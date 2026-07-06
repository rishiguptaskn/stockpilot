"""Module 10 — Portfolio Fit (10 rules).

Weight in aggregate: 5/100. HARD GATES: M10.1, M10.7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M10"
MODULE_NAME = "Portfolio Fit"
MODULE_WEIGHT = 5
HARD_GATE_RULE_IDS = frozenset({"M10.1", "M10.7"})


@dataclass(frozen=True)
class PortfolioContext:
    open_positions_count: int = 0
    max_open_positions: int = 5
    available_cash: float = 500_000.0
    proposed_notional: float = 0.0
    total_portfolio: float = 500_000.0
    reserve_pct: float = 5.0
    sector_pct_after_trade: float = 0.0
    single_stock_pct_after_trade: float = 0.0
    cash_pct: float = 100.0
    portfolio_sharpe_delta: float = 0.0  # + = trade improves Sharpe
    stock_already_open: bool = False
    days_since_stock_stopout: int | None = None
    portfolio_beta_after_trade: float = 1.0
    distinct_market_cap_buckets: int = 2


def _rule(fn):
    return fn


@_rule
def _p1(ctx: PortfolioContext) -> tuple[bool, str]:
    return (ctx.open_positions_count + 1) <= ctx.max_open_positions, f"open={ctx.open_positions_count}+1 max={ctx.max_open_positions}"


@_rule
def _p2(ctx: PortfolioContext) -> tuple[bool, str]:
    needed = ctx.proposed_notional + (ctx.total_portfolio * ctx.reserve_pct / 100.0)
    return ctx.available_cash >= needed, f"cash=₹{ctx.available_cash:,.0f} need=₹{needed:,.0f}"


@_rule
def _p3(ctx: PortfolioContext) -> tuple[bool, str]:
    return ctx.sector_pct_after_trade <= 40.0, f"sector %={ctx.sector_pct_after_trade:.1f}"


@_rule
def _p4(ctx: PortfolioContext) -> tuple[bool, str]:
    return ctx.single_stock_pct_after_trade <= 30.0, f"single stock %={ctx.single_stock_pct_after_trade:.1f}"


@_rule
def _p5(ctx: PortfolioContext) -> tuple[bool, str]:
    return ctx.cash_pct >= 20.0, f"cash %={ctx.cash_pct:.1f}"


@_rule
def _p6(ctx: PortfolioContext) -> tuple[bool, str]:
    """New trade doesn't materially degrade Sharpe (delta > -5%)."""
    return ctx.portfolio_sharpe_delta >= -0.05, f"Sharpe delta={ctx.portfolio_sharpe_delta*100:.1f}%"


@_rule
def _p7(ctx: PortfolioContext) -> tuple[bool, str]:
    return not ctx.stock_already_open, "no existing position" if not ctx.stock_already_open else "already have this stock"


@_rule
def _p8(ctx: PortfolioContext) -> tuple[bool, str]:
    """20 sessions since last stopout in same stock."""
    return (ctx.days_since_stock_stopout is None) or (ctx.days_since_stock_stopout >= 20), (
        f"{ctx.days_since_stock_stopout} days since stopout"
    )


@_rule
def _p9(ctx: PortfolioContext) -> tuple[bool, str]:
    return ctx.portfolio_beta_after_trade <= 1.3, f"portfolio beta={ctx.portfolio_beta_after_trade:.2f}"


@_rule
def _p10(ctx: PortfolioContext) -> tuple[bool, str]:
    return ctx.distinct_market_cap_buckets >= 2, f"market-cap buckets={ctx.distinct_market_cap_buckets}"


RULES: list[tuple[str, str, str, int, Callable[[PortfolioContext], tuple[bool, str]]]] = [
    ("M10.1",  "Positions after add ≤ max_open_positions",       "[E]",              15, _p1),
    ("M10.2",  "Cash sufficient for position + reserve",         "[E]",              12, _p2),
    ("M10.3",  "Sector concentration ≤ 40%",                      "[O]",              12, _p3),
    ("M10.4",  "Single-stock concentration ≤ 30%",                 "[E]",              10, _p4),
    ("M10.5",  "Cash allocation ≥ 20%",                            "[E] dry powder",   10, _p5),
    ("M10.6",  "New trade doesn't degrade Sharpe (>-5%)",         "portfolio theory",  8, _p6),
    ("M10.7",  "No existing position in this stock",               "[E]",              10, _p7),
    ("M10.8",  "≥ 20 sessions since last stopout in stock",        "[E]",               6, _p8),
    ("M10.9",  "Portfolio beta ≤ 1.3 after add",                    "portfolio risk",    8, _p9),
    ("M10.10", "≥ 2 distinct market-cap buckets",                  "portfolio",         5, _p10),
]


def evaluate_portfolio_fit(ctx: PortfolioContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    hard_ok = True
    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
        is_hard = rule_id in HARD_GATE_RULE_IDS
        if is_hard and not passed:
            hard_ok = False
        total_weight += weight
        if passed:
            weighted_pass += weight
        evaluations.append(RuleEvaluation(
            rule_id=rule_id, module_id=MODULE_ID, passed=passed,
            actual_value=actual, threshold=name, is_hard_gate=is_hard, source_citation=source,
        ))
    score = 100.0 * weighted_pass / total_weight if total_weight else 0.0
    return ModuleScore(
        module_id=MODULE_ID, module_name=MODULE_NAME, score=round(score, 2),
        weight_in_aggregate=MODULE_WEIGHT, rule_evaluations=evaluations, hard_gates_passed=hard_ok,
    )
