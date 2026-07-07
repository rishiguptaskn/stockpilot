"""Best-effort persistence of agent runs to Supabase ``agent_runs``.

Writes need the service_role key (the table is under RLS). When credentials are
absent — local dev, tests — persistence is skipped and a locally-generated run id
is returned, so the feature never blocks on infra. This mirrors the existing
``run_workflow`` policy of not requiring service_role for the core path.
"""

from __future__ import annotations

import logging
import os
import uuid

from stockpilot_api.agents.base import RunStats
from stockpilot_api.agents.schemas import ResearchReport

logger = logging.getLogger(__name__)


def _service_client():
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not create Supabase service client: %s", exc)
        return None


def record_runs(
    *,
    user_id: str | None,
    ticker: str,
    report: ResearchReport,
    stats: list[RunStats],
    status: str = "succeeded",
) -> str:
    """Persist one master row + one row per specialist. Returns the master run id.

    ``stats`` is ordered [specialists..., master]; the master is last.
    """
    master_run_id = str(uuid.uuid4())
    client = _service_client()
    if client is None:
        logger.info("Skipping agent_runs persistence (no service_role creds)")
        return master_run_id

    master_stats = stats[-1] if stats else None
    findings_by_agent = {f.agent_name: f.model_dump(mode="json") for f in report.findings}
    rows: list[dict] = []

    if master_stats is not None:
        rows.append(
            {
                "id": master_run_id,
                "user_id": user_id,
                "ticker": ticker,
                "agent_name": master_stats.agent_name,
                "parent_run_id": None,
                "status": status,
                "model": master_stats.model,
                "input": {"ticker": ticker},
                "output": report.model_dump(mode="json"),
                "tool_calls": master_stats.tool_calls,
                "input_tokens": master_stats.input_tokens,
                "output_tokens": master_stats.output_tokens,
                "cost_usd": master_stats.cost_usd,
            }
        )

    for s in stats[:-1]:
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "ticker": ticker,
                "agent_name": s.agent_name,
                "parent_run_id": master_run_id,
                "status": status,
                "model": s.model,
                "input": {"ticker": ticker},
                "output": findings_by_agent.get(s.agent_name),
                "tool_calls": s.tool_calls,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "cost_usd": s.cost_usd,
            }
        )

    try:
        client.table("agent_runs").insert(rows).execute()
    except Exception as exc:  # noqa: BLE001 — persistence failure must not fail the request
        logger.warning("Failed to persist agent_runs: %s", exc)

    return master_run_id
