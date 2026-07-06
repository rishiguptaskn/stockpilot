"""Module 6 — Momentum Indicators (20 rules).

Weight in aggregate: 5/100. RSI is CONTEXT ONLY, never a standalone entry signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from stockpilot_api.indicators import atr, rsi
from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M6"
MODULE_NAME = "Momentum Indicators"
MODULE_WEIGHT = 5


@dataclass(frozen=True)
class MomentumContext:
    daily: pd.DataFrame


def _macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return macd_line, signal, hist


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14):
    """Simplified ADX with +DI/-DI."""
    up = high.diff()
    dn = -low.diff()
    plus_dm = up.where((up > dn) & (up > 0), 0.0)
    minus_dm = dn.where((dn > up) & (dn > 0), 0.0)
    atr_val = atr(high, low, close, window)
    plus_di = 100 * plus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_val
    minus_di = 100 * minus_dm.ewm(alpha=1 / window, adjust=False).mean() / atr_val
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    adx_val = dx.ewm(alpha=1 / window, adjust=False).mean()
    return adx_val, plus_di, minus_di


def _rule(fn):
    return fn


def _c(ctx: MomentumContext) -> pd.Series:
    return ctx.daily["close"]


@_rule
def _r1(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 15:
        return False, "insufficient history"
    r = rsi(_c(ctx), 14).iloc[-1]
    return 50 <= r <= 70, f"RSI={r:.1f}"


@_rule
def _r2(ctx: MomentumContext) -> tuple[bool, str]:
    r = rsi(_c(ctx), 14).iloc[-1]
    return r < 80, f"RSI={r:.1f}"


@_rule
def _r3(ctx: MomentumContext) -> tuple[bool, str]:
    r = rsi(_c(ctx), 14).iloc[-1]
    return r >= 30, f"RSI={r:.1f}"


@_rule
def _r4(ctx: MomentumContext) -> tuple[bool, str]:
    """No bearish RSI divergence in last 20 sessions."""
    if len(ctx.daily) < 40:
        return False, "insufficient history"
    close = _c(ctx).tail(20)
    r = rsi(_c(ctx), 14).tail(20)
    price_high_idx = close.idxmax()
    rsi_high_idx = r.idxmax()
    # If price high is more recent than RSI high, bearish divergence
    return price_high_idx <= rsi_high_idx, "no divergence"


@_rule
def _r5(ctx: MomentumContext) -> tuple[bool, str]:
    """Bullish divergence (bonus)."""
    if len(ctx.daily) < 40:
        return False, "insufficient history"
    close = _c(ctx).tail(20)
    r = rsi(_c(ctx), 14).tail(20)
    price_low_idx = close.idxmin()
    rsi_low_idx = r.idxmin()
    return price_low_idx <= rsi_low_idx, "possible bullish divergence"


@_rule
def _r6(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    line, sig, _ = _macd(_c(ctx))
    return bool(line.iloc[-1] > sig.iloc[-1]), "MACD > signal"


@_rule
def _r7(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    _, _, hist = _macd(_c(ctx))
    return bool(hist.iloc[-1] > 0), f"hist={hist.iloc[-1]:.2f}"


@_rule
def _r8(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 35:
        return False, "insufficient history"
    _, _, hist = _macd(_c(ctx))
    return bool(hist.iloc[-1] > hist.iloc[-6]), "hist rising 5d"


@_rule
def _r9(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    line, _, _ = _macd(_c(ctx))
    return bool(line.iloc[-1] > 0), f"MACD line={line.iloc[-1]:.2f}"


@_rule
def _r10(ctx: MomentumContext) -> tuple[bool, str]:
    """No MACD bearish crossover in last 10 sessions."""
    if len(ctx.daily) < 40:
        return False, "insufficient history"
    line, sig, _ = _macd(_c(ctx))
    diff = (line - sig).tail(11)
    bearish_cross = ((diff.iloc[:-1] > 0) & (diff.iloc[1:].values <= 0)).any()
    return not bool(bearish_cross), "no bearish MACD cross"


@_rule
def _r11(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    a, _, _ = _adx(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14)
    return bool(a.iloc[-1] >= 20), f"ADX={a.iloc[-1]:.1f}"


@_rule
def _r12(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    a, _, _ = _adx(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14)
    return bool(a.iloc[-1] > a.iloc[-11]), "ADX rising 10d"


@_rule
def _r13(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    _, plus, minus = _adx(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14)
    return bool(plus.iloc[-1] > minus.iloc[-1]), "+DI > -DI"


@_rule
def _r14(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 30:
        return False, "insufficient history"
    a, _, _ = _adx(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14)
    return bool(a.iloc[-1] < 50), f"ADX={a.iloc[-1]:.1f}"


@_rule
def _r15(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 15:
        return False, "insufficient history"
    a = atr(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14).iloc[-1]
    ratio = a / ctx.daily["close"].iloc[-1]
    return bool(ratio < 0.05), f"ATR/close={ratio*100:.2f}%"


@_rule
def _r16(ctx: MomentumContext) -> tuple[bool, str]:
    """ATR contracting (last vs 20d ago)."""
    if len(ctx.daily) < 35:
        return False, "insufficient history"
    a = atr(ctx.daily["high"], ctx.daily["low"], ctx.daily["close"], 14)
    return bool(a.iloc[-1] < a.iloc[-21]), "ATR contracting"


@_rule
def _r17(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 63:
        return False, "insufficient history"
    ret = ctx.daily["close"].iloc[-1] / ctx.daily["close"].iloc[-63] - 1
    return bool(ret > 0), f"63d ROC={ret*100:.1f}%"


@_rule
def _r18(ctx: MomentumContext) -> tuple[bool, str]:
    if len(ctx.daily) < 21:
        return False, "insufficient history"
    ret = ctx.daily["close"].iloc[-1] / ctx.daily["close"].iloc[-21] - 1
    return bool(ret > 0), f"21d ROC={ret*100:.1f}%"


@_rule
def _r19(ctx: MomentumContext) -> tuple[bool, str]:
    """Stock 26w ROC > 0 (proxy for outperforming sector when sector data absent)."""
    if len(ctx.daily) < 126:
        return False, "insufficient history"
    ret = ctx.daily["close"].iloc[-1] / ctx.daily["close"].iloc[-126] - 1
    return bool(ret > 0), f"26w ROC={ret*100:.1f}%"


@_rule
def _r20(ctx: MomentumContext) -> tuple[bool, str]:
    """Simple stochastic %K > %D (14, 3)."""
    if len(ctx.daily) < 17:
        return False, "insufficient history"
    high = ctx.daily["high"]
    low = ctx.daily["low"]
    close = ctx.daily["close"]
    k = 100 * (close - low.rolling(14).min()) / (high.rolling(14).max() - low.rolling(14).min())
    d = k.rolling(3).mean()
    if pd.isna(k.iloc[-1]) or pd.isna(d.iloc[-1]):
        return False, "stochastic NaN"
    return bool(k.iloc[-1] > d.iloc[-1]), f"%K={k.iloc[-1]:.1f} > %D={d.iloc[-1]:.1f}"


RULES: list[tuple[str, str, str, int, Callable[[MomentumContext], tuple[bool, str]]]] = [
    ("M6.1",  "RSI 50-70 (healthy uptrend zone)",        "[Mu]",       8, _r1),
    ("M6.2",  "RSI < 80 (not overbought)",                "[Mu]",       6, _r2),
    ("M6.3",  "RSI >= 30 (not oversold going in)",        "[Mu]",       4, _r3),
    ("M6.4",  "No bearish RSI divergence (20d)",          "[Mu]",       6, _r4),
    ("M6.5",  "Bullish RSI divergence (bonus)",           "[Mu]",       4, _r5),
    ("M6.6",  "MACD > signal",                             "[Mu]",       6, _r6),
    ("M6.7",  "MACD histogram > 0",                       "[Mu]",       5, _r7),
    ("M6.8",  "MACD histogram rising (5d)",                "[Mu]",       5, _r8),
    ("M6.9",  "MACD line > 0",                             "[Mu]",       5, _r9),
    ("M6.10", "No MACD bearish cross (10d)",               "[Mu]",       4, _r10),
    ("M6.11", "ADX ≥ 20 (trending)",                       "[Mu]",       6, _r11),
    ("M6.12", "ADX rising (10d)",                          "[Mu]",       4, _r12),
    ("M6.13", "+DI > -DI",                                 "[Mu]",       5, _r13),
    ("M6.14", "ADX < 50 (not exhausted)",                   "[Mu]",       3, _r14),
    ("M6.15", "ATR/close < 5%",                             "[Mu]",       4, _r15),
    ("M6.16", "ATR contracting (20d)",                     "[Mv] VCP",   4, _r16),
    ("M6.17", "12-week ROC positive",                      "[Mu]",       4, _r17),
    ("M6.18", "4-week ROC positive",                       "[Mu]",       3, _r18),
    ("M6.19", "26-week ROC positive",                      "[O] RS",     4, _r19),
    ("M6.20", "Stochastic %K > %D",                        "[Mu]",       2, _r20),
]


def evaluate_momentum(ctx: MomentumContext) -> ModuleScore:
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
