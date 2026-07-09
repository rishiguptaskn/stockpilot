"""Backtest configuration — every knob explicit, every default cited."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CostConfig:
    """Indian equity delivery (cash segment) transaction costs.

    Defaults reflect commonly published rates as of 2025-26.
    # TUNABLE — verify current SEBI/NSE/broker rate cards before trusting results.
    """

    # Brokerage per order: min(pct × notional, flat cap). Groww/Zerodha-style delivery.
    brokerage_pct: float = 0.0005  # 0.05%
    brokerage_cap_inr: float = 20.0  # ₹20 cap per order

    # Securities Transaction Tax — delivery: 0.1% on BOTH buy and sell.
    stt_pct: float = 0.001

    # NSE exchange transaction charge (equity delivery).
    exchange_txn_pct: float = 0.0000297  # 0.00297%

    # SEBI turnover fee (₹10 per crore).
    sebi_fee_pct: float = 0.000001  # 0.0001%

    # Stamp duty — BUY side only.
    stamp_duty_buy_pct: float = 0.00015  # 0.015%

    # GST on (brokerage + exchange txn + SEBI fee).
    gst_pct: float = 0.18

    # Slippage per side, applied to fill price (not a fee). Conservative default.
    slippage_pct: float = 0.001  # 0.1%


@dataclass(frozen=True)
class BacktestConfig:
    """Walk-forward simulation parameters.

    Risk limits follow Elder (The New Trading for a Living):
      - 2% max risk per trade
      - 6% max total open risk
    Swing horizon (2-20 trading days) per PLAN.md §5.
    """

    capital_inr: float = 500_000.0
    risk_per_trade_pct: float = 0.02  # Elder 2% rule
    max_open_risk_pct: float = 0.06  # Elder 6% rule
    max_positions: int = 5
    max_hold_days: int = 20  # swing time stop (trading days)
    scan_every_n_days: int = 5  # weekly scan cadence (trading days)
    min_score: float = 90.0  # aggregate score threshold to act (PLAN.md §8)
    costs: CostConfig = field(default_factory=CostConfig)
