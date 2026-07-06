"""Stage 2 Breakout — Weinstein.

Transition from Stage 1 (base) to Stage 2 (uptrend):
  1. Weekly close breaks above the resistance high of the Stage 1 base
  2. Weekly 30-week SMA is flat or turning up
  3. Volume on the breakout week is ≥ 2× the 30-week average

Weinstein's methodology — one of the safest entries because it captures the
transition from accumulation to markup.
"""

from __future__ import annotations

import pandas as pd

from stockpilot_api.indicators import sma


def _resample_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    return daily.resample("W-FRI").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    ).dropna()


def detect_stage_2_breakout(daily: pd.DataFrame, stage_1_lookback_weeks: int = 10) -> dict:
    """
    Detect a Stage 2 breakout on the weekly chart.

    daily: DataFrame with columns [open, high, low, close, volume], DatetimeIndex.
    stage_1_lookback_weeks: minimum weeks of Stage 1 base before breakout counts.

    # TUNABLE — Weinstein cites at least 10 weeks in Stage 1.
    """
    result = {
        "pattern_name": "Stage 2 Breakout",
        "detected": False,
        "quality_score": 0.0,
        "metadata": {},
    }

    weekly = _resample_weekly(daily)
    if len(weekly) < 32:  # need 30 for SMA + 2 for delta
        return result

    close = weekly["close"]
    volume = weekly["volume"]
    high = weekly["high"]

    sma30 = sma(close, 30)
    if sma30.iloc[-1] != sma30.iloc[-1]:  # NaN check
        return result

    # Latest week's close and prior weeks
    latest_close = float(close.iloc[-1])
    prior_high_stage1 = float(high.iloc[-stage_1_lookback_weeks - 1 : -1].max())

    # Rule 1: breakout above prior resistance
    if latest_close <= prior_high_stage1:
        return result

    # Rule 2: 30-week SMA flat or turning up (slope over last 5 weeks)
    if len(sma30) < 5:
        return result
    sma30_slope_up = sma30.iloc[-1] >= sma30.iloc[-5]  # flat or up
    if not sma30_slope_up:
        return result

    # Rule 3: breakout week volume ≥ 2× 30-week avg
    avg_vol_30w = volume.iloc[-31:-1].mean()  # exclude the breakout week itself
    latest_vol = float(volume.iloc[-1])
    if latest_vol < avg_vol_30w * 2.0:
        return result

    # Bonus: how tight was Stage 1? Tighter = higher quality
    stage_1_range = (
        high.iloc[-stage_1_lookback_weeks - 1 : -1].max()
        - close.iloc[-stage_1_lookback_weeks - 1 : -1].min()
    )
    stage_1_tightness_pct = float(stage_1_range / prior_high_stage1 * 100.0)

    # Quality: base tightness + volume expansion
    tightness_score = max(0, 40 - stage_1_tightness_pct)  # 0-40 (tighter = higher)
    volume_ratio = latest_vol / avg_vol_30w
    volume_score = min(30, (volume_ratio - 2) * 15)  # 0-30 for 2× to 4×
    duration_score = min(30, stage_1_lookback_weeks * 2)  # 20-60
    quality = min(100.0, tightness_score + volume_score + duration_score)

    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "prior_resistance": round(prior_high_stage1, 2),
        "breakout_close": round(latest_close, 2),
        "sma30_slope_up": sma30_slope_up,
        "breakout_volume_ratio": round(volume_ratio, 2),
        "stage_1_tightness_pct": round(stage_1_tightness_pct, 2),
        "stage_1_weeks": stage_1_lookback_weeks,
    }
    return result
