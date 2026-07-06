"""Darvas Box — Nicolas Darvas.

Consolidation range formed after a new 52-week high; box top = highest high,
box bottom = lowest low that holds. Buy on breakout above box top with volume.
"""

from __future__ import annotations

import pandas as pd


def detect_darvas_box(daily: pd.DataFrame, box_window: int = 20) -> dict:
    result = {"pattern_name": "Darvas Box", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < 260:
        return result

    close = daily["close"]

    # Was there a new 52-week high in the last 60 sessions?
    last_60_max = close.tail(60).max()
    full_52w_max = close.tail(252).max()
    if last_60_max < full_52w_max - 0.5:  # slack for floating-point
        return result

    # Since that recent peak, has price consolidated in a box for ≥ box_window days?
    peak_idx = close.tail(60).idxmax()
    idx_pos = close.index.get_loc(peak_idx)
    after_peak = close.iloc[idx_pos:]
    if len(after_peak) < box_window:
        return result

    box_top = after_peak.max()
    box_bottom = after_peak.min()
    if box_top - box_bottom <= 0:
        return result

    range_pct = (box_top - box_bottom) / box_top * 100

    # Breakout: latest close ≥ box_top
    latest = close.iloc[-1]
    if latest < box_top * 0.99:
        return result

    # Volume: latest > avg of box period
    vol_avg_box = daily["volume"].iloc[idx_pos:-1].mean() if idx_pos < len(daily) - 1 else 0
    volume_ok = bool(daily["volume"].iloc[-1] >= vol_avg_box * 1.3)
    if not volume_ok:
        return result

    quality = min(100.0, 40 + (25 - range_pct) + min(30, len(after_peak) - box_window) + 15)
    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "box_top": round(float(box_top), 2),
        "box_bottom": round(float(box_bottom), 2),
        "box_range_pct": round(float(range_pct), 2),
        "days_in_box": int(len(after_peak)),
        "breakout_close": round(float(latest), 2),
    }
    return result
