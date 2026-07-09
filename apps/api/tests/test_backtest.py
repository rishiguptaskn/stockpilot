"""Backtester tests — golden values on synthetic data. No network, no AI."""

from __future__ import annotations

import pandas as pd
import pytest

from stockpilot_api.backtest import (
    BacktestConfig,
    CostConfig,
    TradeSignal,
    buy_costs_inr,
    compute_metrics,
    run_backtest,
    sell_costs_inr,
)
from stockpilot_api.backtest.metrics import cagr_pct, max_drawdown_pct

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

ZERO_COSTS = CostConfig(
    brokerage_pct=0.0,
    brokerage_cap_inr=0.0,
    stt_pct=0.0,
    exchange_txn_pct=0.0,
    sebi_fee_pct=0.0,
    stamp_duty_buy_pct=0.0,
    gst_pct=0.0,
    slippage_pct=0.0,
)


def bars(ohlc: list[tuple[float, float, float, float]], start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(ohlc))
    df = pd.DataFrame(ohlc, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1_000_000
    return df


def flat(n: int, price: float = 100.0) -> list[tuple[float, float, float, float]]:
    return [(price, price + 1, price - 1, price)] * n


def scan_once(signals: list[TradeSignal]):
    """Return a scan_fn that emits `signals` on the first scan day only."""
    fired = {"done": False}

    def scan(as_of: pd.Timestamp, slices: dict[str, pd.DataFrame]) -> list[TradeSignal]:
        if fired["done"]:
            return []
        fired["done"] = True
        return signals

    return scan


def sig(ticker: str = "TEST.NS", entry: float = 100.0, stop: float = 93.0,
        target: float = 121.0, score: float = 95.0) -> TradeSignal:
    return TradeSignal(
        ticker=ticker,
        signal_date=pd.Timestamp("2024-01-01"),
        entry=entry,
        stop=stop,
        target=target,
        score=score,
    )


ZERO_COST_CFG = BacktestConfig(costs=ZERO_COSTS)

# ---------------------------------------------------------------------------
# costs — golden values (hand-computed from the defaults in CostConfig)
# ---------------------------------------------------------------------------


class TestCosts:
    def test_buy_costs_golden_100k(self):
        # brokerage min(50, 20)=20; STT 100; exch 2.97; SEBI 0.10; stamp 15;
        # GST 0.18*(20+2.97+0.10)=4.1526  → total 142.2226
        assert buy_costs_inr(100_000, CostConfig()) == pytest.approx(142.2226)

    def test_sell_costs_golden_100k(self):
        # same minus stamp duty → 127.2226
        assert sell_costs_inr(100_000, CostConfig()) == pytest.approx(127.2226)

    def test_brokerage_cap_applies(self):
        # 10k notional: 0.05% = 5 < cap 20 → brokerage 5
        # buy: 5 + 10 + 0.297 + 0.01 + 1.5 + 0.18*(5+0.297+0.01) = 17.76226
        assert buy_costs_inr(10_000, CostConfig()) == pytest.approx(17.76226)

    def test_zero_costs(self):
        assert buy_costs_inr(100_000, ZERO_COSTS) == 0.0
        assert sell_costs_inr(100_000, ZERO_COSTS) == 0.0


# ---------------------------------------------------------------------------
# metrics — golden values
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_cagr_doubling_in_two_years(self):
        # 505 points = 504 intervals = exactly 2 years of 252 → 2^(1/2)-1 = 41.42%
        equity = pd.Series([100.0] * 504 + [200.0])
        equity.iloc[0] = 100.0
        assert cagr_pct(equity) == pytest.approx(41.4214, abs=1e-3)

    def test_max_drawdown(self):
        equity = pd.Series([100.0, 120.0, 90.0, 130.0])
        assert max_drawdown_pct(equity) == pytest.approx(25.0)

    def test_empty_series_safe(self):
        assert cagr_pct(pd.Series(dtype=float)) == 0.0
        assert max_drawdown_pct(pd.Series(dtype=float)) == 0.0


# ---------------------------------------------------------------------------
# engine — fills, exits, risk caps (zero costs → exact arithmetic)
# ---------------------------------------------------------------------------


class TestEngineFills:
    def test_entry_is_next_day_open_no_lookahead(self):
        # signal on d0 (close 100); d1 opens at 102 → fill MUST be 102, never d0's close
        data = {"TEST.NS": bars([(100, 101, 99, 100), (102, 103, 101, 102)] + flat(28, 102))}
        result = run_backtest(data, scan_once([sig(stop=90.0, target=200.0)]), ZERO_COST_CFG)
        assert result.open_positions_curve.iloc[0] == 0  # nothing filled on signal day
        assert result.open_positions_curve.iloc[1] == 1  # filled the next day
        assert len(result.trades) == 1  # 30 flat bars → time stop closes it
        t = result.trades[0]
        assert t.entry_fill == 102.0  # d1 open, not the signal-day close of 100
        assert t.exit_reason == "time"

    def test_target_exit_r_multiple_is_3(self):
        # entry fill 100 (d1 open), stop 93, target 121 → R:R exactly 1:3
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100),
                (105, 122, 104, 120)] + flat(10, 120)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig()]), ZERO_COST_CFG)
        assert len(result.trades) == 1
        t = result.trades[0]
        assert t.exit_reason == "target"
        assert t.exit_fill == 121.0
        assert t.shares == 1428  # floor(2% of 500k / (100-93)) = floor(10000/7)
        assert t.r_multiple == pytest.approx(3.0)
        assert t.pnl_inr == pytest.approx(21 * 1428)

    def test_stop_exit_r_multiple_is_minus_1(self):
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (96, 97, 92, 94)] + flat(10, 94)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig()]), ZERO_COST_CFG)
        assert len(result.trades) == 1
        t = result.trades[0]
        assert t.exit_reason == "stop"
        assert t.exit_fill == 93.0
        assert t.r_multiple == pytest.approx(-1.0)

    def test_gap_down_exits_at_open_not_stop(self):
        # d2 opens at 85, below the 93 stop → fill at 85 (pessimistic), R < -1
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (85, 88, 84, 86)] + flat(10, 86)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig()]), ZERO_COST_CFG)
        t = result.trades[0]
        assert t.exit_reason == "gap_stop"
        assert t.exit_fill == 85.0
        assert t.r_multiple == pytest.approx((85 - 100) / 7, abs=1e-3)

    def test_stop_checked_before_target_same_bar(self):
        # one violent bar touches both 93 and 121 → conservative: assume stop
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 125, 92, 110)] + flat(10, 110)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig()]), ZERO_COST_CFG)
        assert result.trades[0].exit_reason == "stop"

    def test_time_stop_after_max_hold_days(self):
        # price never hits stop or target → forced exit after 20 trading days
        rows = [(100, 101, 99, 100)] + flat(30, 100)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig(stop=80.0, target=200.0)]),
                              ZERO_COST_CFG)
        assert len(result.trades) == 1
        t = result.trades[0]
        assert t.exit_reason == "time"
        assert t.holding_days == 20

    def test_entry_gapping_below_stop_is_skipped(self):
        # d1 opens at 90, below the 93 stop → entry must never fill
        rows = [(100, 101, 99, 100), (90, 91, 89, 90)] + flat(10, 90)
        result = run_backtest({"TEST.NS": bars(rows)}, scan_once([sig()]), ZERO_COST_CFG)
        assert len(result.trades) == 0
        assert result.skipped_signals["gap_below_stop"] == 1


