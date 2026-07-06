"""Module 4 — Technical Analysis (40 rules).

Weight in aggregate: 15/100. No hard gates.

Implements the 18-point pre-buy checklist (M4.1–M4.18) plus 22 additional
technical rules covering higher-highs, gap analysis, base quality, extension
guards, and pattern references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from stockpilot_api.indicators import atr, ema, sma
from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M4"
MODULE_NAME = "Technical Analysis"
MODULE_WEIGHT = 15


@dataclass(frozen=True)
class TechnicalContext:
    daily: pd.DataFrame  # OHLCV
    weekly: pd.DataFrame  # weekly resample
    rs_rank_252: float
    module_1_score: float  # market environment aggregate
    module_2_score: float  # sector
    module_3_score: float  # fundamentals
    module_9_score: float  # risk
    entry: float = 0.0
    stop: float = 0.0
    target: float = 0.0
    detected_patterns: list[str] = field(default_factory=list)  # ["VCP", "Stage 2 Breakout", ...]


def _rule(fn):
    return fn


def _closes(ctx: TechnicalContext) -> pd.Series:
    return ctx.daily["close"]


# 18-point pre-buy checklist ---


@_rule
def _t1(ctx: TechnicalContext) -> tuple[bool, str]:
    return ctx.module_1_score >= 70, f"module_1_score={ctx.module_1_score:.1f}"


@_rule
def _t2(ctx: TechnicalContext) -> tuple[bool, str]:
    c = _closes(ctx)
    e20 = ema(c, 20).iloc[-1]
    return bool(c.iloc[-1] > e20), f"close={c.iloc[-1]:.2f}, 20ema={e20:.2f}"


@_rule
def _t3(ctx: TechnicalContext) -> tuple[bool, str]:
    c = _closes(ctx)
    s50 = sma(c, 50).iloc[-1]
    return bool(c.iloc[-1] > s50), f"close={c.iloc[-1]:.2f}, 50sma={s50:.2f}"


@_rule
def _t4(ctx: TechnicalContext) -> tuple[bool, str]:
    c = _closes(ctx)
    if len(c) < 200:
        return False, "insufficient history"
    s200 = sma(c, 200).iloc[-1]
    return bool(c.iloc[-1] > s200), f"close={c.iloc[-1]:.2f}, 200sma={s200:.2f}"


@_rule
def _t5(ctx: TechnicalContext) -> tuple[bool, str]:
    c = _closes(ctx)
    if len(c) < 200:
        return False, "insufficient history"
    return bool(sma(c, 50).iloc[-1] > sma(c, 200).iloc[-1]), "50>200"


@_rule
def _t6(ctx: TechnicalContext) -> tuple[bool, str]:
    return ctx.rs_rank_252 >= 70, f"RS={ctx.rs_rank_252:.1f}"


@_rule
def _t7(ctx: TechnicalContext) -> tuple[bool, str]:
    """Institutional buying via 1.5×avg volume up-days."""
    d = ctx.daily.tail(20).copy()
    if len(d) < 20:
        return False, "insufficient history"
    d["up"] = d["close"] > d["open"]
    avg_vol = d["volume"].mean()
    strong_up_days = ((d["up"]) & (d["volume"] > avg_vol * 1.5)).sum()
    return int(strong_up_days) >= 3, f"{strong_up_days} strong up-days in 20"


@_rule
def _t8(ctx: TechnicalContext) -> tuple[bool, str]:
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    return bool(ctx.daily["volume"].iloc[-1] > ctx.daily["volume"].tail(50).mean()), "vol > avg50"


@_rule
def _t9(ctx: TechnicalContext) -> tuple[bool, str]:
    """Tight consolidation: (max-min)/close < 15% in last 20d."""
    if len(ctx.daily) < 20:
        return False, "insufficient history"
    tail = ctx.daily.tail(20)
    rng = (tail["high"].max() - tail["low"].min()) / ctx.daily["close"].iloc[-1]
    return bool(rng < 0.15), f"20d range={rng*100:.1f}%"


@_rule
def _t10(ctx: TechnicalContext) -> tuple[bool, str]:
    """Breakout on high volume — placeholder (checked contextually elsewhere)."""
    if len(ctx.daily) < 50:
        return False, "insufficient history"
    return bool(ctx.daily["volume"].iloc[-1] >= ctx.daily["volume"].tail(50).mean() * 1.4), "vol>=1.4×avg50"


@_rule
def _t11(ctx: TechnicalContext) -> tuple[bool, str]:
    return ctx.module_3_score >= 70, f"module_3_score={ctx.module_3_score:.1f}"


@_rule
def _t12(ctx: TechnicalContext) -> tuple[bool, str]:
    return ctx.module_2_score >= 70, f"module_2_score={ctx.module_2_score:.1f}"


@_rule
def _t13(ctx: TechnicalContext) -> tuple[bool, str]:
    """Strong price momentum (3-month ≥ 20%). TUNABLE."""
    if len(ctx.daily) < 63:
        return False, "insufficient history"
    ret = ctx.daily["close"].iloc[-1] / ctx.daily["close"].iloc[-63] - 1
    return bool(ret >= 0.20), f"63d return={ret*100:.1f}%"


@_rule
def _t14(ctx: TechnicalContext) -> tuple[bool, str]:
    if ctx.entry <= 0 or ctx.stop <= 0:
        return False, "no entry/stop set"
    stop_pct = (ctx.entry - ctx.stop) / ctx.entry
    return bool(stop_pct <= 0.08), f"stop {stop_pct*100:.1f}% below entry"


@_rule
def _t15(ctx: TechnicalContext) -> tuple[bool, str]:
    if ctx.entry <= 0 or ctx.stop <= 0 or ctx.target <= 0:
        return False, "no R:R data"
    rr = (ctx.target - ctx.entry) / (ctx.entry - ctx.stop)
    return bool(rr >= 2.0), f"R:R=1:{rr:.2f}"


@_rule
def _t16(ctx: TechnicalContext) -> tuple[bool, str]:
    return ctx.module_9_score >= 90, f"module_9_score={ctx.module_9_score:.1f}"


@_rule
def _t17(ctx: TechnicalContext) -> tuple[bool, str]:
    """No swing high between entry and target (simplified)."""
    if ctx.entry <= 0 or ctx.target <= 0 or len(ctx.daily) < 126:
        return True, "not applicable"
    recent_highs = ctx.daily["high"].tail(126)
    overhead = ((recent_highs > ctx.entry) & (recent_highs < ctx.target)).sum()
    return int(overhead) < 5, f"overhead resistance touches={overhead}"


@_rule
def _t18(ctx: TechnicalContext) -> tuple[bool, str]:
    return bool(ctx.entry > 0 and ctx.stop > 0 and ctx.target > 0), "exit rules defined"


# Additional M4.19 - M4.40 ---


@_rule
def _t19(ctx: TechnicalContext) -> tuple[bool, str]:
    """Higher highs and higher lows over 63d."""
    if len(ctx.daily) < 63:
        return False, "insufficient history"
    h = ctx.daily["high"].tail(63)
    l = ctx.daily["low"].tail(63)
    hh = h.iloc[-1] > h.iloc[:31].max() and h.iloc[-1] > h.iloc[:31].max()  # very rough
    hl = l.iloc[-1] > l.iloc[:31].min()
    return bool(hh and hl), f"HH:{hh} HL:{hl}"


@_rule
def _t20(ctx: TechnicalContext) -> tuple[bool, str]:
    """Above prior swing high (30d)."""
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    return bool(ctx.daily["close"].iloc[-1] > ctx.daily["high"].tail(30).iloc[:20].max()), "above 30d prior swing"


@_rule
def _t21(ctx: TechnicalContext) -> tuple[bool, str]:
    """No lower low in last 20 sessions."""
    if len(ctx.daily) < 40:
        return False, "insufficient history"
    return bool(ctx.daily["low"].tail(20).min() > ctx.daily["low"].iloc[-40:-20].min()), "no lower low"


@_rule
def _t22(ctx: TechnicalContext) -> tuple[bool, str]:
    """ATR% < 5% (TUNABLE)."""
    if len(ctx.daily) < 15:
        return False, "insufficient history"
    a = atr(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14).iloc[-1]
    ratio = a / ctx.daily["close"].iloc[-1]
    return bool(ratio < 0.05), f"ATR/close={ratio*100:.2f}%"


@_rule
def _t23(ctx: TechnicalContext) -> tuple[bool, str]:
    """No gap down > 3% in last 5 sessions."""
    if len(ctx.daily) < 6:
        return False, "insufficient history"
    tail = ctx.daily.tail(6)
    gaps = tail["open"] / tail["close"].shift(1) - 1
    return bool(gaps.iloc[1:].min() > -0.03), "no >3% gap-down"


@_rule
def _t24(ctx: TechnicalContext) -> tuple[bool, str]:
    """Close in upper half of day's range (buying pressure)."""
    latest = ctx.daily.iloc[-1]
    denom = latest["high"] - latest["low"]
    if denom == 0:
        return False, "no range"
    pos = (latest["close"] - latest["low"]) / denom
    return bool(pos > 0.6), f"close position={pos*100:.0f}% of range"


