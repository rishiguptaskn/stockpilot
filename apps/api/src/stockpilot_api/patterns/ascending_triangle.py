"""Ascending Triangle — Murphy.

Flat horizontal resistance at top with 3+ touches; rising trendline of higher
lows below with 3+ touches; breakout above horizontal resistance on volume.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def detect_ascending_triangle(daily: pd.DataFrame, window: int = 40) -> dict:
    result = {"pattern_name": "Ascending Triangle", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < window + 10:
        return result

    tail = daily.tail(window).copy()
    close = tail["close"]
    high = tail["high"]
    low = tail["low"]

    # Horizontal resistance: highs cluster within 2% of the max
    max_h = float(high.max())
    touches_at_top = int((high >= max_h * 0.98).sum())
    if touches_at_top < 3:
        return result

    # Rising lows: linear regression slope of `low` should be positive
    x = np.arange(len(low))
    slope = np.polyfit(x, low.values, 1)[0]
    if slope <= 0:
        return result

    touches_bottom = int((abs(low - (slope * x + np.polyfit(x, low.values, 1)[1])) < 0.02 * max_h).sum())

    # Latest close breaks above the horizontal resistance
    latest = close.iloc[-1]
    if latest < max_h * 0.99:
        return result

    # Volume expansion on breakout
    vol_avg = daily["volume"].tail(window).iloc[:-1].mean()
    breakout_vol = float(daily["volume"].iloc[-1])
    volume_ok = bool(breakout_vol >= vol_avg * 1.3)
    if not volume_ok:
        return result

    quality = min(100.0, 30 + touches_at_top * 5 + max(0, touches_bottom) * 3 + min(20, slope * 100))
    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "resistance": round(max_h, 2),
        "touches_at_top": touches_at_top,
        "rising_lows_slope": round(float(slope), 4),
        "breakout_close": round(float(latest), 2),
        "breakout_volume_ratio": round(breakout_vol / vol_avg, 2) if vol_avg else 0,
    }
    return result
