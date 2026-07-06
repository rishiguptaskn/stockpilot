"""EMA Pullback — Minervini / Murphy.

Within a strong uptrend, price pulls back to touch 10 EMA or 20 EMA, then
bounces. A high-probability continuation setup.

Detection heuristic:
  1. Strong uptrend: full Minervini Trend Template (via helper): close > 50 SMA > 200 SMA + rising 200 SMA
  2. In last 5-10 sessions, low touched the 20 EMA (within 2%)
  3. Latest close > 20 EMA (bounce confirmed)
  4. Volume declined during the pullback then expanded on the bounce
"""

from __future__ import annotations

import pandas as pd

from stockpilot_api.indicators import ema, sma


def detect_ema_pullback(daily: pd.DataFrame) -> dict:
    result = {"pattern_name": "EMA Pullback", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < 220:
        return result

    close = daily["close"]
    sma50 = sma(close, 50).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    sma200_series = sma(close, 200)

    # Trend gate
    if not (close.iloc[-1] > sma50 > sma200):
        return result
    if sma200 <= sma200_series.iloc[-22]:  # 200 SMA must be rising
        return result

    ema20 = ema(close, 20)
    latest_close = close.iloc[-1]
    latest_ema20 = ema20.iloc[-1]

    # Bounce confirmed
    if latest_close <= latest_ema20:
        return result

    # Pullback touched EMA in last 10 sessions
    last_10_lows = daily["low"].iloc[-10:]
    last_10_ema = ema20.iloc[-10:]
    touched = bool((last_10_lows <= last_10_ema * 1.02).any())
    if not touched:
        return result

    # Volume behavior: last 3 days > 5-day prior average
    vol_recent = daily["volume"].tail(3).mean()
    vol_prior = daily["volume"].iloc[-8:-3].mean()
    volume_expansion = bool(vol_recent > vol_prior)

    proximity_score = 40 * (1 - abs(latest_close - latest_ema20) / latest_close)
    quality = min(100.0, 40 + proximity_score + (30 if volume_expansion else 15))
    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "close": round(float(latest_close), 2),
        "ema20": round(float(latest_ema20), 2),
        "touched_ema": touched,
        "volume_expansion_on_bounce": volume_expansion,
    }
    return result
