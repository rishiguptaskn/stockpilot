"""Master Trading Agent — orchestrates specialists and synthesizes the report.

This milestone has one specialist (Technical). The Master (1) runs the specialist
agents, (2) makes a single synthesis LLM call that composes their findings into a
narrative WITHOUT introducing new numbers, and (3) assembles the final
``ResearchReport`` — attaching ticker, dates, and the server-owned disclaimer.

When more agents ship, only ``_run_specialists`` changes (fan-out in parallel);
the synthesis + assembly stay the same. Open/Closed by construction.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from stockpilot_api.agents.base import BaseAgent, EventHook, RunStats
from stockpilot_api.agents.schemas import (
    DISCLAIMER,
    AgentFinding,
    ResearchReport,
    Stance,
)
from stockpilot_api.agents.technical import TechnicalAnalysisAgent
from stockpilot_api.llm.client import LLMTransport
from stockpilot_api.llm.config import LLMConfig

logger = logging.getLogger(__name__)

_PROMPT = (Path(__file__).parent / "prompts" / "master.md").read_text(encoding="utf-8")

AGENT_NAME = "master"


class MasterSynthesis(BaseModel):
    """What the Master LLM produces — narrative + stance only, no new data."""

    overall_stance: Literal["bullish", "neutral", "bearish"]
    confidence: float = Field(ge=0, le=1)
    master_synthesis: str
    uncertainties: list[str] = Field(default_factory=list)


class MasterAgent:
    def __init__(
        self,
        *,
        transport: LLMTransport,
        config: LLMConfig,
        on_event: EventHook | None = None,
    ) -> None:
        self._transport = transport
        self._config = config
        self._on_event = on_event

    def _run_specialists(self, ticker: str) -> tuple[list[AgentFinding], list[RunStats]]:
        """Run every domain agent. Milestone 1: Technical only (sequential)."""
        findings: list[AgentFinding] = []
        stats: list[RunStats] = []
        technical = TechnicalAnalysisAgent(
            transport=self._transport, config=self._config, on_event=self._on_event
        )
        result = technical.analyze(ticker)
        findings.append(result.output)  # type: ignore[arg-type]
        stats.append(result.stats)
        return findings, stats

    def _synthesize(self, ticker: str, findings: list[AgentFinding]) -> tuple[MasterSynthesis, RunStats]:
        agent = BaseAgent(
            name=AGENT_NAME,
            model=self._config.master_model,
            system_prompt=_PROMPT,
            output_model=MasterSynthesis,
            transport=self._transport,
            config=self._config,
            registry=None,  # synthesis uses no data tools — it only composes findings
            on_event=self._on_event,
            submit_tool_name="submit_report",
            submit_tool_description="Submit your final synthesis. Call exactly once.",
        )
        findings_json = "\n\n".join(f.model_dump_json(indent=2) for f in findings)
        task = (
            f"Ticker: {ticker}\n\n"
            f"Specialist findings to synthesize (do NOT introduce new numbers):\n\n"
            f"{findings_json}"
        )
        result = agent.run(task)
        return result.output, result.stats  # type: ignore[return-value]

    def analyze(
        self, ticker: str, *, as_of: date | None = None
    ) -> tuple[ResearchReport, list[RunStats]]:
        """Produce the full research report and return it with per-agent run stats."""
        self._emit({"agent": AGENT_NAME, "type": "agent_started"})
        findings, specialist_stats = self._run_specialists(ticker)
        synthesis, master_stats = self._synthesize(ticker, findings)

        report = ResearchReport(
            ticker=ticker,
            as_of=as_of or date.today(),
            overall_stance=_clamp_stance(synthesis.overall_stance, findings),
            confidence=synthesis.confidence,
            master_synthesis=synthesis.master_synthesis,
            findings=findings,
            uncertainties=synthesis.uncertainties,
            disclaimer=DISCLAIMER,  # server-owned, never model-generated
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._emit({"agent": AGENT_NAME, "type": "report", "report": report.model_dump(mode="json")})
        return report, [*specialist_stats, master_stats]

    def _emit(self, event: dict) -> None:
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:  # noqa: BLE001
                logger.debug("event hook raised", exc_info=True)


def _clamp_stance(stance: Stance, findings: list[AgentFinding]) -> Stance:
    """Safety rail: if every specialist reported no data, force neutral."""
    if findings and all(not f.data_available for f in findings):
        return "neutral"
    return stance
