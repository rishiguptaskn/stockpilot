"""Walk-forward backtest engine — point-in-time, no look-ahead, no AI.

Contract:
  - `scan_fn(as_of, slices)` receives ONLY data up to and including `as_of`
    (point-in-time slices) and returns trade signals. The production adapter
    wraps the real rule engine; tests inject synthetic signals.
  - Signals generated on day T are filled at day T+1's OPEN (+slippage).
    This is what makes look-ahead bias structurally impossible.

Conservative fill rules (pessimistic by design):
  - Gap below stop at open  → exit at open (not at the stop price)
  - Stop and target both touched in one bar → assume STOP hit first
  - Entry that gaps at/below its stop → skipped, never filled
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Literal

import pandas as pd

from stockpilot_api.backtest.config import BacktestConfig
from stockpilot_api.backtest.costs import buy_costs_inr, sell_costs_inr

logger = logging.getLogger(__name__)

ExitReason = Literal["stop", "gap_stop", "target", "time"]


@dataclass(frozen=True)
class TradeSignal:
    """A candidate produced by the scan on `signal_date` (acted on next bar)."""

    ticker: str
    signal_date: pd.Timestamp
    entry: float  # planned entry (signal-day close)
    stop: float
    target: float
    score: float


@dataclass
class Position:
    ticker: str
    entry_date: pd.Timestamp
    entry_fill: float
    shares: int
    stop: float
    target: float
    entry_costs_inr: float
    signal_score: float
    holding_days: int = 0

    @property
    def initial_risk_inr(self) -> float:
        return (self.entry_fill - self.stop) * self.shares


@dataclass(frozen=True)
class ClosedTrade:
    ticker: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_fill: float
    exit_fill: float
    shares: int
    stop: float
    target: float
    costs_inr: float  # entry + exit charges
    pnl_inr: float  # net of all costs
    r_multiple: float  # net pnl / initial risk
    exit_reason: ExitReason
    signal_score: float
    holding_days: int


@dataclass
class BacktestResult:
    trades: list[ClosedTrade]
    equity_curve: pd.Series  # daily mark-to-market, indexed by date
    open_positions_curve: pd.Series  # count of open positions per day
    skipped_signals: Counter  # reason -> count (honest accounting, no silent drops)
    config: BacktestConfig = field(repr=False, default_factory=BacktestConfig)


ScanFn = Callable[[pd.Timestamp, dict[str, pd.DataFrame]], list[TradeSignal]]


def run_backtest(
    data: dict[str, pd.DataFrame],
    scan_fn: ScanFn,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """
    Simulate the strategy over `data` (ticker -> full daily OHLCV history).

    Each DataFrame must have columns [open, high, low, close, volume] and a
    DatetimeIndex. The engine walks the union calendar chronologically:
      1. fill pending entries at today's open
      2. process exits (gap / stop / target / time)
      3. on scan days, call scan_fn with point-in-time slices
      4. mark equity to market at today's closes
    """
    cfg = config or BacktestConfig()
    costs = cfg.costs

    calendar = sorted(set().union(*(df.index for df in data.values())))
    if not calendar:
        return BacktestResult([], pd.Series(dtype=float), pd.Series(dtype=int), Counter(), cfg)

    cash = cfg.capital_inr
    open_positions: dict[str, Position] = {}
    pending: list[TradeSignal] = []
    trades: list[ClosedTrade] = []
    skipped: Counter = Counter()
    equity_points: dict[pd.Timestamp, float] = {}
    open_count_points: dict[pd.Timestamp, int] = {}
    last_close: dict[str, float] = {}
    last_equity = cfg.capital_inr

    for i, today in enumerate(calendar):
        bars = {t: df.loc[today] for t, df in data.items() if today in df.index}

        # ---- 1. Fill pending entries at today's open -----------------------
        for sig in pending:
            bar = bars.get(sig.ticker)
            if bar is None:
                skipped["no_bar_on_entry_day"] += 1
                continue
            if sig.ticker in open_positions:
                skipped["already_holding"] += 1
                continue
            fill = float(bar["open"]) * (1 + costs.slippage_pct)
            if fill <= sig.stop:
                skipped["gap_below_stop"] += 1
                continue

            # Elder 2% rule: risk budget from current equity, not initial capital
            risk_budget = last_equity * cfg.risk_per_trade_pct
            risk_per_share = fill - sig.stop
            shares = int(risk_budget // risk_per_share)
            if shares <= 0:
                skipped["risk_per_share_too_large"] += 1
                continue

            # Elder 6% rule: total open risk cap
            open_risk = sum(p.initial_risk_inr for p in open_positions.values())
            max_open_risk = last_equity * cfg.max_open_risk_pct
            if open_risk + shares * risk_per_share > max_open_risk:
                skipped["six_pct_open_risk_cap"] += 1
                continue
            if len(open_positions) >= cfg.max_positions:
                skipped["max_positions"] += 1
                continue

            notional = fill * shares
            entry_charges = buy_costs_inr(notional, costs)
            if notional + entry_charges > cash:
                # size down to available cash rather than skip outright
                shares = int(cash // (fill * (1 + 0.01)))  # 1% headroom for charges
                if shares <= 0:
                    skipped["insufficient_cash"] += 1
                    continue
                notional = fill * shares
                entry_charges = buy_costs_inr(notional, costs)

            cash -= notional + entry_charges
            open_positions[sig.ticker] = Position(
                ticker=sig.ticker,
                entry_date=today,
                entry_fill=fill,
                shares=shares,
                stop=sig.stop,
                target=sig.target,
                entry_costs_inr=entry_charges,
                signal_score=sig.score,
            )
        pending = []

        # ---- 2. Process exits ----------------------------------------------
        for ticker in list(open_positions):
            pos = open_positions[ticker]
            bar = bars.get(ticker)
            if bar is None:
                continue  # holiday / missing bar for this ticker
            o, h, lo, c = (float(bar[k]) for k in ("open", "high", "low", "close"))

            exit_fill: float | None = None
            reason: ExitReason | None = None
            entered_today = pos.entry_date == today

            if o <= pos.stop and not entered_today:
                exit_fill = o * (1 - costs.slippage_pct)  # gapped through the stop
                reason = "gap_stop"
            elif lo <= pos.stop:
                exit_fill = pos.stop * (1 - costs.slippage_pct)
                reason = "stop"  # conservative: stop checked BEFORE target
            elif h >= pos.target:
                exit_fill = pos.target  # limit order — no slippage
                reason = "target"
            else:
                pos.holding_days += 1
                if pos.holding_days >= cfg.max_hold_days:
                    exit_fill = c * (1 - costs.slippage_pct)
                    reason = "time"

            if exit_fill is not None and reason is not None:
                notional = exit_fill * pos.shares
                exit_charges = sell_costs_inr(notional, costs)
                total_costs = pos.entry_costs_inr + exit_charges
                pnl = (exit_fill - pos.entry_fill) * pos.shares - total_costs
                risk = pos.initial_risk_inr
                trades.append(
                    ClosedTrade(
                        ticker=ticker,
                        entry_date=pos.entry_date,
                        exit_date=today,
                        entry_fill=pos.entry_fill,
                        exit_fill=exit_fill,
                        shares=pos.shares,
                        stop=pos.stop,
                        target=pos.target,
                        costs_inr=round(total_costs, 2),
                        pnl_inr=round(pnl, 2),
                        r_multiple=round(pnl / risk, 3) if risk > 0 else 0.0,
                        exit_reason=reason,
                        signal_score=pos.signal_score,
                        holding_days=pos.holding_days,
                    )
                )
                cash += notional - exit_charges
                del open_positions[ticker]

        # ---- 3. Scan for new signals (point-in-time slices only) -----------
        if i % cfg.scan_every_n_days == 0:
            slices = {t: df.loc[:today] for t, df in data.items() if today in df.index}
            try:
                signals = scan_fn(today, slices)
            except Exception:
                logger.exception("scan_fn failed on %s — skipping scan day", today)
                signals = []
            for sig in signals:
                if sig.ticker in open_positions:
                    skipped["already_holding"] += 1
                elif sig.score < cfg.min_score:
                    skipped["below_min_score"] += 1
                elif sig.stop >= sig.entry:
                    skipped["invalid_stop"] += 1
                else:
                    pending.append(sig)

        # ---- 4. Mark to market ----------------------------------------------
        for t, bar in bars.items():
            last_close[t] = float(bar["close"])
        holdings_value = sum(
            p.shares * last_close.get(t, p.entry_fill) for t, p in open_positions.items()
        )
        last_equity = cash + holdings_value
        equity_points[today] = last_equity
        open_count_points[today] = len(open_positions)

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series(equity_points, name="equity"),
        open_positions_curve=pd.Series(open_count_points, name="open_positions"),
        skipped_signals=skipped,
        config=cfg,
    )
