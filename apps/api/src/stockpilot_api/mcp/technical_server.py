"""Standalone Technical MCP server (stdio transport).

Exposes the exact same tool functions the in-process registry uses, but over the
standard Model Context Protocol so any MCP client (Claude Desktop, external
agents) can consume them.

    python -m stockpilot_api.mcp.technical_server

This is the "standards-compliant" face of the technical tools; the agent runtime
does NOT go through here on the hot path (it uses registry.py in-process).
"""

from __future__ import annotations

import json

from stockpilot_api.mcp.registry import TECHNICAL_REGISTRY


def build_server():  # pragma: no cover - thin protocol wiring
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("stockpilot-technical")

    def _register(tool_name: str) -> None:
        tool = TECHNICAL_REGISTRY  # closure over the shared registry

        @server.tool(name=tool_name)
        def _handler(**kwargs) -> str:  # MCP tools return text; we JSON-encode
            return json.dumps(tool.call(tool_name, kwargs))

        _handler.__doc__ = next(
            (t["description"] for t in TECHNICAL_REGISTRY.anthropic_tools() if t["name"] == tool_name),
            tool_name,
        )

    for name in TECHNICAL_REGISTRY.names():
        _register(name)

    return server


def main() -> None:  # pragma: no cover
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    main()
