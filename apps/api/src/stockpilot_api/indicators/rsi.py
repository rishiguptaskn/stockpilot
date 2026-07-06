"""Relative Strength Index — Wilder's smoothing."""

from __future__ import annotations

import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Wilder's RSI over `window` periods.

    Per docs/RULEBOOK.md and [Mu] Murphy, RSI is used ONLY as context in the rule
    engine — it is never a standalone entry signal.

    Returns values in [0, 100].
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing (alpha = 1/n)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss
    result = 100 - (100 / (1 + rs))
    # When avg_loss == 0, rs is inf, RSI should be 100
    result = result.where(avg_loss != 0, 100.0)
    return result