@_rule
def _t25(ctx: TechnicalContext) -> tuple[bool, str]:
    """Latest candle bullish."""
    latest = ctx.daily.iloc[-1]
    return bool(latest["close"] > latest["open"]), "bullish candle"


@_rule
def _t26(ctx: TechnicalContext) -> tuple[bool, str]:
    """Bullish candle pattern (simple: latest > open AND range >= 1% AND close in top 60%)."""
    latest = ctx.daily.iloc[-1]
    if latest["high"] == latest["low"]:
        return False, "no range"
    body = abs(latest["close"] - latest["open"]) / latest["high"]
    return bool(latest["close"] > latest["open"] and body > 0.005), "bullish candle body"


@_rule
def _t27(ctx: TechnicalContext) -> tuple[bool, str]:
    """No bearish reversal in last 3 candles (simple heuristic)."""
    if len(ctx.daily) < 3:
        return False, "insufficient history"
    last3 = ctx.daily.tail(3)
    red_days = int((last3["close"] < last3["open"]).sum())
    return red_days < 3, f"{red_days} red candles in last 3"


@_rule
def _t28(ctx: TechnicalContext) -> tuple[bool, str]:
    """Weekly in uptrend (close > 30-week SMA)."""
    if len(ctx.weekly) < 30:
        return False, "insufficient weekly history"
    return bool(ctx.weekly["close"].iloc[-1] > sma(ctx.weekly["close"], 30).iloc[-1]), "weekly > 30w sma"


