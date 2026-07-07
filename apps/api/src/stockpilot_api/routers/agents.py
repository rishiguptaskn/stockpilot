"""/agents router — AI research reports over the deterministic engine.

  POST /agents/analyze          -> full ResearchReport (JSON)
  GET  /agents/analyze/stream   -> Server-Sent Events (live agent trace + report)

The Anthropic key lives only in this process; the browser never sees it. The
report's numbers all originate from MCP tools, and a server-owned disclaimer is
attached to every response.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from stockpilot_api.agents.master import MasterAgent
from stockpilot_api.agents.persistence import record_runs
from stockpilot_api.auth import optional_user_id
from stockpilot_api.llm.client import AnthropicTransport
from stockpilot_api.llm.config import LLMConfig
from stockpilot_api.mcp.data_access import clear_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


class AnalyzeRequest(BaseModel):
    ticker: str
    force_refresh: bool = False

    @field_validator("ticker")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("ticker is required")
        return v if "." in v else f"{v}.NS"


def _build_agent(on_event=None) -> MasterAgent:
    config = LLMConfig.from_env()
    try:
        transport = AnthropicTransport(
            api_key=config.api_key,
            timeout_s=config.request_timeout_s,
            max_retries=config.max_retries,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return MasterAgent(transport=transport, config=config, on_event=on_event)


def _run(ticker: str, user_id: str | None, on_event=None) -> tuple[dict[str, Any], str]:
    master = _build_agent(on_event=on_event)
    report, stats = master.analyze(ticker, as_of=date.today())
    run_id = record_runs(user_id=user_id, ticker=ticker, report=report, stats=stats)
    payload = report.model_dump(mode="json")
    payload["run_id"] = run_id
    payload["cost_usd"] = round(sum(s.cost_usd for s in stats), 6)
    return payload, run_id


@router.post("/analyze")
def analyze(
    req: AnalyzeRequest,
    user_id: str | None = Depends(optional_user_id),
) -> dict[str, Any]:
    if req.force_refresh:
        clear_cache()
    try:
        payload, _ = _run(req.ticker, user_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    return payload


@router.get("/analyze/stream")
def analyze_stream(
    ticker: str,
    force_refresh: bool = False,
    user_id: str | None = Depends(optional_user_id),
) -> StreamingResponse:
    req = AnalyzeRequest(ticker=ticker, force_refresh=force_refresh)
    if req.force_refresh:
        clear_cache()

    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def worker() -> None:
        try:
            payload, _ = _run(req.ticker, user_id, on_event=events.put)
            events.put({"type": "done", "report": payload})
        except HTTPException as exc:
            events.put({"type": "error", "detail": exc.detail})
        except Exception as exc:  # noqa: BLE001
            logger.exception("stream analyze failed for %s", req.ticker)
            events.put({"type": "error", "detail": f"Analysis failed: {exc}"})
        finally:
            events.put(None)  # sentinel

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        while True:
            event = events.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
