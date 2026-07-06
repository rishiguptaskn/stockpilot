"""VCP — Volatility Contraction Pattern (Minervini).

A series of 2-6 progressively smaller pullbacks with declining volume, within
an established uptrend, culminating in a tight range ready to break out.

Detection algorithm (simplified — production tuning would validate against real charts):
  1. Stock must be in an uptrend (close > sma_50 > sma_200)
  2. Identify pullbacks in the last 6 months: peaks and troughs
  3. Each successive pullback must be shallower than the prior one
  4. Average volume must decline during contractions
  5. Latest range (last 5-10 days) must be the tightest of all

# TUNABLE — Minervini's book cites 2-6 contractions; we default to requiring ≥ 2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from stockpilot_api.indicators import sma


@dataclass
class VCPMetadata:
    pullback_depths: list[float]
    pivot_price: float | None
    contractions: int
    latest_range_pct: float


def _find_swing_extrema(close: pd.Series, window: int = 5) -> tuple[list[int], list[int]]:
    """
    Return (peak_idx_list, trough_idx_list) via a simple ±window comparison.
    """
    peaks: list[int] = []
    troughs: list[int] = []
    values = close.to_numpy()
    for i in range(window, len(values) - window):
        left = values[i - window : i]
        right = values[i + 1 : i + 1 + window]
        if values[i] > left.max() and values[i] > right.max():
            peaks.append(i)
        elif values[i] < left.min() and values[i] < right.min():
            troughs.append(i)
    return peaks, troughs


def detect_vcp(daily: pd.DataFrame, lookback: int = 130) -> dict:  # noqa: PLR0912
    """
    Detect VCP in the last `lookback` sessions.

    daily: DataFrame with columns [open, high, low, close, volume].
    Returns a dict with keys: pattern_name, detected, quality_score, metadata.
    """
    result = {
        "pattern_name": "VCP",
        "detected": False,
        "quality_score": 0.0,
        "metadata": {},
    }

    if len(daily) < 210:  # need enough for 200 SMA
        return result

    close = daily["close"]
    volume = daily["volume"]

    # 1) Uptrend gate: close > sma_50 > sma_200
    sma50_now = sma(close, 50).iloc[-1]
    sma200_now = sma(close, 200).iloc[-1]
    if not (close.iloc[-1] > sma50_now > sma200_now):
        return result

    # 2) Focus on lookback window
    window_close = close.tail(lookback).reset_index(drop=True)
    window_volume = volume.tail(lookback).reset_index(drop=True)
    peaks, troughs = _find_swing_extrema(window_close, window=5)

    if len(peaks) < 2 or len(troughs) < 2:
        return result

    # 3) Compute pullback depths from paired (peak, next-trough)
    pullbacks: list[tuple[int, int, float]] = []  # (peak_idx, trough_idx, depth_pct)
    for p in peaks:
        next_troughs = [t for t in troughs if t > p]
        if not next_troughs:
            continue
        t = next_troughs[0]
        depth_pct = (window_close.iloc[p] - window_close.iloc[t]) / window_close.iloc[p] * 100.0
        pullbacks.append((p, t, float(depth_pct)))

    if len(pullbacks) < 2:
        return result

    # 4) Successively shallower contractions
    depths = [pb[2] for pb in pullbacks]
    shallower = all(depths[i] > depths[i + 1] for i in range(len(depths) - 1))
    if not shallower:
        return result

    # 5) Volume declines across contraction phases
    vol_declining = True
    for i in range(len(pullbacks) - 1):
        p_start, t_start, _ = pullbacks[i]
        p_end, t_end, _ = pullbacks[i + 1]
        vol_prior = window_volume.iloc[p_start:t_start].mean() if t_start > p_start else np.nan
        vol_next = window_volume.iloc[p_end:t_end].mean() if t_end > p_end else np.nan
        if pd.notna(vol_prior) and pd.notna(vol_next) and vol_next >= vol_prior * 1.1:
            vol_declining = False
            break

    if not vol_declining:
        return result

    # 6) Latest range tightest
    latest_range_pct = (
        (window_close.tail(10).max() - window_close.tail(10).min())
        / window_close.iloc[-1]
        * 100.0
    )
    all_ranges = [
        (window_close.iloc[p : t + 1].max() - window_close.iloc[p : t + 1].min())
        / window_close.iloc[p]
        * 100.0
        for p, t, _ in pullbacks
    ]
    if all_ranges and latest_range_pct > min(all_ranges):
        return result  # latest not the tightest

    # Passed — score based on # of contractions and volume slope
    contractions = len(pullbacks)
    # More contractions = better (up to 5); tighter latest range = better
    contraction_score = min(contractions, 5) * 15  # 30-75 for 2-5 contractions
    tightness_score = max(0, 25 - latest_range_pct)  # 0-25
    quality = min(100.0, contraction_score + tightness_score)

    pivot_price = float(window_close.iloc[-lookback:].max())

    result["detected"] = True
    result["quality_score"] = round(quality, 2)
    result["metadata"] = {
        "pullback_depths": [round(d, 2) for d in depths],
        "contractions": contractions,
        "latest_range_pct": round(latest_range_pct, 2),
        "pivot_price": round(pivot_price, 2),
        "volume_declining": vol_declining,
    }
    return result
