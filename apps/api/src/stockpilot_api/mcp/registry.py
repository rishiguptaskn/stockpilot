"""In-process MCP tool registry.

The agent runtime calls tools *in-process* through this registry — no subprocess,
no IPC — so the analysis hot path has zero transport overhead. The very same
tool functions are also exposed over the standard MCP stdio protocol by
``technical_server.py`` for external/standard clients (Claude Desktop, etc.).

A ``ToolRegistry`` gives the agent two things:
  * ``anthropic_tools()`` — the tool schemas to pass to the Messages API, and
  * ``call(name, args)`` — synchronous execution returning a JSON-able dict.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from stockpilot_api.mcp.technical_tools import TOOL_SPECS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., dict[str, Any]]


class ToolRegistry:
    """A named collection of read-only tools an agent is allowed to call."""

    def __init__(self, name: str, tools: list[Tool]) -> None:
        self.name = name
        self._tools: dict[str, Tool] = {t.name: t for t in tools}

    def anthropic_tools(self) -> list[dict[str, Any]]:
        """Tool definitions in the shape the Anthropic Messages API expects."""
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self._tools.values()
        ]

    def names(self) -> list[str]:
        return list(self._tools)

    def has(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool. Never raises to the caller — errors become tool output.

        A failed tool must not crash the agent loop; the model needs to *see* the
        failure (as data) so it can degrade to 'data unavailable' rather than guess.
        """
        tool = self._tools.get(name)
        if tool is None:
            return {"data_available": False, "error": f"unknown tool {name!r}"}
        try:
            return tool.fn(**args)
        except Exception as exc:  # noqa: BLE001 — surface as data, never propagate
            logger.warning("Tool %s failed: %s", name, exc)
            return {"data_available": False, "error": f"{type(exc).__name__}: {exc}"}


def _build_technical_registry() -> ToolRegistry:
    tools = [
        Tool(
            name=spec["name"],
            description=spec["description"],
            input_schema=spec["input_schema"],
            fn=spec["fn"],
        )
        for spec in TOOL_SPECS
    ]
    return ToolRegistry("technical", tools)


# Singleton for the technical domain (this milestone's only registry).
TECHNICAL_REGISTRY = _build_technical_registry()
