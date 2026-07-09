"""Indian equity delivery transaction costs — deterministic, per side.

Slippage is NOT included here; it adjusts the fill price in the engine.
"""

from __future__ import annotations

from stockpilot_api.backtest.config import CostConfig


def _brokerage_inr(notional_inr: float, costs: CostConfig) -> float:
    return min(notional_inr * costs.brokerage_pct, costs.brokerage_cap_inr)


def buy_costs_inr(notional_inr: float, costs: CostConfig) -> float:
    """Total charges on a delivery BUY of `notional_inr` (price × shares)."""
    brokerage = _brokerage_inr(notional_inr, costs)
    stt = notional_inr * costs.stt_pct
    exchange = notional_inr * costs.exchange_txn_pct
    sebi = notional_inr * costs.sebi_fee_pct
    stamp = notional_inr * costs.stamp_duty_buy_pct
    gst = (brokerage + exchange + sebi) * costs.gst_pct
    return brokerage + stt + exchange + sebi + stamp + gst


def sell_costs_inr(notional_inr: float, costs: CostConfig) -> float:
    """Total charges on a delivery SELL of `notional_inr` (no stamp duty)."""
    brokerage = _brokerage_inr(notional_inr, costs)
    stt = notional_inr * costs.stt_pct
    exchange = notional_inr * costs.exchange_txn_pct
    sebi = notional_inr * costs.sebi_fee_pct
    gst = (brokerage + exchange + sebi) * costs.gst_pct
    return brokerage + stt + exchange + sebi + gst