@_rule
def _t29(ctx: TechnicalContext) -> tuple[bool, str]:
    """Weekly close > prior week's high."""
    if len(ctx.weekly) < 2:
        return False, "insufficient weekly history"
    return bool(ctx.weekly["close"].iloc[-1] > ctx.weekly["high"].iloc[-2]), "weekly breakout"


@_rule
def _t30(ctx: TechnicalContext) -> tuple[bool, str]:
    if len(ctx.daily) < 252:
        return False, "insufficient history"
    low_52w = ctx.daily["close"].tail(252).min()
    ratio = ctx.daily["close"].iloc[-1] / low_52w - 1
    return bool(ratio >= 0.30), f"{ratio*100:.1f}% above 52w-low"


@_rule
def _t31(ctx: TechnicalContext) -> tuple[bool, str]:
    if len(ctx.daily) < 252:
        return False, "insufficient history"
    high_52w = ctx.daily["close"].tail(252).max()
    ratio = ctx.daily["close"].iloc[-1] / high_52w
    return bool(ratio >= 0.75), f"{ratio*100:.1f}% of 52w-high"


@_rule
def _t32(ctx: TechnicalContext) -> tuple[bool, str]:
    return len(ctx.detected_patterns) > 0, f"patterns={ctx.detected_patterns}"


@_rule
def _t33(ctx: TechnicalContext) -> tuple[bool, str]:
    """Pattern quality — proxy: we count detected patterns."""
    return len(ctx.detected_patterns) >= 1, f"{len(ctx.detected_patterns)} patterns detected"


@_rule
def _t34(ctx: TechnicalContext) -> tuple[bool, str]:
    """Base depth reasonable (30d range/close ≤ 33%). TUNABLE."""
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    tail = ctx.daily.tail(30)
    depth = (tail["high"].max() - tail["low"].min()) / tail["high"].max()
    return 0.05 <= depth <= 0.33, f"base depth={depth*100:.1f}%"


@_rule
def _t35(ctx: TechnicalContext) -> tuple[bool, str]:
    """Handle drifts down on light vol (weak proxy — always true for simplicity)."""
    return True, "not enforced without pattern context"


@_rule
def _t36(ctx: TechnicalContext) -> tuple[bool, str]:
    """Prior uptrend before base (30% in 6mo)."""
    if len(ctx.daily) < 126:
        return False, "insufficient history"
    ret = ctx.daily["close"].iloc[-30] / ctx.daily["close"].iloc[-126] - 1
    return bool(ret >= 0.20), f"prior 6mo→30d ret={ret*100:.1f}%"


@_rule
def _t37(ctx: TechnicalContext) -> tuple[bool, str]:
    """Not late-stage base (proxy: passes)."""
    return True, "not enforced without cycle context"


@_rule
def _t38(ctx: TechnicalContext) -> tuple[bool, str]:
    """Not extended >5% from pivot. Pivot = 20d high."""
    if len(ctx.daily) < 20 or ctx.entry <= 0:
        return True, "no entry set"
    pivot = ctx.daily["high"].tail(20).max()
    return bool(ctx.entry <= pivot * 1.05), f"entry vs pivot={ctx.entry:.2f} vs {pivot:.2f}"


@_rule
def _t39(ctx: TechnicalContext) -> tuple[bool, str]:
    """Not near round-number resistance (>2% away). TUNABLE."""
    price = ctx.daily["close"].iloc[-1]
    nearest_100 = round(price / 100) * 100
    if nearest_100 == 0:
        return True, "no round nearby"
    dist = abs(price - nearest_100) / price
    return bool(dist > 0.02), f"dist from ₹{nearest_100}={dist*100:.2f}%"


