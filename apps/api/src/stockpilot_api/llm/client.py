"""Anthropic transport wrapper.

The agent layer never touches the ``anthropic`` SDK directly. It talks to an
``LLMTransport`` — a tiny interface with one method, ``create()`` — so that:

  * unit tests inject a ``FakeTransport`` with a scripted tool-use transcript
    (no network, no API key, deterministic), and
  * the real ``AnthropicTransport`` owns retries, timeouts, and token capture.

Responses are normalised into plain dataclasses (``LLMResponse``) so nothing
downstream depends on SDK types. We keep ``raw_content`` (the assistant blocks
verbatim) so the agent can append the exact turn back onto the message list,
which the Messages API requires for multi-turn tool use.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    stop_reason: str
    text: str
    tool_uses: list[ToolUse]
    usage: Usage
    raw_content: list[dict[str, Any]] = field(default_factory=list)


class LLMTransport(Protocol):
    """The seam every agent depends on. Implemented by the real SDK and by tests."""

    def create(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        tool_choice: dict[str, Any] | None = None,
    ) -> LLMResponse: ...


class AnthropicTransport:
    """Production transport. Wraps ``anthropic.Anthropic`` with retry + normalisation."""

    # Retryable API failures (imported lazily so tests need no SDK/key).
    _RETRY_STATUS = {429, 500, 502, 503, 529}

    def __init__(self, *, api_key: str | None, timeout_s: float, max_retries: int) -> None:
        import anthropic  # lazy: keeps import-time cost out of tests

        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. The agent layer requires it. "
                "Set it in the API environment only — never expose it to the browser."
            )
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s)
        self._max_retries = max_retries

    def create(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        tool_choice: dict[str, Any] | None = None,
    ) -> LLMResponse:
        import anthropic

        kwargs: dict[str, Any] = {
            "model": model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.messages.create(**kwargs)
                return self._normalise(resp)
            except anthropic.APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status not in self._RETRY_STATUS or attempt == self._max_retries:
                    raise
                last_exc = exc
            except anthropic.APIConnectionError as exc:
                if attempt == self._max_retries:
                    raise
                last_exc = exc
            backoff = min(2**attempt, 16)
            logger.warning(
                "Anthropic call failed (attempt %d/%d): %s — retrying in %ds",
                attempt + 1,
                self._max_retries + 1,
                last_exc,
                backoff,
            )
            time.sleep(backoff)
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def _normalise(resp: Any) -> LLMResponse:
        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        raw_content: list[dict[str, Any]] = []
        for block in resp.content:
            raw_content.append(block.model_dump())
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(ToolUse(id=block.id, name=block.name, input=dict(block.input)))
        return LLMResponse(
            stop_reason=resp.stop_reason or "",
            text="".join(text_parts),
            tool_uses=tool_uses,
            usage=Usage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            raw_content=raw_content,
        )
