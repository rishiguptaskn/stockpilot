"""Tests for the technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stockpilot_api.indicators import atr, ema, rsi, sma
from stockpilot_api.indicators.relative_strength import rs_rank_252, total_return_252


# ---- SMA -------------------------------------------------------------------


def test_sma_matches_manual_average() -> None:
    s = pd.Series([1, 2, 3, 4, 5])
    result = sma(s, 3)
    # First 2 values NaN, then rolling means
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert result.iloc[3] == pytest.approx(3.0)  # (2+3+4)/3
    assert result.iloc[4] == pytest.approx(4.0)  # (3+4+5)/3


def test_sma_rejects_non_positive_window() -> None:
    with pytest.raises(ValueError):
        sma(pd.Series([1, 2, 3]), 0)


def test_sma_on_uptrend_is_monotonic_late(uptrend_close: pd.Series) -> None:
    result = sma(uptrend_close, 50)
    # Late in the series, the SMA should be rising
    tail = result.dropna().tail(50)
    assert (tail.diff().dropna() > 0).mean() > 0.9  # >90% of steps rising


# ---- EMA -------------------------------------------------------------------


def test_ema_flat_input_equals_constant() -> None:
    """On a constant series, EMA converges to that constant."""
    s = pd.Series([100.0] * 20)
    result = ema(s, 5).dropna()
    assert np.allclose(result.values, 100.0)


def test_ema_warmup_period_produces_nan() -> None:
    """First `window - 1` values must be NaN (matching SMA behavior for alignment)."""
    s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    result = ema(s, 3)
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert not pd.isna(result.iloc[2])


def test_ema_lags_less_than_sma_on_uptrend(uptrend_close: pd.Series) -> None:
    """EMA should be closer to the current price than SMA in a trending market."""
    sma50 = sma(uptrend_close, 50).iloc[-1]
    ema20 = ema(uptrend_close, 20).iloc[-1]
    latest = uptrend_close.iloc[-1]
    # In an uptrend, latest > ema20 > sma50 typically
    assert latest > ema20 > sma50


# ---- ATR -------------------------------------------------------------------


def test_atr_positive_on_realistic_data(uptrend_ohlcv: pd.DataFrame) -> None:
    result = atr(uptrend_ohlcv["high"], uptrend_ohlcv["low"], uptrend_ohlcv["close"], 14)
    assert (result.dropna() > 0).all()


def test_atr_rejects_bad_window(uptrend_ohlcv: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        atr(uptrend_ohlcv["high"], uptrend_ohlcv["low"], uptrend_ohlcv["close"], -1)


# ---- RSI -------------------------------------------------------------------


def test_rsi_in_range_0_100(uptrend_close: pd.Series) -> None:
    result = rsi(uptrend_close, 14).dropna()
    assert (result >= 0).all()
    assert (result <= 100).all()


def test_rsi_uptrend_biased_above_50(uptrend_close: pd.Series) -> None:
    """A steady uptrend should push RSI above 50 on average."""
    result = rsi(uptrend_close, 14).dropna()
    assert result.mean() > 55


def test_rsi_all_gains_hits_100() -> None:
    """RSI when there are no losses should be exactly 100."""
    s = pd.Series([100.0 + i for i in range(30)])
    result = rsi(s, 14).dropna()
    assert result.iloc[-1] == pytest.approx(100.0)


# ---- Relative Strength -----------------------------------------------------


def test_total_return_252_needs_enough_history() -> None:
    s = pd.Series(np.arange(100.0))
    assert np.isnan(total_return_252(s))


def test_total_return_252_computes_correct_value() -> None:
    s = pd.Series([100.0] * 253)
    s.iloc[-1] = 150.0
    assert total_return_252(s) == pytest.approx(0.5, rel=1e-3)


def test_rs_rank_252_percentile_correct() -> None:
    # Stock with 50% return; universe returns spanning -20% to +30%
    idx = pd.date_range("2024-01-01", periods=253, freq="B")
    stock = pd.Series([100.0] * 253, index=idx)
    stock.iloc[-1] = 150.0  # +50%
    universe = [-0.20, -0.10, 0.0, 0.10, 0.20, 0.30]
    # All 6 universe returns are below 50%, so rank should be 100
    assert rs_rank_252(stock, universe) == pytest.approx(100.0)


def test_rs_rank_252_middle_stock() -> None:
    idx = pd.date_range("2024-01-01", periods=253, freq="B")
    stock = pd.Series([100.0] * 253, index=idx)
    stock.iloc[-1] = 110.0  # +10%
    universe = [-0.20, -0.10, 0.0, 0.05, 0.15, 0.20, 0.30, 0.40]
    # 4 of 8 universe returns are below 10% → rank = 50
    assert rs_rank_252(stock, universe) == pytest.approx(50.0)
