"""Deterministic data access for MCP tools.

Every number an agent ever sees enters the system here. This module pulls free
OHLCV via yfinance (reusing the existing ingestion fetcher) and normalises it to
a DatetimeIndex'd frame the rule engine expects. A small per-process cache avoids
refetching the same ticker across the 3-4 tool calls in one analysis.

No LLM ever calls yfinance or invents data — it can only reason over what this
module returns.
"""

from __future__ import annotations

import logging

import pandas as pd

from stockpilot_api.ingestion.yfinance_sync import fetch_daily_ohlcv

logger = logging.getLogger(__name__)

_MIN_BARS = 200  # rule engine needs >= 200 trading days for 200-DMA rules

# Process-local cache: ticker -> daily frame (empty frame means "fetched, no data").
_CACHE: dict[str, pd.DataFrame] = {}


def clear_cache() -> None:
    """Drop the in-memory cache (used by tests and force-refresh)."""
    _CACHE.clear()


def load_daily(ticker: str, *, period: str = "2y") -> pd.DataFrame:
    """Return normalised daily OHLCV with a DatetimeIndex, or an empty frame.

    Cached per process. The rule engine modules resample to weekly and index by
    position, so a DatetimeIndex is required (ingestion returns date objects).
    """
    key = ticker.upper()
    if key in _CACHE:
        return _CACHE[key]

    df = fetch_daily_ohlcv(key, period=period)
    if not df.empty:
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df.index.name = "date"
    _CACHE[key] = df
    return df


def has_sufficient_history(df: pd.DataFrame) -> bool:
    return not df.empty and len(df) >= _MIN_BARS


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    return (
        daily.resample("W-FRI")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
