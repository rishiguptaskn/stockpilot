"""Exponential Moving Average — standard 2/(n+1) smoothing."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, window: int) -> pd.Series:
    """
    Standard EMA with alpha = 2/(window+1).

    Uses `adjust=False` to match TradingView / most charting platforms:
      EMA_t = alpha * price_t + (1 - alpha) * EMA_{t-1}

    First `window - 1` values are NaN so this aligns with SMA behavior.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    result = series.ewm(span=window, adjust=False, min_periods=window).mean()
    return result
