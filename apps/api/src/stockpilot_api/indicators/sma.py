"""Simple Moving Average."""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    Simple moving average over `window` periods.

    Returns a Series with the same index as `series`. First `window - 1` values are NaN.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    return series.rolling(window=window, min_periods=window).mean()