class TestTrailingExit:
    def test_trail_exit_on_close_below_ema(self):
        # steady rise then a sharp break below the short EMA → "trail" exit
        rows = [(100, 101, 99, 100)] + [(100 + i, 101 + i, 99 + i, 100 + i) for i in range(1, 10)]
        rows += [(108, 109, 95, 96)] + flat(5, 96)  # hard close below the rising EMA
        cfg = BacktestConfig(costs=ZERO_COSTS, use_target=False, trail_ema_days=5,
                             max_hold_days=50)
        result = run_backtest({"T.NS": bars(rows)},
                              scan_once([sig(ticker="T.NS", stop=80.0, target=999.0)]), cfg)
        assert len(result.trades) == 1
        assert result.trades[0].exit_reason == "trail"

    def test_no_target_exit_when_use_target_false(self):
        # price rockets through the old 3R target but use_target=False → no target exit
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 130, 99, 128)] + flat(4, 128)
        cfg = BacktestConfig(costs=ZERO_COSTS, use_target=False, max_hold_days=5)
        result = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]), cfg)
        assert len(result.trades) == 1
        assert result.trades[0].exit_reason == "time"  # held to the time stop instead

    def test_stop_still_wins_over_trail(self):
        # both stop-touch and EMA-break same bar → stop (conservative ordering)
        rows = [(100, 101, 99, 100)] + flat(3, 100) + [(100, 101, 92, 93)] + flat(4, 93)
        cfg = BacktestConfig(costs=ZERO_COSTS, use_target=False, trail_ema_days=3,
                             max_hold_days=50)
        result = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]), cfg)
        assert result.trades[0].exit_reason == "stop"


