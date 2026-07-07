"""Technical MCP tools — read-only views over the deterministic rule engine.

Each function is a *tool* an agent may call. They wrap the existing engine
(indicators, Modules 4-7, pattern detectors) and return JSON-serialisable dicts.
They never mutate anything and never call an LLM.

Honesty contract: where a rule needs a cross-module input the technical slice
cannot compute in isolation (market/sector/fundamental/risk scores, universe RS
rank), we pass a clearly-labelled neutral placeholder and surface it in a
``notes`` field so the agent can discount it rather than treat it as real.
"""

from __future__ import annotations

import math
from typing import Any

from stockpilot_api.engine.module_4_technical import (
    TechnicalContext,
    evaluate_technical_analysis,
)
from stockpilot_api.engine.module_5_moving_averages import (
    MovingAveragesContext,
    evaluate_moving_averages,
)
from stockpilot_api.engine.module_6_momentum import MomentumContext, evaluate_momentum
from stockpilot_api.engine.module_7_volume import VolumeContext, evaluate_volume
from stockpilot_api.indicators import atr, ema, rsi, sma
from stockpilot_api.mcp.data_access import has_sufficient_history, load_daily, to_weekly
from stockpilot_api.patterns import detect_all_patterns

_NEUTRAL_RS_RANK = 50.0  # placeholder: real rank needs a scored universe
_UNAVAILABLE = {"data_available": False}


def _unavailable(ticker: str, reason: str) -> dict[str, Any]:
    return {"data_available": False, "ticker": ticker, "reason": reason}


def _round(x: float, n: int = 2) -> float | None:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


def get_indicators(ticker: str) -> dict[str, Any]:
    """Latest values of the core indicators the engine computes for a ticker."""
    daily = load_daily(ticker)
    if not has_sufficient_history(daily):
        return _unavailable(ticker, "fewer than 200 trading days of history")

    c = daily["close"]
    h, low = daily["high"], daily["low"]
    return {
        "data_available": True,
        "ticker": ticker,
        "as_of": daily.index[-1].date().isoformat(),
        "close": _round(c.iloc[-1]),
        "ema_20": _round(ema(c, 20).iloc[-1]),
        "sma_50": _round(sma(c, 50).iloc[-1]),
        "sma_150": _round(sma(c, 150).iloc[-1]) if len(c) >= 150 else None,
        "sma_200": _round(sma(c, 200).iloc[-1]) if len(c) >= 200 else None,
        "rsi_14": _round(rsi(c, 14).iloc[-1]),
        "atr_14": _round(atr(h, low, c, 14).iloc[-1]),
        "atr_pct": _round(atr(h, low, c, 14).iloc[-1] / c.iloc[-1] * 100),
        "notes": "RSI is context only (not an entry trigger) per the rulebook.",
    }


def get_price_action(ticker: str, lookback: int = 20) -> dict[str, Any]:
    """Recent price action: change, distance to 52w extremes, position vs key MAs."""
    daily = load_daily(ticker)
    if not has_sufficient_history(daily):
        return _unavailable(ticker, "fewer than 200 trading days of history")

    c = daily["close"]
    last = float(c.iloc[-1])
    window = c.tail(252)
    high_52w, low_52w = float(window.max()), float(window.min())
    ref = c.iloc[-lookback - 1] if len(c) > lookback else c.iloc[0]
    return {
        "data_available": True,
        "ticker": ticker,
        "as_of": daily.index[-1].date().isoformat(),
        "close": _round(last),
        "change_pct_lookback": _round((last / ref - 1) * 100),
        "lookback_days": lookback,
        "high_52w": _round(high_52w),
        "low_52w": _round(low_52w),
        "dist_to_52w_high_pct": _round((last / high_52w - 1) * 100),
        "off_52w_low_pct": _round((last / low_52w - 1) * 100),
        "above_ema_20": bool(last > ema(c, 20).iloc[-1]),
        "above_sma_50": bool(last > sma(c, 50).iloc[-1]),
        "above_sma_200": bool(last > sma(c, 200).iloc[-1]) if len(c) >= 200 else None,
    }


def detect_patterns(ticker: str) -> dict[str, Any]:
    """Run all 8 pattern detectors; return those that fired with quality + metadata."""
    daily = load_daily(ticker)
    if not has_sufficient_history(daily):
        return _unavailable(ticker, "fewer than 200 trading days of history")

    patterns = detect_all_patterns(daily)
    return {
        "data_available": True,
        "ticker": ticker,
        "as_of": daily.index[-1].date().isoformat(),
        "detected_count": len(patterns),
        "patterns": patterns,
    }


