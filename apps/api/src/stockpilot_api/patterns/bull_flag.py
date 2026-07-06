"""Bull Flag — Murphy / classical TA.

Strong pole (15-30% rally in 1-4 weeks) followed by tight downward-sloping
consolidation (flag, 3-15 days), then breakout above the flag high.
"""

from __future__ import annotations

import pandas as pd


def detect_bull_flag(daily: pd.DataFrame) -> dict:
    result = {"pattern_name": "Bull Flag", "detected": False, "quality_score": 0.0, "metadata": {}}
    if len(daily) < 30:
        return result

    close = daily["close"]
    # Pole: last 20 days before the flag (approx)
    pole_start_idx = -25
    pole_end_idx = -10
    pole_start = close.iloc[pole_start_idx]
    pole_end = close.iloc[pole_end_idx]
    pole_ret = pole_end / pole_start - 1
    if not (0.10 <= pole_ret <= 0.40):
        return result

    # Flag: last ~10 days, tight downward drift
    flag = daily.iloc[pole_end_idx:]
    flag_high = flag["high"].max()
    flag_low = flag["low"].min()
    flag_depth = (flag_high - flag_low) / flag_high
    if flag_depth > 0.40 * pole_ret:  # flag depth ≤ 40% of pole
        return result

    # Latest breakout above flag_high
    if close.iloc[-1] < flag_high * 0.99:
        return result

    # Volume: flag avg < pole avg (drying)
    pole_vol = daily["volume"].iloc[pole_start_idx:pole_end_idx].mean()
    flag_vol_prior = daily["volume"].iloc[pole_end_idx:-1].mean()  # exclude breakout day
    volume_declining = bool(flag_vol_prior < pole_vol)

    # Volume expansion on breakout
    breakout_vol = daily["volume"].iloc[-1]
    volume_expansion = bool(breakout_vol >= flag_vol_prior * 1.5)

    if not volume_expansion:
        return result

    quality = min(100.0, 30 + pole_ret * 100 + (30 if volume_declining else 0) + 20)
    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "pole_return_pct": round(float(pole_ret) * 100, 2),
        "flag_depth_pct": round(float(flag_depth) * 100, 2),
        "flag_high": round(float(flag_high), 2),
        "breakout_close": round(float(close.iloc[-1]), 2),
        "volume_declining_in_flag": volume_declining,
        "volume_expansion_on_breakout": volume_expansion,
    }
    return result
