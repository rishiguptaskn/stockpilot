"""/backtest router — async backtest jobs (runs take minutes; ARCHITECTURE.md §5).

POST /backtest/run          -> {run_id}   (starts a worker thread)
GET  /backtest/runs/{id}    -> {status, progress, report?}
GET  /backtest/runs         -> recent runs (id, status, config)

v1: in-memory job store (single user, local host). Persisting to Supabase
`backtest_runs` is the production step once service-role wiring lands.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from stockpilot_api.backtest.config import BacktestConfig
from stockpilot_api.backtest.run import run as run_backtest_full

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])

_RUNS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_MAX_CONCURRENT = 1  # scoring is CPU/network heavy — serialize v1 runs


class BacktestRunInput(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=50)
    period: str = Field(default="2y", pattern=r"^(1|2|3|5|10)y$")
    min_score: float = Field(default=85.0, ge=50, le=100)
    capital_inr: float = Field(default=500_000.0, gt=0)
    require_pattern: bool = True  # best variant in BACKTEST_FINDINGS round 3


def _worker(run_id: str, payload: BacktestRunInput) -> None:
    def progress(phase: str, done: int, total: int) -> None:
        with _LOCK:
            _RUNS[run_id]["progress"] = {"phase": phase, "done": done, "total": total}

    try:
        cfg = replace(
            BacktestConfig(), min_score=payload.min_score, capital_inr=payload.capital_inr
        )
        _, report = run_backtest_full(
            payload.tickers,
            payload.period,
            cfg,
            require_pattern=payload.require_pattern,
            progress_cb=progress,
        )
        with _LOCK:
            _RUNS[run_id].update(
                status="done",
                report=report,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
    except Exception as exc:  # noqa: BLE001 — job errors surface via status
        logger.exception("backtest run %s failed", run_id)
        with _LOCK:
            _RUNS[run_id].update(
                status="failed",
                error=str(exc),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )


@router.post("/run")
def start_run(payload: BacktestRunInput) -> dict[str, Any]:
    with _LOCK:
        active = sum(1 for r in _RUNS.values() if r["status"] == "running")
        if active >= _MAX_CONCURRENT:
            raise HTTPException(
                status_code=429,
                detail="A backtest is already running — wait for it to finish (v1 runs one at a time).",
            )
        run_id = uuid.uuid4().hex[:12]
        _RUNS[run_id] = {
            "run_id": run_id,
            "status": "running",
            "progress": {"phase": "queued", "done": 0, "total": 1},
            "config": payload.model_dump(),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    threading.Thread(target=_worker, args=(run_id, payload), daemon=True).start()
    return {"run_id": run_id, "status": "running"}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with _LOCK:
        run = _RUNS.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown run {run_id}")
        return dict(run)


@router.get("/runs")
def list_runs() -> list[dict[str, Any]]:
    with _LOCK:
        return [
            {k: v for k, v in r.items() if k != "report"}
            for r in sorted(_RUNS.values(), key=lambda r: r["started_at"], reverse=True)
        ][:20]
