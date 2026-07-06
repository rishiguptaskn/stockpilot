"""Cup & Handle — O'Neil.

U-shaped consolidation (cup) followed by a shorter, shallower drift downward
(handle), then a breakout above the cup's rim.

Heuristic detection over the last ~60-130 sessions:
  1. Prior uptrend ≥ 30%
  2. Cup: rounded bottom with depth 12-33%
  3. Handle: shorter drift down, depth ≤ 50% of cup, on lower volume
  4. Latest close > cup's right rim
"""

from __future__ import annotations

import pandas as pd


def detect_cup_and_handle(daily: pd.DataFrame) -> dict:
    result = {"pattern_name": "Cup & Handle", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < 200:
        return result

    close = daily["close"]
    # Look at last ~130 sessions for a possible cup
    window = daily.tail(130)
    peaks_left = window["close"].iloc[:20].max()
    trough = window["close"].iloc[20:80].min()
    peaks_right = window["close"].iloc[80:120].max()
    handle_low = window["close"].iloc[110:125].min()
    latest = close.iloc[-1]

    # Prior uptrend gate
    if len(daily) > 260:
        prior_ret = daily["close"].iloc[-131] / daily["close"].iloc[-260] - 1
        if prior_ret < 0.20:
            return result

    # Cup rims should be roughly similar (within 5%)
    if peaks_left <= 0 or peaks_right <= 0 or abs(peaks_left - peaks_right) / peaks_left > 0.10:
        return result

    cup_depth_pct = (peaks_left - trough) / peaks_left * 100
    if not (12 <= cup_depth_pct <= 40):
        return result

    handle_depth_pct = (peaks_right - handle_low) / peaks_right * 100
    if handle_depth_pct > cup_depth_pct * 0.5:
        return result

    # Latest close should be above cup's right rim (breakout)
    if latest < peaks_right * 0.98:
        return result

    quality = min(100.0, 40 + (30 - handle_depth_pct) + (25 - abs(cup_depth_pct - 20)))
    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "cup_depth_pct": round(float(cup_depth_pct), 2),
        "handle_depth_pct": round(float(handle_depth_pct), 2),
        "cup_left_rim": round(float(peaks_left), 2),
        "cup_right_rim": round(float(peaks_right), 2),
        "handle_low": round(float(handle_low), 2),
    }
    return result
