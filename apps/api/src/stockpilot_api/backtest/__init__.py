"""Deterministic backtester — the trust gate (ARCHITECTURE.md §14).

Point-in-time, walk-forward simulation of the rule engine over historical
OHLCV with realistic Indian equity delivery costs and Elder risk rules.

No AI anywhere in this package. Pure functions of numeric input.
"""

from stockpilot_api.backtest.config import BacktestConfig, CostConfig
from stockpilot_api.backtest.costs import buy_costs_inr, sell_costs_inr
from stockpilot_api.backtest.engine import (
    BacktestResult,
    ClosedTrade,
    Position,
    TradeSignal,
    run_backtest,
)
from stockpilot_api.backtest.metrics import BacktestMetrics, compute_metrics

__all__ = [
    "BacktestConfig",
    "CostConfig",
    "buy_costs_inr",
    "sell_costs_inr",
    "TradeSignal",
    "Position",
    "ClosedTrade",
    "BacktestResult",
    "run_backtest",
    "BacktestMetrics",
    "compute_metrics",
]
