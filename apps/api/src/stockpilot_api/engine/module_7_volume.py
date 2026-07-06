"""Module 7 — Volume Analysis (15 rules).

Weight in aggregate: 10/100. HARD GATE: M7.1 (liquidity floor).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M7"
MODULE_NAME = "Volume Analysis"
MODULE_WEIGHT = 10
HARD_GATE_RULE_IDS = frozenset({"M7.1"})


@dataclass(frozen=True)
class VolumeContext:
    daily: pd.DataFrame  # must include volume + delivery_pct if available
    latest_delivery_pct: float | None = None


def _rule(fn):
    return fn


@_rule
def _v1(ctx: VolumeContext) -> tuple[bool, str]:
    """Avg daily turnover ≥ ₹5 crore (5,00,00,000)."""
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    tail = ctx.daily.tail(50)
    turnover = (tail["close"] * tail["volume"]).mean()
    return bool(turnover >= 50_000_000), f"turnover ₹{turnover/10_000_000:.2f} cr"


@_rule
def _v2(ctx: VolumeContext) -> tuple[bool, str]:
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    avg_vol = ctx.daily["volume"].tail(50).mean()
    return bool(avg_vol >= 100_000), f"50d avg vol={avg_vol:,.0f}"


@_rule
def _v3(ctx: VolumeContext) -> tuple[bool, str]:
    """Latest vol ≥ 1.5× 50d avg."""
    if len(ctx.daily) < 51:
        return False, "insufficient history"
    avg = ctx.daily["volume"].iloc[-51:-1].mean()
    return bool(ctx.daily["volume"].iloc[-1] >= avg * 1.5), f"latest={ctx.daily['volume'].iloc[-1]:,} vs 50d avg={avg:,.0f}"


@_rule
def _v4(ctx: VolumeContext) -> tuple[bool, str]:
    """Up-day volume > down-day volume in trailing 20."""
    if len(ctx.daily) < 20:
        return False, "insufficient history"
    tail = ctx.daily.tail(20)
    up_days = tail[tail["close"] > tail["open"]]
    down_days = tail[tail["close"] < tail["open"]]
    up_v = up_days["volume"].sum() if len(up_days) else 0
    dn_v = down_days["volume"].sum() if len(down_days) else 0
    return bool(up_v > dn_v), f"up_vol={up_v:,} dn_vol={dn_v:,}"


@_rule
def _v5(ctx: VolumeContext) -> tuple[bool, str]:
    """≥ 3 power up-days (close +2%, vol 1.5× avg) in last 20."""
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    tail = ctx.daily.tail(20)
    avg = ctx.daily["volume"].tail(50).mean()
    prev_close = ctx.daily["close"].shift(1).tail(20)
    up_pct = (tail["close"] / prev_close - 1) * 100
    strong = ((up_pct > 2.0) & (tail["volume"] > avg * 1.5)).sum()
    return int(strong) >= 3, f"{strong} strong up-days"


@_rule
def _v6(ctx: VolumeContext) -> tuple[bool, str]:
    """Distribution days ≤ 3 (stock-level)."""
    if len(ctx.daily) < 21:
        return False, "insufficient history"
    tail = ctx.daily.tail(20).copy()
    prev_close = ctx.daily["close"].shift(1).tail(20)
    prev_vol = ctx.daily["volume"].shift(1).tail(20)
    down_days = ((tail["close"] / prev_close - 1) < -0.002) & (tail["volume"] > prev_vol)
    return int(down_days.sum()) <= 3, f"{down_days.sum()} distribution days"


@_rule
def _v7(ctx: VolumeContext) -> tuple[bool, str]:
    """Volume drying up in the base (last 10 < prior 10)."""
    if len(ctx.daily) < 20:
        return False, "insufficient history"
    last10 = ctx.daily["volume"].iloc[-10:].mean()
    prior10 = ctx.daily["volume"].iloc[-20:-10].mean()
    return bool(last10 < prior10), f"last10={last10:,.0f} < prior10={prior10:,.0f}"


@_rule
def _v8(ctx: VolumeContext) -> tuple[bool, str]:
    """OBV making new 20d high."""
    if len(ctx.daily) < 21:
        return False, "insufficient history"
    close = ctx.daily["close"]
    volume = ctx.daily["volume"]
    delta = close.diff()
    obv_step = pd.Series(0, index=close.index, dtype=float)
    obv_step[delta > 0] = volume[delta > 0]
    obv_step[delta < 0] = -volume[delta < 0]
    obv = obv_step.cumsum()
    return bool(obv.iloc[-1] == obv.tail(20).max()), "OBV at 20d high"


@_rule
def _v9(ctx: VolumeContext) -> tuple[bool, str]:
    """OBV linreg slope positive over 60d."""
    if len(ctx.daily) < 60:
        return False, "insufficient history"
    close = ctx.daily["close"]
    volume = ctx.daily["volume"]
    delta = close.diff()
    obv_step = pd.Series(0, index=close.index, dtype=float)
    obv_step[delta > 0] = volume[delta > 0]
    obv_step[delta < 0] = -volume[delta < 0]
    obv = obv_step.cumsum().tail(60)
    x = list(range(len(obv)))
    slope = (len(obv) * sum(x[i] * obv.iloc[i] for i in range(len(obv))) - sum(x) * obv.sum()) / \
            (len(obv) * sum(i * i for i in x) - sum(x) ** 2)
    return bool(slope > 0), f"OBV slope={slope:.2f}"


@_rule
def _v10(ctx: VolumeContext) -> tuple[bool, str]:
    """VWAP proxy — skip in EOD."""
    return True, "intraday VWAP not available in EOD data"


@_rule
def _v11(ctx: VolumeContext) -> tuple[bool, str]:
    """Delivery % ≥ 40%. TUNABLE."""
    if ctx.latest_delivery_pct is None:
        return True, "delivery % not available (skipped)"
    return bool(ctx.latest_delivery_pct >= 40), f"delivery %={ctx.latest_delivery_pct:.1f}%"


@_rule
def _v12(ctx: VolumeContext) -> tuple[bool, str]:
    """Delivery % rising 5d vs prior 15."""
    if "delivery_pct" not in ctx.daily.columns:
        return True, "delivery data not available (skipped)"
    dp = ctx.daily["delivery_pct"].dropna()
    if len(dp) < 20:
        return True, "insufficient delivery history (skipped)"
    return bool(dp.tail(5).mean() > dp.iloc[-20:-5].mean()), "delivery rising"


@_rule
def _v13(ctx: VolumeContext) -> tuple[bool, str]:
    """No unusual vol spike + price decline (churning) in last 20."""
    if len(ctx.daily) < 51:
        return False, "insufficient history"
    tail = ctx.daily.tail(20)
    prev_close = ctx.daily["close"].shift(1).tail(20)
    avg_vol = ctx.daily["volume"].tail(50).mean()
    churn = ((tail["volume"] > avg_vol * 2.0) & ((tail["close"] / prev_close - 1) < -0.01)).sum()
    return int(churn) == 0, f"{churn} churning days"


@_rule
def _v14(ctx: VolumeContext) -> tuple[bool, str]:
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    vol20 = ctx.daily["volume"].tail(20).mean()
    vol50 = ctx.daily["volume"].tail(50).mean()
    return bool(vol20 >= vol50 * 0.9), f"vol20/vol50={vol20/vol50:.2f}"


@_rule
def _v15(ctx: VolumeContext) -> tuple[bool, str]:
    """Latest vol in top 10% of last 50."""
    if len(ctx.daily) < 51:
        return False, "insufficient history"
    p90 = ctx.daily["volume"].iloc[-51:-1].quantile(0.90)
    return bool(ctx.daily["volume"].iloc[-1] >= p90), f"latest={ctx.daily['volume'].iloc[-1]:,} vs p90={p90:,.0f}"


RULES: list[tuple[str, str, str, int, Callable[[VolumeContext], tuple[bool, str]]]] = [
    ("M7.1",  "Avg daily turnover ≥ ₹5 cr",         "[O] liquidity floor",  10, _v1),
    ("M7.2",  "50d avg volume ≥ 100k shares",        "[O]",                  6, _v2),
    ("M7.3",  "Latest vol ≥ 1.5× 50d avg",           "[O] breakout confirm", 10, _v3),
    ("M7.4",  "Up-day vol > down-day vol (20d)",      "[O] accumulation",     8, _v4),
    ("M7.5",  "≥ 3 power up-days (20d)",              "[O]",                  8, _v5),
    ("M7.6",  "Distribution days ≤ 3 (20d)",         "[O]",                  8, _v6),
    ("M7.7",  "Volume drying up in base",              "[Mv] VCP",             6, _v7),
    ("M7.8",  "OBV at 20d high",                        "[Mu]",                 5, _v8),
    ("M7.9",  "OBV trending up (60d)",                  "[Mu]",                 5, _v9),
    ("M7.10", "VWAP: skipped in EOD (auto-pass)",       "[Mu]",                 4, _v10),
    ("M7.11", "Delivery % ≥ 40% (India-specific)",      "NSE-specific",        6, _v11),
    ("M7.12", "Delivery % rising (5d vs 15d)",          "NSE-specific",        5, _v12),
    ("M7.13", "No volume churning (20d)",                "[O]",                  6, _v13),
    ("M7.14", "20d avg vol ≥ 90% of 50d avg",           "[O]",                  4, _v14),
    ("M7.15", "Latest vol in top 10% of 50d",           "[O]",                  5, _v15),
]


def evaluate_volume(ctx: VolumeContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    hard_ok = True
    for rule_id, name, source, weight, fn in RULES:
        try:
            passed, actual = fn(ctx)
        except Exception as e:
            passed, actual = False, f"error: {e}"
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