class TestEngineRiskCaps:
    def test_two_pct_position_sizing(self):
        # 2% of 500,000 = 10,000 risk budget; risk/share 7 → 1428 shares
        rows = flat(15, 100)
        result = run_backtest({"A.NS": bars(rows)}, scan_once([sig(ticker="A.NS")]),
                              ZERO_COST_CFG)
        assert result.open_positions_curve.max() == 1  # entered
        # verify via the eventual time-stop close
        cfg = BacktestConfig(costs=ZERO_COSTS, max_hold_days=5)
        result2 = run_backtest({"A.NS": bars(flat(15, 100))},
                               scan_once([sig(ticker="A.NS", stop=93.0, target=500.0)]), cfg)
        assert result2.trades[0].shares == 1428

    def test_six_pct_open_risk_cap_blocks_fourth_position(self):
        # 3 positions × 2% = 6% cap reached → 4th signal must be skipped
        tickers = ["A.NS", "B.NS", "C.NS", "D.NS"]
        data = {t: bars(flat(15, 100)) for t in tickers}
        signals = [sig(ticker=t, stop=93.0, target=500.0) for t in tickers]
        result = run_backtest(data, scan_once(signals), ZERO_COST_CFG)
        assert result.skipped_signals["six_pct_open_risk_cap"] == 1
        assert result.open_positions_curve.max() == 3

    def test_below_min_score_is_skipped(self):
        data = {"A.NS": bars(flat(15, 100))}
        result = run_backtest(data, scan_once([sig(ticker="A.NS", score=80.0)]), ZERO_COST_CFG)
        assert len(result.trades) == 0
        assert result.skipped_signals["below_min_score"] == 1

    def test_invalid_stop_at_or_above_entry_is_skipped(self):
        data = {"A.NS": bars(flat(15, 100))}
        result = run_backtest(data, scan_once([sig(ticker="A.NS", stop=100.0)]), ZERO_COST_CFG)
        assert result.skipped_signals["invalid_stop"] == 1

    def test_no_duplicate_position_same_ticker(self):
        data = {"A.NS": bars(flat(30, 100))}

        def always_signal(as_of, slices):
            return [sig(ticker="A.NS", stop=80.0, target=500.0)]

        result = run_backtest(data, always_signal, ZERO_COST_CFG)
        assert result.open_positions_curve.max() == 1
        assert result.skipped_signals["already_holding"] >= 1


class TestEngineAccounting:
    def test_costs_and_slippage_reduce_pnl(self):
        # identical scenario with and without costs → costful PnL strictly lower
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100),
                (105, 122, 104, 120)] + flat(10, 120)
        free = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]),
                            ZERO_COST_CFG)
        costly = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]),
                              BacktestConfig())  # real default costs
        assert len(free.trades) == len(costly.trades) == 1
        assert costly.trades[0].pnl_inr < free.trades[0].pnl_inr
        assert costly.trades[0].costs_inr > 0

    def test_equity_curve_conserves_money_zero_costs(self):
        # with zero costs, final equity == initial + sum(trade pnl)
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (96, 97, 92, 94)] + flat(10, 94)
        result = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]),
                              ZERO_COST_CFG)
        expected = 500_000.0 + sum(t.pnl_inr for t in result.trades)
        assert float(result.equity_curve.iloc[-1]) == pytest.approx(expected)

    def test_metrics_from_result(self):
        rows = [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 99, 100),
                (105, 122, 104, 120)] + flat(10, 120)
        result = run_backtest({"T.NS": bars(rows)}, scan_once([sig(ticker="T.NS")]),
                              ZERO_COST_CFG)
        m = compute_metrics(result)
        assert m.n_trades == 1
        assert m.win_rate_pct == 100.0
        assert m.expectancy_r == pytest.approx(3.0)
        assert m.exit_reason_counts == {"target": 1}
        assert m.max_drawdown_pct >= 0.0

    def test_empty_data_returns_empty_result(self):
        result = run_backtest({}, scan_once([]), ZERO_COST_CFG)
        assert result.trades == []
        assert len(result.equity_curve) == 0
