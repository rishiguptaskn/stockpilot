"""Flat Base — O'Neil.

Sideways consolidation within ~15% range after a prior uptrend, minimum 5 weeks.
Volume typically dries up during the base.
"""

from __future__ import annotations

import pandas as pd


def detect_flat_base(daily: pd.DataFrame, base_window: int = 25) -> dict:
    result = {"pattern_name": "Flat Base", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < 125:
        return result

    base = daily.tail(base_window)
    high = base["high"].max()
    low = base["low"].min()
    range_pct = (high - low) / high * 100
    if range_pct > 15.0:
        return result

    # Prior uptrend of ≥ 20% over the 100 sessions before the base
    if len(daily) < base_window + 100:
        return result
    prior_start = daily["close"].iloc[-(base_window + 100)]
    prior_end = daily["close"].iloc[-base_window - 1]
    if prior_end / prior_start - 1 < 0.20:
        return result

    # Volume drying: last 5 avg < prior 20 avg
    vol_last5 = base["volume"].tail(5).mean()
    vol_prior = base["volume"].head(base_window - 5).mean()
    volume_drying = bool(vol_last5 < vol_prior)

    tightness_score = max(0, 60 - range_pct * 2)  # 60 if 0%, 30 if 15%
    volume_score = 20 if volume_drying else 0
    duration_score = min(20, base_window)
    quality = min(100.0, tightness_score + volume_score + duration_score)

    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "base_range_pct": round(float(range_pct), 2),
        "base_window": base_window,
        "volume_drying": volume_drying,
        "base_high": round(float(high), 2),
        "base_low": round(float(low), 2),
    }
    return result
