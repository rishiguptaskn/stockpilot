"""Average True Range — Wilder's smoothing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    True Range per Wilder:
      TR = max( high - low,
                |high - prev_close|,
                |low  - prev_close| )
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Average True Range with Wilder's smoothing (equivalent to EMA with alpha = 1/n).

    First `window` values are NaN.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")

    tr = true_range(high, low, close)
    # Wilder's smoothing: alpha = 1/n → span = 2n - 1 in pandas ewm terms
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean().where(
        np.arange(len(tr)) >= window - 1
    )
