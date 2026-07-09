"""Backtest runner — wires the PRODUCTION rule engine into the backtest engine.

The scan adapter calls the same `_score_stock` that powers the live workflow,
on point-in-time slices only. No logic is duplicated; what you backtest is
exactly what runs live.

Usage:
    python -m stockpilot_api.backtest.run --tickers RELIANCE.NS,TCS.NS --period 5y
    python -m stockpilot_api.backtest.run                     # default sample universe
    python -m stockpilot_api.backtest.run --min-score 85      # act on watch-level too

HONEST CAVEATS (printed with every report):
  - Modules 3 (fundamentals) and 8 (news) use neutral defaults in the current
    workflow — this backtest validates the PRICE/TECHNICAL/RISK rules only.
  - Market context uses static VIX/FII defaults (only index trend is real).
  - Universe is today's ticker list → survivorship bias (delisted losers absent).
  - yfinance data is unofficial and may contain errors.
Positive expectancy here is NECESSARY but not sufficient before live capital.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import replace

import pandas as pd

from stockpilot_api.backtest.config import BacktestConfig
from stockpilot_api.backtest.engine import BacktestResult, TradeSignal, run_backtest
from stockpilot_api.backtest.metrics import compute_metrics
from stockpilot_api.indicators.relative_strength import total_return_252
from stockpilot_api.workflow import _build_market_context, _fetch_daily, _score_stock

logger = logging.getLogger(__name__)

# Liquid NSE large-caps as a small default sample. Replace with NSE-500 for real runs.
DEFAULT_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "LT.NS", "MARUTI.NS", "TITAN.NS", "SUNPHARMA.NS",
]

MIN_BARS = 260  # ≥ 253 for RS-252 + headroom


def make_rule_engine_scan_fn(nifty: pd.DataFrame, capital_inr: float, min_score: float):
    """Adapter: point-in-time slices -> production rule engine -> TradeSignals."""

    def scan_fn(as_of: pd.Timestamp, slices: dict[str, pd.DataFrame]) -> list[TradeSignal]:
        nifty_slice = nifty.loc[:as_of]
        if len(nifty_slice) < 200:
            return []
        market_ctx = _build_market_context(nifty_slice)

        # Cross-sectional RS rank computed ONLY from data available at as_of
        returns: dict[str, float] = {}
        for ticker, df in slices.items():
            if len(df) >= MIN_BARS:
                r = total_return_252(df["close"])
                if r == r:  # not NaN
                    returns[ticker] = r
        if not returns:
            return []
        peer_returns = list(returns.values())

        signals: list[TradeSignal] = []
        for ticker, stock_return in returns.items():
            rs_rank = 100.0 * sum(1 for r in peer_returns if r < stock_return) / len(peer_returns)
            try:
                candidate = _score_stock(
                    ticker=ticker,
                    daily=slices[ticker],
                    market_ctx=market_ctx,
                    sector_ctx=None,
                    rs_rank=rs_rank,
                    capital_inr=capital_inr,
                )
            except Exception:
                logger.exception("scoring failed for %s on %s", ticker, as_of.date())
                continue
            if candidate is None:
                continue
            if candidate.aggregate_score >= min_score and candidate.hard_gates_all_passed:
                signals.append(
                    TradeSignal(
                        ticker=ticker,
                        signal_date=as_of,
                        entry=candidate.entry,
                        stop=candidate.stop,
                        target=candidate.target,
                        score=candidate.aggregate_score,
                    )
                )
        return signals

    return scan_fn


CAVEATS = [
    "Modules 3 (fundamentals) and 8 (news) used neutral defaults — "
    "only price/technical/risk rules were validated.",
    "Market context: only index trend is real; VIX/FII/breadth are static defaults.",
    "Survivorship bias: universe is today's listing; delisted losers are absent.",
    "Data source is yfinance (unofficial); bars may contain errors.",
    "Positive expectancy is necessary but NOT sufficient before live capital.",
]


def run(
    tickers: list[str],
    period: str = "5y",
    config: BacktestConfig | None = None,
) -> tuple[BacktestResult, dict]:
    """Fetch data, run the backtest, return (result, report_dict)."""
    cfg = config or BacktestConfig()

    logger.info("Fetching %s of history for %d tickers + Nifty…", period, len(tickers))
    nifty = _fetch_daily("^NSEI", period=period)
    if nifty.empty or len(nifty) < 200:
        raise RuntimeError("Failed to fetch Nifty history — cannot build market context.")

    data: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = _fetch_daily(t, period=period)
        if len(df) >= MIN_BARS:
            data[t] = df
        else:
            logger.warning("Dropping %s — only %d bars (< %d)", t, len(df), MIN_BARS)
    if not data:
        raise RuntimeError("No tickers with sufficient history.")

    scan_fn = make_rule_engine_scan_fn(nifty, cfg.capital_inr, cfg.min_score)
    result = run_backtest(data, scan_fn, cfg)
    metrics = compute_metrics(result)

    report = {
        "period": period,
        "universe": sorted(data.keys()),
        "config": {
            "capital_inr": cfg.capital_inr,
            "risk_per_trade_pct": cfg.risk_per_trade_pct,
            "max_open_risk_pct": cfg.max_open_risk_pct,
            "max_positions": cfg.max_positions,
            "max_hold_days": cfg.max_hold_days,
            "scan_every_n_days": cfg.scan_every_n_days,
            "min_score": cfg.min_score,
        },
        "metrics": metrics.to_dict(),
        "skipped_signals": dict(result.skipped_signals),
        "trades": [
            {
                "ticker": t.ticker,
                "entry_date": t.entry_date.date().isoformat(),
                "exit_date": t.exit_date.date().isoformat(),
                "entry": t.entry_fill,
                "exit": t.exit_fill,
                "shares": t.shares,
                "pnl_inr": t.pnl_inr,
                "r": t.r_multiple,
                "reason": t.exit_reason,
                "score": t.signal_score,
                "days": t.holding_days,
            }
            for t in result.trades
        ],
        "caveats": CAVEATS,
        "verdict": (
            "POSITIVE expectancy after costs"
            if metrics.expectancy_r > 0 and metrics.n_trades > 0
            else "NO EDGE DEMONSTRATED (expectancy <= 0 or no trades)"
        ),
    }
    return result, report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
    parser = argparse.ArgumentParser(description="StockPilot deterministic backtester")
    parser.add_argument("--tickers", default=",".join(DEFAULT_UNIVERSE),
                        help="Comma-separated .NS tickers")
    parser.add_argument("--period", default="5y", help="yfinance period (e.g. 2y, 5y)")
    parser.add_argument("--capital", type=float, default=500_000.0)
    parser.add_argument("--min-score", type=float, default=90.0)
    parser.add_argument("--json-out", default=None, help="Write full report JSON to this path")
    args = parser.parse_args()

    cfg = replace(BacktestConfig(), capital_inr=args.capital, min_score=args.min_score)
    _, report = run([t.strip() for t in args.tickers.split(",") if t.strip()], args.period, cfg)

    print(json.dumps({k: v for k, v in report.items() if k != "trades"}, indent=2))
    print(f"\nTrades: {len(report['trades'])}")
    for tr in report["trades"]:
        print(f"  {tr['ticker']:<16} {tr['entry_date']} -> {tr['exit_date']}"
              f"  {tr['reason']:<8} R={tr['r']:+.2f}  PnL=₹{tr['pnl_inr']:+,.0f}")
    print(f"\nVERDICT: {report['verdict']}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Full report written to {args.json_out}")


if __name__ == "__main__":  # pragma: no cover
    main()
