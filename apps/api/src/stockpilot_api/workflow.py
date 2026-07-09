"""End-to-end workflow orchestration.

Given a list of tickers, fetches OHLCV via yfinance, computes all 10 module
scores + all 8 pattern detectors, aggregates via scoring pipeline, and returns
a ranked list of candidates.

This is what powers the "Run workflow" button on the Today page.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

import pandas as pd
import yfinance as yf

from stockpilot_api.engine.module_1_market import MarketContext, evaluate_market_environment
from stockpilot_api.engine.module_2_sector import SectorContext, evaluate_sector_strength
from stockpilot_api.engine.module_3_fundamentals import FundamentalsContext, evaluate_fundamentals
from stockpilot_api.engine.module_4_technical import TechnicalContext, evaluate_technical_analysis
from stockpilot_api.engine.module_5_moving_averages import MovingAveragesContext, evaluate_moving_averages
from stockpilot_api.engine.module_6_momentum import MomentumContext, evaluate_momentum
from stockpilot_api.engine.module_7_volume import VolumeContext, evaluate_volume
from stockpilot_api.engine.module_8_news import NewsContext, evaluate_news
from stockpilot_api.engine.module_9_risk import RiskContext, evaluate_risk_management
from stockpilot_api.engine.module_10_portfolio import PortfolioContext, evaluate_portfolio_fit
from stockpilot_api.indicators.relative_strength import total_return_252
from stockpilot_api.models import ModuleScore
from stockpilot_api.patterns import detect_all_patterns
from stockpilot_api.scoring import aggregate_scores

logger = logging.getLogger(__name__)


@dataclass
class CandidateOutput:
    ticker: str
    aggregate_score: float
    verdict: str
    hard_gates_all_passed: bool
    module_scores: dict[str, float]
    detected_patterns: list[str]
    entry: float
    stop: float
    target: float
    shares: int
    metadata: dict = field(default_factory=dict)


def _fetch_daily(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        raw = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    except Exception as e:
        logger.warning("yfinance failed for %s: %s", ticker, e)
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(1, axis=1)
    df = raw.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )[["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index)
    return df.dropna()


def _to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    return daily.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()


def _default_fundamentals() -> FundamentalsContext:
    """Neutral defaults when real fundamentals aren't available."""
    return FundamentalsContext(
        q_eps_yoy_growth=0.25,
        q_eps_yoy_growth_prior_q=0.20,
        q_revenue_yoy_growth=0.20,
        q_earnings_surprise=0.0,
        eps_cagr_3y=0.25,
        roe_annual=0.18,
        net_income_positive_3y=True,
        debt_to_equity=0.5,
        close=0.0,
        high_52w=0.0,
        days_since_high_20d=0,
        shares_outstanding=100_000_000,
        promoter_holding_pct=45.0,
        promoter_holding_change_4q=0.0,
        has_recent_buyback=False,
        equity_dilution_pct_365d=0.0,
        rs_rank_252=50.0,
        stock_63d_return=0.0,
        sector_63d_return=0.0,
        institutional_holding_change_qoq=0.0,
        institutional_holders_count_change_qoq=0,
        has_quality_mf_holder=True,
    )


