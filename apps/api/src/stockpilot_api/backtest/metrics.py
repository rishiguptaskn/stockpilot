"""Performance metrics — pure functions over trades + equity curve.

Expectancy and R-multiples follow Elder / Tharp conventions:
  R          = initial risk on the trade (entry_fill − stop) × shares
  R-multiple = net PnL / R
  Expectancy = mean R-multiple across all trades (must be > 0 after costs)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from stockpilot_api.backtest.engine import BacktestResult

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestMetrics:
    n_trades: int
    win_rate_pct: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float  # mean R-multiple, net of costs — THE edge number
    total_pnl_inr: float
    total_costs_inr: float
    final_equity_inr: float
    cagr_pct: float
    max_drawdown_pct: float
    exposure_pct: float  # % of days with at least one open position
    avg_holding_days: float
    exit_reason_counts: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(result: BacktestResult) -> BacktestMetrics:
    trades = result.trades
    equity = result.equity_curve

    n = len(trades)
    wins = [t for t in trades if t.pnl_inr > 0]
    losses = [t for t in trades if t.pnl_inr <= 0]

    win_rate = 100.0 * len(wins) / n if n else 0.0
    avg_win_r = sum(t.r_multiple for t in wins) / len(wins) if wins else 0.0
    avg_loss_r = sum(t.r_multiple for t in losses) / len(losses) if losses else 0.0
    expectancy = sum(t.r_multiple for t in trades) / n if n else 0.0

    total_pnl = sum(t.pnl_inr for t in trades)
    total_costs = sum(t.costs_inr for t in trades)

    exit_counts: dict[str, int] = {}
    for t in trades:
        exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1

    avg_hold = sum(t.holding_days for t in trades) / n if n else 0.0

    return BacktestMetrics(
        n_trades=n,
        win_rate_pct=round(win_rate, 2),
        avg_win_r=round(avg_win_r, 3),
        avg_loss_r=round(avg_loss_r, 3),
        expectancy_r=round(expectancy, 3),
        total_pnl_inr=round(total_pnl, 2),
        total_costs_inr=round(total_costs, 2),
        final_equity_inr=round(float(equity.iloc[-1]), 2) if len(equity) else 0.0,
        cagr_pct=round(cagr_pct(equity), 2),
        max_drawdown_pct=round(max_drawdown_pct(equity), 2),
        exposure_pct=round(exposure_pct(result.open_positions_curve), 2),
        avg_holding_days=round(avg_hold, 1),
        exit_reason_counts=exit_counts,
    )


def cagr_pct(equity: pd.Series) -> float:
    """Compound annual growth rate from the daily equity curve, in percent."""
    if len(equity) < 2:
        return 0.0
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0:
        return 0.0
    years = (len(equity) - 1) / TRADING_DAYS_PER_YEAR
    if years <= 0:
        return 0.0
    return ((end / start) ** (1 / years) - 1) * 100.0


def max_drawdown_pct(equity: pd.Series) -> float:
    """Largest peak-to-trough decline of the equity curve, in percent (positive number)."""
    if len(equity) < 2:
        return 0.0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    return float(-drawdown.min()) * 100.0


def exposure_pct(open_positions_curve: pd.Series) -> float:
    """Percentage of trading days with at least one open position."""
    if len(open_positions_curve) == 0:
        return 0.0
    return 100.0 * float((open_positions_curve > 0).mean())
