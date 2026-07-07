"""MCP layer — read-only tool servers wrapping the deterministic rule engine.

Each domain (technical, and later market/news/fundamental/risk/portfolio/journal/
backtesting) is exposed twice from one implementation:
  * in-process via ``registry.ToolRegistry`` (agent hot path, zero transport cost)
  * over standard MCP stdio via ``*_server.py`` (external clients)
"""

from stockpilot_api.mcp.registry import TECHNICAL_REGISTRY, Tool, ToolRegistry

__all__ = ["ToolRegistry", "Tool", "TECHNICAL_REGISTRY"]