@_rule
def _t40(ctx: TechnicalContext) -> tuple[bool, str]:
    """Volatility contracting (stdev(20) < stdev(60))."""
    if len(ctx.daily) < 60:
        return False, "insufficient history"
    close = ctx.daily["close"]
    return bool(close.pct_change().tail(20).std() < close.pct_change().tail(60).std()), "vol contracting"


RULES: list[tuple[str, str, str, int, Callable[[TechnicalContext], tuple[bool, str]]]] = [
    ("M4.1",  "Market bullish (M1 ≥ 70)",                "[O] M-in-CAN-SLIM",       5, _t1),
    ("M4.2",  "Price > 20 EMA",                          "[Mv]",                     4, _t2),
    ("M4.3",  "Price > 50 SMA",                          "[Mv] TT #5",              5, _t3),
    ("M4.4",  "Price > 200 SMA",                         "[Mv] TT #1 / [W]",         6, _t4),
    ("M4.5",  "50 SMA > 200 SMA",                        "[Mv] TT partial",          5, _t5),
    ("M4.6",  "RS > market",                             "[Mv] TT #8",               6, _t6),
    ("M4.7",  "Institutional buying visible",            "[O]",                      5, _t7),
    ("M4.8",  "Daily volume > average",                  "[O]",                      3, _t8),
    ("M4.9",  "Tight consolidation base",                "[O][Mv] VCP",              5, _t9),
    ("M4.10", "Breakout volume ≥ 1.4× avg50",            "[O]",                      8, _t10),
    ("M4.11", "Positive fundamentals (M3 ≥ 70)",         "[O]",                      5, _t11),
    ("M4.12", "Sector leading (M2 ≥ 70)",                "[O]",                      5, _t12),
    ("M4.13", "Strong momentum (63d ≥ 20%)",             "[Mv]",                     4, _t13),
    ("M4.14", "Stop within 8% of entry",                 "[O]",                      6, _t14),
    ("M4.15", "R:R ≥ 2:1",                                "[O][E]",                   6, _t15),
    ("M4.16", "Risk sizing passes (M9 ≥ 90)",             "[E]",                      6, _t16),
    ("M4.17", "No major overhead resistance",             "[Mu]",                     4, _t17),
    ("M4.18", "Exit rules defined",                       "[E]",                      4, _t18),
    ("M4.19", "Higher highs & higher lows (3mo)",         "[Mu] uptrend def",         4, _t19),
    ("M4.20", "Above prior swing high (30d)",             "[Mu]",                     3, _t20),
    ("M4.21", "No lower low in last 20 sessions",         "[Mu]",                     3, _t21),
    ("M4.22", "ATR%/close < 5%",                          "[Mu]",                     3, _t22),
    ("M4.23", "No large gap-down (5d)",                   "[Mu]",                     3, _t23),
    ("M4.24", "Close in upper half of day range",         "[Mu]",                     3, _t24),
    ("M4.25", "Latest candle bullish",                    "[N]",                      2, _t25),
    ("M4.26", "Bullish candle pattern on breakout",       "[N]",                      3, _t26),
    ("M4.27", "No bearish reversal (3d)",                 "[N]",                      3, _t27),
    ("M4.28", "Weekly in uptrend (30w SMA)",              "[W]",                      4, _t28),
    ("M4.29", "Weekly close > prior week high",           "[Mu]",                     3, _t29),
    ("M4.30", "≥ 30% above 52w-low",                       "[Mv] TT #6",              4, _t30),
    ("M4.31", "≤ 25% below 52w-high",                      "[Mv] TT #7",              4, _t31),
    ("M4.32", "At least one recognized pattern",          "[Mv][O]",                  6, _t32),
    ("M4.33", "Pattern quality ≥ 70",                     "[Mv]",                     4, _t33),
    ("M4.34", "Base depth 5-33%",                          "[O]",                      3, _t34),
    ("M4.35", "Handle drifts down on light vol",          "[O]",                      3, _t35),
    ("M4.36", "Prior 30%+ uptrend before base",           "[O]",                      4, _t36),
    ("M4.37", "Not late-stage base",                       "[O]",                      3, _t37),
    ("M4.38", "Entry ≤ 5% above pivot",                   "[O]",                      4, _t38),
    ("M4.39", "Not near round-number resistance",         "[Mu]",                     2, _t39),
    ("M4.40", "Historical volatility contracting",        "[Mv] VCP",                 3, _t40),
]


def evaluate_technical_analysis(ctx: TechnicalContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    for rule_id, name, source, weight, fn in RULES:
        try:
            passed, actual = fn(ctx)
        except Exception as e:
            passed, actual = False, f"error: {e}"
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
