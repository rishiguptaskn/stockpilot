"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockpilot_api import __version__
from stockpilot_api.engine.module_1_market import RULES as M1_RULES
from stockpilot_api.engine.module_5_moving_averages import RULES as M5_RULES
from stockpilot_api.engine.module_9_risk import RULES as M9_RULES

app = FastAPI(
    title="StockPilot API",
    version=__version__,
    description="Rule engine + indicators + pattern detectors + scoring + ingestion. See docs/RULEBOOK.md.",
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/info")
def info() -> dict[str, object]:
    """Metadata about what the engine currently implements."""
    return {
        "name": "StockPilot API",
        "version": __version__,
        "modules_implemented": ["M1", "M5", "M9"],
        "modules_planned": ["M2", "M3", "M4", "M6", "M7", "M8", "M10"],
        "patterns_implemented": ["VCP", "Stage 2 Breakout"],
        "patterns_planned": [
            "Cup & Handle",
            "Flat Base",
            "Bull Flag",
            "Darvas Box",
            "Ascending Triangle",
            "EMA Pullback",
        ],
        "total_rules_implemented": len(M1_RULES) + len(M5_RULES) + len(M9_RULES),
        "total_rules_target": 206,
        "modules": {
            "M1": [{"id": r[0], "name": r[1], "source": r[2], "weight": r[3]} for r in M1_RULES],
            "M5": [{"id": r[0], "name": r[1], "source": r[2], "weight": r[3]} for r in M5_RULES],
            "M9": [{"id": r[0], "name": r[1], "source": r[2], "weight": r[3]} for r in M9_RULES],
        },
    }
