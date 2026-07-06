"""Module 2 — Sector Strength (10 rules).

Weight in aggregate: 10/100. No hard gates.

Rationale [O]: "The right stock in the wrong industry group won't work."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from stockpilot_api.indicators import sma
from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M2"
MODULE_NAME = "Sector Strength"
MODULE_WEIGHT = 10


@dataclass(frozen=True)
class SectorContext:
    sector_daily: pd.DataFrame  # OHLCV for sector index
    nifty_daily: pd.DataFrame  # for comparison
    sector_rs_rank: float  # percentile 0-100 vs other sectors
    sector_adx_14: float
    peer_new_highs_last_5d: int  # count of stocks in sector making new 52w highs


def _rule(fn: Callable[[SectorContext], tuple[bool, str]]) -> Callable[[SectorContext], tuple[bool, str]]:
    return fn


@_rule
def _m2_1(ctx: SectorContext) -> tuple[bool, str]:
    close = ctx.sector_daily["close"]
    s50 = sma(close, 50).iloc[-1]
    return bool(close.iloc[-1] > s50), f"close={close.iloc[-1]:.2f}, sma50={s50:.2f}"


@_rule
def _m2_2(ctx: SectorContext) -> tuple[bool, str]:
    close = ctx.sector_daily["close"]
    s200 = sma(close, 200).iloc[-1]
    return bool(close.iloc[-1] > s200), f"close={close.iloc[-1]:.2f}, sma200={s200:.2f}"


@_rule
def _m2_3(ctx: SectorContext) -> tuple[bool, str]:
    """Sector outperforming Nifty over 3 months."""
    if len(ctx.sector_daily) < 63 or len(ctx.nifty_daily) < 63:
        return False, "insufficient history"
    s = ctx.sector_daily["close"].iloc[-1] / ctx.sector_daily["close"].iloc[-63] - 1
    n = ctx.nifty_daily["close"].iloc[-1] / ctx.nifty_daily["close"].iloc[-63] - 1
    return s > n, f"sector 63d={s*100:.1f}%, nifty={n*100:.1f}%"


@_rule
def _m2_4(ctx: SectorContext) -> tuple[bool, str]:
    """Sector outperforming Nifty over 1 month."""
    if len(ctx.sector_daily) < 21 or len(ctx.nifty_daily) < 21:
        return False, "insufficient history"
    s = ctx.sector_daily["close"].iloc[-1] / ctx.sector_daily["close"].iloc[-21] - 1
    n = ctx.nifty_daily["close"].iloc[-1] / ctx.nifty_daily["close"].iloc[-21] - 1
    return s > n, f"sector 21d={s*100:.1f}%, nifty={n*100:.1f}%"


@_rule
def _m2_5(ctx: SectorContext) -> tuple[bool, str]:
    return ctx.sector_rs_rank >= 70, f"sector RS rank={ctx.sector_rs_rank:.1f}"


@_rule
def _m2_6(ctx: SectorContext) -> tuple[bool, str]:
    """Not parabolic (63d < 40%). TUNABLE."""
    if len(ctx.sector_daily) < 63:
        return True, "insufficient history — assume ok"
    s = ctx.sector_daily["close"].iloc[-1] / ctx.sector_daily["close"].iloc[-63] - 1
    return s < 0.40, f"sector 63d={s*100:.1f}%"


@_rule
def _m2_7(ctx: SectorContext) -> tuple[bool, str]:
    """50 SMA sloping up (10d)."""
    if len(ctx.sector_daily) < 60:
        return False, "insufficient history"
    s50 = sma(ctx.sector_daily["close"], 50)
    return bool(s50.iloc[-1] > s50.iloc[-11]), f"50sma today={s50.iloc[-1]:.2f} vs 10d ago={s50.iloc[-11]:.2f}"


@_rule
def _m2_8(ctx: SectorContext) -> tuple[bool, str]:
    """3+ stocks in sector making new 52w highs in last 5 days. TUNABLE."""
    return ctx.peer_new_highs_last_5d >= 3, f"{ctx.peer_new_highs_last_5d} peers at new highs"


@_rule
def _m2_9(ctx: SectorContext) -> tuple[bool, str]:
    """Sector ADX ≥ 20 (trending)."""
    return ctx.sector_adx_14 >= 20, f"ADX={ctx.sector_adx_14:.1f}"


@_rule
def _m2_10(ctx: SectorContext) -> tuple[bool, str]:
    """Sector not worst 20% (RS rank > 20)."""
    return ctx.sector_rs_rank > 20, f"sector RS rank={ctx.sector_rs_rank:.1f}"


RULES: list[tuple[str, str, str, int, Callable[[SectorContext], tuple[bool, str]]]] = [
    ("M2.1",  "Sector > 50 SMA",                       "[O] leading sectors",  12, _m2_1),
    ("M2.2",  "Sector > 200 SMA",                       "[W] Stage 2 sector",   12, _m2_2),
    ("M2.3",  "Sector outperforms Nifty (3mo)",         "[O] the 'L'",          15, _m2_3),
    ("M2.4",  "Sector outperforms Nifty (1mo)",         "[O] momentum",         10, _m2_4),
    ("M2.5",  "Sector RS rank ≥ 70",                     "[O] RS methodology",   15, _m2_5),
    ("M2.6",  "Sector not parabolic (<40% in 63d)",     "[W] Stage 3 warn",      8, _m2_6),
    ("M2.7",  "Sector 50 SMA sloping up",                "[W] rising trend",    10, _m2_7),
    ("M2.8",  "3+ peer stocks at new 52w highs",         "[O] themes in groups", 8, _m2_8),
    ("M2.9",  "Sector ADX ≥ 20 (trending)",              "[Mu]",                 5, _m2_9),
    ("M2.10", "Sector not in bottom 20%",                 "[O]",                  5, _m2_10),
]


def evaluate_sector_strength(ctx: SectorContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
        total_weight += weight
        if passed:
            weighted_pass += weight
        evaluations.append(RuleEvaluation(
            rule_id=rule_id, module_id=MODULE_ID, passed=passed,
            actual_value=actual, threshold=name, is_hard_gate=False, source_citation=source,
        ))
    score = 100.0 * weighted_pass / total_weight if total_weight else 0.0
    return ModuleScore(
        module_id=MODULE_ID, module_name=MODULE_NAME, score=round(score, 2),
        weight_in_aggregate=MODULE_WEIGHT, rule_evaluations=evaluations, hard_gates_passed=True,
    )
