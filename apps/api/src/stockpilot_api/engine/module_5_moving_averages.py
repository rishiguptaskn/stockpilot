"""Module 5 — Moving Averages (20 rules).

Weight in aggregate: 10/100. No hard gates in this module (all soft signals).

Includes the full Minervini Trend Template (8 checks — M5.1 through M5.8),
MA alignment rules, slope rules, distance-from-MA rules, and Weinstein's
30-week weekly MA rule.

See docs/RULEBOOK.md § Module 5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from stockpilot_api.indicators import ema, sma
from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M5"
MODULE_NAME = "Moving Averages"
MODULE_WEIGHT = 10


@dataclass(frozen=True)
class MovingAveragesContext:
    """
    Daily OHLCV for a single stock plus its 252-day RS rank.

    daily: DataFrame with columns [open, high, low, close, volume], indexed by date.
           Must have at least 252 trading days of history.
    rs_rank_252: percentile (0-100) of stock's 252-day return vs universe.
    """

    daily: pd.DataFrame
    rs_rank_252: float


def _weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Resample daily to weekly (Friday close)."""
    return daily.resample("W-FRI").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    ).dropna()


# --- Rules -----------------------------------------------------------------


def _rule_m5_1(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #1: close > 150 SMA AND close > 200 SMA."""
    close = ctx.daily["close"]
    if len(close) < 200:
        return False, "insufficient history"
    latest = close.iloc[-1]
    sma150 = sma(close, 150).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    passed = latest > sma150 and latest > sma200
    return bool(passed), f"close={latest:.2f}, sma150={sma150:.2f}, sma200={sma200:.2f}"


def _rule_m5_2(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #2: 150 SMA > 200 SMA."""
    close = ctx.daily["close"]
    sma150 = sma(close, 150).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    return bool(sma150 > sma200), f"sma150={sma150:.2f}, sma200={sma200:.2f}"


def _rule_m5_3(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #3: 200 SMA sloping up for at least 1 month (~21 sessions)."""
    close = ctx.daily["close"]
    if len(close) < 221:
        return False, "insufficient history"
    sma200 = sma(close, 200)
    now = sma200.iloc[-1]
    ago = sma200.iloc[-22]
    return bool(now > ago), f"sma200 today={now:.2f} vs 21d ago={ago:.2f}"


def _rule_m5_4(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #4: 50 SMA > 150 SMA AND 50 SMA > 200 SMA."""
    close = ctx.daily["close"]
    sma50 = sma(close, 50).iloc[-1]
    sma150 = sma(close, 150).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    return bool(sma50 > sma150 and sma50 > sma200), f"sma50={sma50:.2f}, sma150={sma150:.2f}, sma200={sma200:.2f}"


def _rule_m5_5(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #5: close > 50 SMA."""
    close = ctx.daily["close"]
    latest = close.iloc[-1]
    sma50 = sma(close, 50).iloc[-1]
    return bool(latest > sma50), f"close={latest:.2f}, sma50={sma50:.2f}"


def _rule_m5_6(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #6: close >= 30% above 52-week low."""
    close = ctx.daily["close"]
    if len(close) < 252:
        return False, "insufficient history"
    latest = close.iloc[-1]
    low_52w = float(close.tail(252).min())
    ratio = latest / low_52w
    return bool(ratio >= 1.30), f"{100*(ratio-1):.1f}% above 52w-low"


def _rule_m5_7(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #7: close within 25% of 52-week high."""
    close = ctx.daily["close"]
    if len(close) < 252:
        return False, "insufficient history"
    latest = close.iloc[-1]
    high_52w = float(close.tail(252).max())
    ratio = latest / high_52w
    return bool(ratio >= 0.75), f"{100*ratio:.1f}% of 52w-high"


def _rule_m5_8(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """TT #8: RS rank >= 70."""
    return ctx.rs_rank_252 >= 70, f"RS rank={ctx.rs_rank_252:.1f}"


def _rule_m5_9(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """20 EMA > 50 SMA."""
    close = ctx.daily["close"]
    ema20 = ema(close, 20).iloc[-1]
    sma50 = sma(close, 50).iloc[-1]
    return bool(ema20 > sma50), f"20ema={ema20:.2f}, 50sma={sma50:.2f}"


def _rule_m5_10(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """50 SMA > 150 SMA."""
    close = ctx.daily["close"]
    sma50 = sma(close, 50).iloc[-1]
    sma150 = sma(close, 150).iloc[-1]
    return bool(sma50 > sma150), f"50sma={sma50:.2f}, 150sma={sma150:.2f}"


def _rule_m5_11(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Full stack: close > 20 EMA > 50 SMA > 150 SMA > 200 SMA."""
    close = ctx.daily["close"]
    latest = close.iloc[-1]
    ema20 = ema(close, 20).iloc[-1]
    sma50 = sma(close, 50).iloc[-1]
    sma150 = sma(close, 150).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    passed = latest > ema20 > sma50 > sma150 > sma200
    return bool(passed), f"stack: {latest:.2f}>{ema20:.2f}>{sma50:.2f}>{sma150:.2f}>{sma200:.2f}"


def _rule_m5_12(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """50 SMA sloping up over 20 sessions."""
    close = ctx.daily["close"]
    if len(close) < 71:
        return False, "insufficient history"
    sma50 = sma(close, 50)
    now = sma50.iloc[-1]
    ago = sma50.iloc[-21]
    return bool(now > ago), f"50sma today={now:.2f} vs 20d ago={ago:.2f}"


def _rule_m5_13(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """20 EMA sloping up over 10 sessions."""
    close = ctx.daily["close"]
    if len(close) < 31:
        return False, "insufficient history"
    ema20 = ema(close, 20)
    now = ema20.iloc[-1]
    ago = ema20.iloc[-11]
    return bool(now > ago), f"20ema today={now:.2f} vs 10d ago={ago:.2f}"


def _rule_m5_14(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Not > 25% above 50 SMA (overextension guard). TUNABLE."""
    close = ctx.daily["close"]
    latest = close.iloc[-1]
    sma50 = sma(close, 50).iloc[-1]
    extended_pct = (latest / sma50 - 1) * 100
    return bool(extended_pct <= 25.0), f"{extended_pct:+.1f}% above 50sma"


def _rule_m5_15(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Not > 50% above 200 SMA (climax guard). TUNABLE."""
    close = ctx.daily["close"]
    latest = close.iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    extended_pct = (latest / sma200 - 1) * 100
    return bool(extended_pct <= 50.0), f"{extended_pct:+.1f}% above 200sma"


def _rule_m5_16(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Recent pullback touched 20 EMA and bounced (EMA Pullback setup)."""
    close = ctx.daily["close"]
    if len(close) < 30:
        return False, "insufficient history"
    ema20 = ema(close, 20)
    tail_10_low = ctx.daily["low"].iloc[-10:]
    ema20_tail = ema20.iloc[-10:]
    touched = (tail_10_low <= ema20_tail * 1.02).any()
    above_now = close.iloc[-1] > ema20.iloc[-1]
    return bool(touched and above_now), f"touched={touched}, above_now={above_now}"


def _rule_m5_17(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Recent pullback held above 50 SMA."""
    close = ctx.daily["close"]
    if len(close) < 60:
        return False, "insufficient history"
    sma50 = sma(close, 50)
    tail_10_low = ctx.daily["low"].iloc[-10:]
    sma50_tail = sma50.iloc[-10:]
    touched = (tail_10_low <= sma50_tail * 1.02).any()
    above_now = close.iloc[-1] > sma50.iloc[-1]
    return bool(touched and above_now), f"touched={touched}, above_now={above_now}"


def _rule_m5_18(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Weinstein Stage 2 on weekly: close > 30-week SMA which is sloping up."""
    weekly = _weekly(ctx.daily)
    if len(weekly) < 31:
        return False, "insufficient weekly history"
    w_close = weekly["close"]
    w_sma30 = sma(w_close, 30)
    latest_close = w_close.iloc[-1]
    latest_sma = w_sma30.iloc[-1]
    slope_up = latest_sma > w_sma30.iloc[-2]
    passed = latest_close > latest_sma and slope_up
    return bool(passed), f"weekly close={latest_close:.2f}, sma30={latest_sma:.2f}, up={slope_up}"


def _rule_m5_19(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """Weekly 30 SMA sloping up over 5 weeks."""
    weekly = _weekly(ctx.daily)
    if len(weekly) < 36:
        return False, "insufficient weekly history"
    w_sma30 = sma(weekly["close"], 30)
    return bool(w_sma30.iloc[-1] > w_sma30.iloc[-6]), (
        f"weekly sma30 now={w_sma30.iloc[-1]:.2f} vs 5w ago={w_sma30.iloc[-6]:.2f}"
    )


def _rule_m5_20(ctx: MovingAveragesContext) -> tuple[bool, str]:
    """No death cross (50 SMA crossing below 200 SMA) in last 60 sessions."""
    close = ctx.daily["close"]
    if len(close) < 260:
        return False, "insufficient history"
    sma50 = sma(close, 50)
    sma200 = sma(close, 200)
    # Compare last 60 sessions: 50 SMA - 200 SMA. If sign flipped negative from positive, death cross.
    diff = (sma50 - sma200).tail(60)
    if diff.iloc[0] > 0:
        # Started positive — check if any subsequent value went negative
        if (diff <= 0).any():
            return False, "death cross in last 60d"
    return True, "no death cross"


RULES: list[tuple[str, str, str, int, Callable[[MovingAveragesContext], tuple[bool, str]]]] = [
    ("M5.1",  "Trend Template #1: close > 150 & 200 SMA",         "[Mv] TT #1",         8, _rule_m5_1),
    ("M5.2",  "Trend Template #2: 150 SMA > 200 SMA",              "[Mv] TT #2",         7, _rule_m5_2),
    ("M5.3",  "Trend Template #3: 200 SMA sloping up ≥ 21 sessions","[Mv] TT #3",         8, _rule_m5_3),
    ("M5.4",  "Trend Template #4: 50 > 150 & 200 SMA",              "[Mv] TT #4",         7, _rule_m5_4),
    ("M5.5",  "Trend Template #5: close > 50 SMA",                  "[Mv] TT #5",         6, _rule_m5_5),
    ("M5.6",  "Trend Template #6: close ≥ 30% above 52w-low",       "[Mv] TT #6",         6, _rule_m5_6),
    ("M5.7",  "Trend Template #7: close within 25% of 52w-high",   "[Mv] TT #7",         6, _rule_m5_7),
    ("M5.8",  "Trend Template #8: RS rank ≥ 70",                    "[Mv] TT #8 / [O] L", 8, _rule_m5_8),
    ("M5.9",  "20 EMA > 50 SMA",                                    "[Mv] short/mid",     4, _rule_m5_9),
    ("M5.10", "50 SMA > 150 SMA",                                   "[Mv] mid/long",      5, _rule_m5_10),
    ("M5.11", "Full stack: price>20e>50s>150s>200s",                "[Mv] textbook",      6, _rule_m5_11),
    ("M5.12", "50 SMA sloping up (20d)",                            "[W] rising mid-MA",  5, _rule_m5_12),
    ("M5.13", "20 EMA sloping up (10d)",                            "[Mv] short slope",   4, _rule_m5_13),
    ("M5.14", "Not > 25% above 50 SMA (extension guard)",           "[O][Mv] TUNABLE",    5, _rule_m5_14),
    ("M5.15", "Not > 50% above 200 SMA (climax guard)",             "[W] Stage 3 warn",   4, _rule_m5_15),
    ("M5.16", "EMA Pullback setup (touched 20 EMA, bounced)",       "[Mv][Mu]",           4, _rule_m5_16),
    ("M5.17", "Deeper pullback held above 50 SMA",                  "[O] proper base",    3, _rule_m5_17),
    ("M5.18", "Weinstein Stage 2 (weekly)",                         "[W]",                6, _rule_m5_18),
    ("M5.19", "Weekly 30 SMA sloping up (5w)",                      "[W] Stage 2 conf",   4, _rule_m5_19),
    ("M5.20", "No death cross in last 60 sessions",                 "[Mu]",               4, _rule_m5_20),
]


def evaluate_moving_averages(ctx: MovingAveragesContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0

    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
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
                is_hard_gate=False,
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
        hard_gates_passed=True,  # no hard gates
    )
