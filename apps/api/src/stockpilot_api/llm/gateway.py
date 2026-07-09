"""LLM Gateway — routes each call to the right provider by model ID.

ARCHITECTURE.md §7.3: model IDs are configuration, not code. ``claude-*`` IDs
go to Anthropic; ``gpt-*`` / ``o*`` IDs go to OpenAI. Missing API keys fail
loudly at call time with an actionable message — never silently.
"""

from __future__ import annotations

import logging
from typing import Any

from stockpilot_api.llm.client import LLMResponse, LLMTransport
from stockpilot_api.llm.config import LLMConfig

logger = logging.getLogger(__name__)


class RoutingTransport:
    """Delegates ``create()`` to a provider transport based on the model ID prefix."""

    def __init__(
        self,
        *,
        anthropic: LLMTransport | None,
        openai: LLMTransport | None,
    ) -> None:
        self._anthropic = anthropic
        self._openai = openai

    def _route(self, model: str) -> LLMTransport:
        if model.startswith("claude"):
            if self._anthropic is None:
                raise RuntimeError(
                    f"Model '{model}' requires ANTHROPIC_API_KEY, which is not set."
                )
            return self._anthropic
        if model.startswith(("gpt", "o1", "o3", "o4")):
            if self._openai is None:
                raise RuntimeError(f"Model '{model}' requires OPENAI_API_KEY, which is not set.")
            return self._openai
        raise RuntimeError(
            f"Unknown model family for '{model}'. Expected a 'claude-*' or 'gpt-*'/'o*' ID."
        )

    def create(self, *, model: str, **kwargs: Any) -> LLMResponse:
        return self._route(model).create(model=model, **kwargs)


def build_transport(config: LLMConfig) -> RoutingTransport:
    """Construct the gateway with whichever providers have keys configured.

    Raises if NO provider is configured — the agent layer cannot run keyless.
    """
    anthropic_transport: LLMTransport | None = None
    openai_transport: LLMTransport | None = None

    if config.api_key:
        from stockpilot_api.llm.client import AnthropicTransport

        anthropic_transport = AnthropicTransport(
            api_key=config.api_key,
            timeout_s=config.request_timeout_s,
            max_retries=config.max_retries,
        )
    if config.openai_api_key:
        from stockpilot_api.llm.openai_transport import OpenAITransport

        openai_transport = OpenAITransport(
            api_key=config.openai_api_key,
            timeout_s=config.request_timeout_s,
            max_retries=config.max_retries,
        )

    if anthropic_transport is None and openai_transport is None:
        raise RuntimeError(
            "No LLM provider configured. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY."
        )
    return RoutingTransport(anthropic=anthropic_transport, openai=openai_transport)
