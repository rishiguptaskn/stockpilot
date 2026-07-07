"""BaseAgent — the Claude tool-use loop shared by every domain agent.

Responsibilities (Single Responsibility + Open/Closed): drive a bounded tool-use
conversation against an MCP ``ToolRegistry``, force a schema-validated final
answer via a terminal "submit" tool, capture tokens/cost/tool-calls, and emit
progress events. Concrete agents (Technical, Master) only supply a name, model,
system prompt, tool registry, and output schema — no loop logic is duplicated.

The forced-submit pattern is how we get reliable structured output: the model's
only way to finish is to call the submit tool, whose input schema IS the Pydantic
output model. Malformed output is rejected and retried, not silently trusted.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from stockpilot_api.llm.client import LLMTransport
from stockpilot_api.llm.config import LLMConfig, cost_usd
from stockpilot_api.mcp.registry import ToolRegistry

logger = logging.getLogger(__name__)

EventHook = Callable[[dict[str, Any]], None]


@dataclass
class RunStats:
    agent_name: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    iterations: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        return cost_usd(self.model, self.input_tokens, self.output_tokens)


@dataclass
class AgentResult:
    output: BaseModel
    stats: RunStats


class AgentError(RuntimeError):
    """Raised when the agent cannot produce a valid output within its budget."""


class BaseAgent:
    def __init__(
        self,
        *,
        name: str,
        model: str,
        system_prompt: str,
        output_model: type[BaseModel],
        transport: LLMTransport,
        config: LLMConfig,
        registry: ToolRegistry | None = None,
        on_event: EventHook | None = None,
        submit_tool_name: str = "submit",
        submit_tool_description: str = "Submit your final structured answer. Call this exactly once.",
    ) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.output_model = output_model
        self._transport = transport
        self._config = config
        self._registry = registry
        self._on_event = on_event
        self._submit_name = submit_tool_name
        self._submit_desc = submit_tool_description

    # -- events --------------------------------------------------------------
    def _emit(self, event: dict[str, Any]) -> None:
        if self._on_event is not None:
            try:
                self._on_event({"agent": self.name, **event})
            except Exception:  # noqa: BLE001 — a broken listener must not fail the run
                logger.debug("event hook raised", exc_info=True)

    # -- tool definitions ----------------------------------------------------
    def _all_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        if self._registry is not None:
            tools.extend(self._registry.anthropic_tools())
        tools.append(
            {
                "name": self._submit_name,
                "description": self._submit_desc,
                "input_schema": self.output_model.model_json_schema(),
            }
        )
        return tools

    # -- main loop -----------------------------------------------------------
    def run(self, task: str) -> AgentResult:
        stats = RunStats(agent_name=self.name, model=self.model)
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        tools = self._all_tools()
        self._emit({"type": "agent_started"})

        max_iter = self._config.max_tool_iterations
        for i in range(max_iter):
            stats.iterations = i + 1
            over_budget = (
                stats.input_tokens + stats.output_tokens
            ) >= self._config.max_total_tokens_per_run
            force_submit = i == max_iter - 1 or over_budget
            tool_choice = (
                {"type": "tool", "name": self._submit_name}
                if force_submit
                else {"type": "auto"}
            )

            resp = self._transport.create(
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                tool_choice=tool_choice,
            )
            stats.input_tokens += resp.usage.input_tokens
            stats.output_tokens += resp.usage.output_tokens
            messages.append({"role": "assistant", "content": resp.raw_content})

            submit = next((t for t in resp.tool_uses if t.name == self._submit_name), None)
            if submit is not None:
                try:
                    output = self.output_model.model_validate(submit.input)
                    self._emit({"type": "agent_finding", "finding": output.model_dump(mode="json")})
                    return AgentResult(output=output, stats=stats)
                except ValidationError as exc:
                    if force_submit:
                        raise AgentError(
                            f"{self.name}: final output failed validation: {exc}"
                        ) from exc
                    # One repair round: tell the model exactly what was wrong.
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": submit.id,
                                    "is_error": True,
                                    "content": f"Output invalid, fix and resubmit: {exc}",
                                }
                            ],
                        }
                    )
                    continue

            data_calls = [t for t in resp.tool_uses if t.name != self._submit_name]
            if data_calls:
                tool_results = []
                for call in data_calls:
                    result = (
                        self._registry.call(call.name, call.input)
                        if self._registry is not None
                        else {"data_available": False, "error": "no tools available"}
                    )
                    stats.tool_calls.append({"tool": call.name, "args": call.input})
                    self._emit({"type": "tool_call", "tool": call.name, "args": call.input})
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                messages.append({"role": "user", "content": tool_results})
                continue

            # Model produced text without any tool call — nudge it to submit.
            messages.append(
                {
                    "role": "user",
                    "content": f"Now call `{self._submit_name}` with your final answer.",
                }
            )

        raise AgentError(f"{self.name}: exhausted {max_iter} iterations without valid output")