def _score_stock(
    ticker: str,
    daily: pd.DataFrame,
    market_ctx: MarketContext,
    sector_ctx: SectorContext | None,
    rs_rank: float,
    capital_inr: float = 500_000.0,
    include_details: bool = False,
) -> CandidateOutput | None:
    if len(daily) < 200:
        return None

    weekly = _to_weekly(daily)
    close = daily["close"]
    latest_price = float(close.iloc[-1])

    # Modules independent of trade plan first
    m1 = evaluate_market_environment(market_ctx)
    m2 = (
        evaluate_sector_strength(sector_ctx)
        if sector_ctx is not None
        else ModuleScore(module_id="M2", module_name="Sector Strength", score=70.0,
                          weight_in_aggregate=10, rule_evaluations=[], hard_gates_passed=True)
    )

    fund_ctx = _default_fundamentals()
    # Fill in what we can compute from price data
    fund_ctx_dict = fund_ctx.__dict__.copy()
    fund_ctx_dict["close"] = latest_price
    fund_ctx_dict["high_52w"] = float(close.tail(252).max()) if len(close) >= 252 else latest_price
    fund_ctx_dict["rs_rank_252"] = rs_rank
    if len(close) >= 64:
        fund_ctx_dict["stock_63d_return"] = float(close.iloc[-1] / close.iloc[-64] - 1)
    fund_ctx_updated = FundamentalsContext(**fund_ctx_dict)
    m3 = evaluate_fundamentals(fund_ctx_updated)

    m5 = evaluate_moving_averages(MovingAveragesContext(daily=daily, rs_rank_252=rs_rank))
    m6 = evaluate_momentum(MomentumContext(daily=daily))
    m7 = evaluate_volume(VolumeContext(daily=daily))
    m8 = evaluate_news(NewsContext())  # neutral defaults

    # Detect patterns
    patterns = detect_all_patterns(daily)
    pattern_names = [p["pattern_name"] for p in patterns]

    # Suggested trade plan: entry = latest close; stop = 7% below; target = 3R above
    entry = latest_price
    stop = round(entry * 0.93, 2)  # 7% stop (within Elder 8% + O'Neil 7-8% cap)
    risk_per_share = entry - stop
    target = round(entry + risk_per_share * 3.0, 2)  # 1:3 R:R
    max_risk_inr = capital_inr * 0.02
    shares = int(max_risk_inr // risk_per_share) if risk_per_share > 0 else 0

    m4 = evaluate_technical_analysis(TechnicalContext(
        daily=daily,
        weekly=weekly,
        rs_rank_252=rs_rank,
        module_1_score=m1.score,
        module_2_score=m2.score,
        module_3_score=m3.score,
        module_9_score=95.0,  # placeholder — computed after M9 runs
        entry=entry,
        stop=stop,
        target=target,
        detected_patterns=pattern_names,
    ))

    m9 = evaluate_risk_management(RiskContext(
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        shares=shares,
        atr_14=None,
        capital_inr=capital_inr,
    ))

    m10 = evaluate_portfolio_fit(PortfolioContext(
        available_cash=capital_inr,
        proposed_notional=entry * shares,
        total_portfolio=capital_inr,
        cash_pct=100.0,
        single_stock_pct_after_trade=(entry * shares) / capital_inr * 100,
        sector_pct_after_trade=(entry * shares) / capital_inr * 100,
    ))

    all_modules = [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10]
    verdict = aggregate_scores(all_modules)

    metadata: dict = {}
    if include_details:
        # Full per-rule breakdown for the explainability engine (ARCHITECTURE.md §13)
        metadata["module_details"] = [m.model_dump(mode="json") for m in all_modules]

    return CandidateOutput(
        ticker=ticker,
        aggregate_score=verdict.aggregate_score,
        verdict=verdict.verdict,
        hard_gates_all_passed=verdict.hard_gates_all_passed,
        module_scores={m.module_id: m.score for m in all_modules},
        detected_patterns=pattern_names,
        entry=entry,
        stop=stop,
        target=target,
        shares=shares,
        metadata=metadata,
    )


def _build_market_context(nifty_daily: pd.DataFrame) -> MarketContext:
    """Build a MarketContext from Nifty data alone (v1 simplification)."""
    return MarketContext(
        nifty=nifty_daily,
        nifty_midcap=nifty_daily,  # v1: reuse Nifty as proxy
        nifty_smallcap=nifty_daily,
        india_vix=15.0,   # neutral default; real data comes from ingestion later
        fii_net_10d=1000.0,  # neutral positive default
        dii_net_10d=800.0,
        usd_inr_change_20d=0.0,
        in10y_bp_change_20d=0.0,
        advance_count=1200,
        decline_count=1000,
        days_since_follow_through=10,
    )


def run_workflow(tickers: Iterable[str], capital_inr: float = 500_000.0) -> dict:
    """
    Score every ticker against the full 10-module engine + 8 pattern detectors.

    Returns a dict with:
      - candidates: list of CandidateOutput with verdict "candidate" (>= 90) or "watch" (85-89)
      - all_results: full ranked list
      - as_of: today's date
    """
    logger.info("Running workflow for %d tickers", len(list(tickers) if not isinstance(tickers, list) else tickers))
    tickers_list = list(tickers)

    # Fetch Nifty 50 for market context
    nifty = _fetch_daily("^NSEI", period="2y")
    if nifty.empty or len(nifty) < 200:
        return {"error": "Failed to fetch Nifty 50 data", "candidates": [], "all_results": []}

    market_ctx = _build_market_context(nifty)

    # For each ticker, fetch and score
    all_results: list[CandidateOutput] = []
    universe_returns: list[float] = []

    fetched: dict[str, pd.DataFrame] = {}
    for ticker in tickers_list:
        daily = _fetch_daily(ticker, period="2y")
        if not daily.empty and len(daily) >= 253:
            fetched[ticker] = daily
            universe_returns.append(total_return_252(daily["close"]))

    for ticker, daily in fetched.items():
        stock_return = total_return_252(daily["close"])
        peer_returns = [r for r in universe_returns if r == r]  # drop NaN
        if peer_returns:
            rs_rank = 100.0 * sum(1 for r in peer_returns if r < stock_return) / len(peer_returns)
        else:
            rs_rank = 50.0

        try:
            candidate = _score_stock(
                ticker=ticker,
                daily=daily,
                market_ctx=market_ctx,
                sector_ctx=None,  # v1: skip sector-level for now
                rs_rank=rs_rank,
                capital_inr=capital_inr,
            )
            if candidate:
                all_results.append(candidate)
        except Exception as e:
            logger.warning("Failed to score %s: %s", ticker, e)

    all_results.sort(key=lambda c: c.aggregate_score, reverse=True)
    surfaced = [c for c in all_results if c.verdict in ("candidate", "watch")]

    return {
        "as_of": date.today().isoformat(),
        "universe_size": len(fetched),
        "candidates": [_to_dict(c) for c in surfaced],
        "all_results": [_to_dict(c) for c in all_results[:20]],  # top 20
    }


def _to_dict(c: CandidateOutput) -> dict:
    return {
        "ticker": c.ticker,
        "aggregate_score": c.aggregate_score,
        "verdict": c.verdict,
        "hard_gates_all_passed": c.hard_gates_all_passed,
        "module_scores": c.module_scores,
        "detected_patterns": c.detected_patterns,
        "entry": c.entry,
        "stop": c.stop,
        "target": c.target,
        "shares": c.shares,
    }
