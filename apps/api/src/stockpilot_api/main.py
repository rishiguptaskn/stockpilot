"""FastAPI application entry point."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from stockpilot_api import __version__
from stockpilot_api.engine.module_1_market import RULES as M1_RULES
from stockpilot_api.engine.module_2_sector import RULES as M2_RULES
from stockpilot_api.engine.module_3_fundamentals import RULES as M3_RULES
from stockpilot_api.engine.module_4_technical import RULES as M4_RULES
from stockpilot_api.engine.module_5_moving_averages import RULES as M5_RULES
from stockpilot_api.engine.module_6_momentum import RULES as M6_RULES
from stockpilot_api.engine.module_7_volume import RULES as M7_RULES
from stockpilot_api.engine.module_8_news import RULES as M8_RULES
from stockpilot_api.engine.module_9_risk import RULES as M9_RULES
from stockpilot_api.engine.module_10_portfolio import RULES as M10_RULES
from stockpilot_api.routers.agents import router as agents_router
from stockpilot_api.routers.backtest import router as backtest_router
from stockpilot_api.workflow import run_workflow

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="StockPilot API",
    version=__version__,
    description="Full rule engine (10 modules · 206 rules) + 8 pattern detectors + scoring + yfinance ingestion.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(agents_router)
app.include_router(backtest_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/info")
def info() -> dict[str, object]:
    total_rules = sum(
        len(x) for x in [
            M1_RULES, M2_RULES, M3_RULES, M4_RULES, M5_RULES,
            M6_RULES, M7_RULES, M8_RULES, M9_RULES, M10_RULES,
        ]
    )
    return {
        "name": "StockPilot API",
        "version": __version__,
        "modules_implemented": [f"M{i}" for i in range(1, 11)],
        "patterns_implemented": [
            "VCP", "Cup & Handle", "Flat Base", "Bull Flag",
            "Darvas Box", "Ascending Triangle", "Stage 2 Breakout", "EMA Pullback",
        ],
        "total_rules_implemented": total_rules,
        "total_rules_target": 206,
        "module_rule_counts": {
            "M1": len(M1_RULES), "M2": len(M2_RULES), "M3": len(M3_RULES),
            "M4": len(M4_RULES), "M5": len(M5_RULES), "M6": len(M6_RULES),
            "M7": len(M7_RULES), "M8": len(M8_RULES), "M9": len(M9_RULES),
            "M10": len(M10_RULES),
        },
    }


# M1 rules whose inputs are static v1 defaults (not live data) — the UI labels
# these "estimated" so a default never masquerades as a live reading.
# Real from Nifty OHLCV: M1.1-M1.5, M1.8. Proxied by Nifty: M1.9, M1.10.
_M1_STATIC_INPUT_RULES = frozenset(
    {"M1.6", "M1.7", "M1.11", "M1.12", "M1.13", "M1.14", "M1.15"}
)
_M1_PROXY_RULES = frozenset({"M1.9", "M1.10"})


@app.get("/market/environment")
def market_environment() -> dict:
    """Module 1 (Market Environment) evaluated on FRESH Nifty data.

    Honest by construction: every check reports whether its input is live
    (Nifty OHLCV), a proxy (mid/small-cap reuse Nifty in v1), or a static
    default (VIX/FII/breadth — ingestion pending).
    """
    from stockpilot_api.engine.module_1_market import evaluate_market_environment
    from stockpilot_api.workflow import _build_market_context, _fetch_daily

    nifty = _fetch_daily("^NSEI", period="2y")
    if nifty.empty or len(nifty) < 200:
        raise HTTPException(status_code=503, detail="Could not fetch Nifty history")

    module = evaluate_market_environment(_build_market_context(nifty))

    if not module.hard_gates_passed:
        verdict = "bearish"
    elif module.score >= 70:
        verdict = "bullish"
    else:
        verdict = "neutral"

    return {
        "as_of": nifty.index[-1].date().isoformat(),
        "nifty_close": round(float(nifty["close"].iloc[-1]), 2),
        "score": module.score,
        "verdict": verdict,
        "hard_gates_passed": module.hard_gates_passed,
        "checks": [
            {
                "rule_id": r.rule_id,
                "label": str(r.threshold),
                "passed": r.passed,
                "detail": str(r.actual_value),
                "hard_gate": r.is_hard_gate,
                "citation": r.source_citation,
                "input_quality": (
                    "static_default"
                    if r.rule_id in _M1_STATIC_INPUT_RULES
                    else "proxy"
                    if r.rule_id in _M1_PROXY_RULES
                    else "live"
                ),
            }
            for r in module.rule_evaluations
        ],
    }


class RunWorkflowInput(BaseModel):
    tickers: list[str]
    capital_inr: float = 500_000.0


@app.post("/engine/run-workflow")
def run_workflow_endpoint(payload: RunWorkflowInput) -> dict:
    """
    Execute the full pipeline against the given tickers.

    For each ticker:
      1. Fetch 2y OHLCV via yfinance
      2. Compute Modules 1-10 + all 8 pattern detectors
      3. Aggregate to a 0-100 score
      4. Verdict: candidate (>=90) / watch (85-89) / reject

    Returns a ranked list of candidates. Does NOT write to Supabase in v1 —
    that step is left to the caller so we don't need service_role credentials.
    """
    if not payload.tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")
    if len(payload.tickers) > 50:
        raise HTTPException(status_code=400, detail="Max 50 tickers per request (v1 rate limit)")

    result = run_workflow(payload.tickers, capital_inr=payload.capital_inr)
    return result


@app.get("/engine/quick-score/{ticker}")
def quick_score(ticker: str) -> dict:
    """Score a single ticker synchronously — for the Stock Detail page."""
    result = run_workflow([ticker])
    if not result.get("all_results"):
        raise HTTPException(status_code=404, detail=f"Could not score {ticker}")
    return result["all_results"][0]