def _default_trade_plan(last: float) -> tuple[float, float, float]:
    """A conservative reference plan so M4/M9-style rules have inputs.

    entry = last close; stop = 7% below (within O'Neil 7-8% / Elder 8% caps);
    target = 3R above (1:3 reward:risk). Suggestive only.
    """
    entry = round(last, 2)
    stop = round(entry * 0.93, 2)
    target = round(entry + (entry - stop) * 3.0, 2)
    return entry, stop, target


def get_module_score(ticker: str, module: str) -> dict[str, Any]:
    """Run one technical module (M4|M5|M6|M7) and return its ModuleScore.

    M4 depends on market/sector/fundamental/risk scores that the technical slice
    cannot compute; those are passed as neutral placeholders and flagged in
    ``notes``. M5-M7 are pure price/volume and fully real.
    """
    module = module.upper().strip()
    allowed = {"M4", "M5", "M6", "M7"}
    if module not in allowed:
        return {
            "data_available": False,
            "ticker": ticker,
            "reason": f"module must be one of {sorted(allowed)}; got {module!r}",
        }

    daily = load_daily(ticker)
    if not has_sufficient_history(daily):
        return _unavailable(ticker, "fewer than 200 trading days of history")

    notes: list[str] = []
    if module == "M5":
        score = evaluate_moving_averages(
            MovingAveragesContext(daily=daily, rs_rank_252=_NEUTRAL_RS_RANK)
        )
        notes.append("rs_rank_252 is a neutral placeholder (50); real rank needs a scored universe.")
    elif module == "M6":
        score = evaluate_momentum(MomentumContext(daily=daily))
    elif module == "M7":
        score = evaluate_volume(VolumeContext(daily=daily))
    else:  # M4
        last = float(daily["close"].iloc[-1])
        entry, stop, target = _default_trade_plan(last)
        pattern_names = [p["pattern_name"] for p in detect_all_patterns(daily)]
        score = evaluate_technical_analysis(
            TechnicalContext(
                daily=daily,
                weekly=to_weekly(daily),
                rs_rank_252=_NEUTRAL_RS_RANK,
                module_1_score=70.0,
                module_2_score=70.0,
                module_3_score=70.0,
                module_9_score=95.0,
                entry=entry,
                stop=stop,
                target=target,
                detected_patterns=pattern_names,
            )
        )
        notes.append(
            "M4 cross-inputs (market/sector/fundamental/risk scores, RS rank, trade plan) "
            "are neutral placeholders — weight this module's absolute score with caution; "
            "the individual rule_evaluations are still meaningful."
        )

    result = score.model_dump()
    result.update({"data_available": True, "ticker": ticker, "notes": notes})
    return result


# Registry-facing metadata: (name, description, input_schema, fn) ------------
_TICKER_PROP = {
    "ticker": {
        "type": "string",
        "description": "NSE ticker with suffix, e.g. 'RELIANCE.NS'.",
    }
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "get_indicators",
        "description": (
            "Latest core technical indicators (EMA20, SMA50/150/200, RSI14, ATR14) for a ticker. "
            "Use to assess trend structure and volatility."
        ),
        "input_schema": {"type": "object", "properties": _TICKER_PROP, "required": ["ticker"]},
        "fn": get_indicators,
    },
    {
        "name": "get_price_action",
        "description": (
            "Recent price action: % change over a lookback, distance to 52-week high/low, "
            "and whether price is above key moving averages."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_TICKER_PROP,
                "lookback": {
                    "type": "integer",
                    "description": "Trading days to measure change over (default 20).",
                    "default": 20,
                },
            },
            "required": ["ticker"],
        },
        "fn": get_price_action,
    },
    {
        "name": "detect_patterns",
        "description": (
            "Run all 8 chart-pattern detectors (VCP, Cup & Handle, Flat Base, Bull Flag, "
            "Darvas Box, Ascending Triangle, Stage 2 Breakout, EMA Pullback) and return those "
            "that fired with a quality score and metadata."
        ),
        "input_schema": {"type": "object", "properties": _TICKER_PROP, "required": ["ticker"]},
        "fn": detect_patterns,
    },
    {
        "name": "get_module_score",
        "description": (
            "Run one deterministic rule module and return its 0-100 score plus every rule "
            "evaluation with citations. Modules: M4 Technical Analysis, M5 Moving Averages, "
            "M6 Momentum, M7 Volume. Prefer M5/M6/M7 (fully real); M4 uses neutral placeholders "
            "for non-technical cross-inputs (see the returned notes)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_TICKER_PROP,
                "module": {
                    "type": "string",
                    "enum": ["M4", "M5", "M6", "M7"],
                    "description": "Which module to evaluate.",
                },
            },
            "required": ["ticker", "module"],
        },
        "fn": get_module_score,
    },
]
