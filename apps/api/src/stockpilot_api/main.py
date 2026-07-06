"""FastAPI application entry point.

Endpoints:
  GET  /health              → liveness check
  GET  /info                → app metadata (version, rule count)
  POST /engine/module-1     → evaluate Module 1 (Market Environment)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockpilot_api import __version__
from stockpilot_api.engine import evaluate_market_environment
from stockpilot_api.engine.module_1_market import MODULE_NAME, RULES

app = FastAPI(
    title="StockPilot API",
    version=__version__,
    description="Rule engine + indicators + ingestion. See docs/RULEBOOK.md.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/info")
def info() -> dict[str, object]:
    return {
        "name": "StockPilot API",
        "version": __version__,
        "modules_implemented": ["M1"],
        "module_1_rules": [
            {"id": r[0], "name": r[1], "source": r[2], "weight": r[3]} for r in RULES
        ],
        "module_1_name": MODULE_NAME,
    }
