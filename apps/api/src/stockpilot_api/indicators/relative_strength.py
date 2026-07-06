"""Relative Strength rank — a stock's 252-day return percentile vs a universe."""

from __future__ import annotations

import pandas as pd


def total_return_252(close: pd.Series) -> float:
    """
    Trailing 252-day total return as a decimal (e.g., 0.35 = +35%).
    Uses close_today / close_252_days_ago - 1.
    Returns NaN if fewer than 253 observations.
    """
    if len(close) < 253:
        return float("nan")
    return float(close.iloc[-1] / close.iloc[-253] - 1)


def rs_rank_252(stock_close: pd.Series, universe_returns: list[float]) -> float:
    """
    Percentile rank (0-100) of stock's 252-day return within the universe.

    `universe_returns` is a list of 252-day total returns for every stock in the
    tradable universe (excluding this stock). We return where this stock sits.

    Per [O] O'Neil: RS >= 80 is the minimum threshold; RS >= 90 for leaders.
    Per [Mv] Minervini: Trend Template requires RS rank >= 70.
    """
    r = total_return_252(stock_close)
    if pd.isna(r) or not universe_returns:
        return float("nan")

    valid = [x for x in universe_returns if x == x]  # drop NaN
    if not valid:
        return float("nan")

    count_below = sum(1 for u in valid if u < r)
    return 100.0 * count_below / len(valid)
