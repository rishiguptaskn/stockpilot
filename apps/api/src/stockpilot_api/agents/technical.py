"""Technical Analysis Agent — the first domain agent (vertical slice).

Runs a Claude tool-use loop against the Technical MCP registry and returns a
schema-validated ``AgentFinding``. All reasoning is grounded in tool output.
"""

from __future__ import annotations

from pathlib import Path

from stockpilot_api.agents.base import AgentResult, BaseAgent, EventHook
from stockpilot_api.agents.schemas import AgentFinding
from stockpilot_api.llm.client import LLMTransport
from stockpilot_api.llm.config import LLMConfig
from stockpilot_api.mcp.registry import TECHNICAL_REGISTRY

_PROMPT = (Path(__file__).parent / "prompts" / "technical.md").read_text(encoding="utf-8")

AGENT_NAME = "technical"


class TechnicalAnalysisAgent:
    """Thin wrapper binding the technical prompt + MCP registry to BaseAgent."""

    def __init__(
        self,
        *,
        transport: LLMTransport,
        config: LLMConfig,
        on_event: EventHook | None = None,
    ) -> None:
        self._agent = BaseAgent(
            name=AGENT_NAME,
            model=config.sub_agent_model,
            system_prompt=_PROMPT,
            output_model=AgentFinding,
            transport=transport,
            config=config,
            registry=TECHNICAL_REGISTRY,
            on_event=on_event,
            submit_tool_name="submit_finding",
            submit_tool_description=(
                "Submit your final technical finding for the ticker. Call exactly once."
            ),
        )

    def analyze(self, ticker: str) -> AgentResult:
        task = (
            f"Analyze {ticker} from a pure technical perspective. Gather evidence with the "
            f"tools (moving averages M5, momentum M6, volume M7, patterns, and price action), "
            f"then submit your finding. Set agent_name to '{AGENT_NAME}'."
        )
        result = self._agent.run(task)
        # Guarantee the agent_name is authoritative regardless of what the model set.
        finding: AgentFinding = result.output  # type: ignore[assignment]
        if finding.agent_name != AGENT_NAME:
            result.output = finding.model_copy(update={"agent_name": AGENT_NAME})
        return result
