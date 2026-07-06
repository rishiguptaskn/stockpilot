"""Shared pytest fixtures — reproducible synthetic OHLCV series."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def uptrend_close() -> pd.Series:
    """400 sessions of a clean uptrend + light noise. Rising 50/200 SMA."""
    rng = np.random.default_rng(seed=42)
    n = 400
    trend = np.linspace(100, 180, n)
    noise = rng.normal(0, 0.5, n)
    values = trend + noise
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(values, index=idx, name="close")


@pytest.fixture
def flat_close() -> pd.Series:
    """400 sessions of flat price around 100 with tight noise."""
    rng = np.random.default_rng(seed=7)
    n = 400
    values = 100 + rng.normal(0, 0.3, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.Series(values, index=idx, name="close")


@pytest.fixture
def uptrend_ohlcv() -> pd.DataFrame:
    """400 sessions of a clean uptrend OHLCV frame with realistic volume."""
    rng = np.random.default_rng(seed=42)
    n = 400
    trend = np.linspace(100, 180, n)
    close = trend + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.2, 1.0, n)
    low = close - rng.uniform(0.2, 1.0, n)
    open_ = close + rng.normal(0, 0.3, n)
    volume = rng.integers(500_000, 2_000_000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


@pytest.fixture
def downtrend_ohlcv() -> pd.DataFrame:
    """400 sessions descending — used to prove Module 1 fails M1.1/M1.4."""
    rng = np.random.default_rng(seed=13)
    n = 400
    trend = np.linspace(180, 100, n)
    close = trend + rng.normal(0, 0.5, n)
    high = close + rng.uniform(0.2, 1.0, n)
    low = close - rng.uniform(0.2, 1.0, n)
    open_ = close + rng.normal(0, 0.3, n)
    volume = rng.integers(500_000, 2_000_000, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )
