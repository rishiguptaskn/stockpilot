"""OpenAI transport — implements the same ``LLMTransport`` protocol as Anthropic.

The agent layer speaks one internal dialect: Anthropic-style message blocks
(``text`` / ``tool_use`` / ``tool_result``). This transport translates that
dialect to the OpenAI Chat Completions format on the way out and back to the
internal dialect on the way in, so ``BaseAgent`` works unchanged on either
provider.

Model IDs are configuration (env vars) — nothing here hardcodes a specific
OpenAI model.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from stockpilot_api.llm.client import LLMResponse, ToolUse, Usage

logger = logging.getLogger(__name__)


def _to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate internal (Anthropic-block) messages to OpenAI chat format."""
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for msg in messages:
        role, content = msg["role"], msg["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []
            for block in content:
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block.get("input", {})),
                            },
                        }
                    )
            entry: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts) or None}
            if tool_calls:
                entry["tool_calls"] = tool_calls
            out.append(entry)
        else:  # user turn carrying tool_result blocks (and/or text)
            for block in content:
                btype = block.get("type")
                if btype == "tool_result":
                    raw = block.get("content", "")
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": raw if isinstance(raw, str) else json.dumps(raw),
                        }
                    )
                elif btype == "text":
                    out.append({"role": "user", "content": block.get("text", "")})
    return out


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def _to_openai_tool_choice(tool_choice: dict[str, Any] | None) -> Any:
    if tool_choice is None:
        return None
    if tool_choice.get("type") == "tool":
        return {"type": "function", "function": {"name": tool_choice["name"]}}
    return "auto"


class OpenAITransport:
    """Production OpenAI transport with retry + normalisation to ``LLMResponse``."""

    _RETRY_STATUS = {429, 500, 502, 503}

    def __init__(self, *, api_key: str | None, timeout_s: float, max_retries: int) -> None:
        import openai  # lazy: keeps import-time cost out of tests

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it in the API environment only — "
                "never expose it to the browser."
            )
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout_s)
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
        import openai

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _to_openai_messages(system, messages),
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = _to_openai_tools(tools)
        choice = _to_openai_tool_choice(tool_choice)
        if choice is not None:
            kwargs["tool_choice"] = choice

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.chat.completions.create(**kwargs)
                return self._normalise(resp)
            except openai.APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status not in self._RETRY_STATUS or attempt == self._max_retries:
                    raise
                last_exc = exc
            except openai.APIConnectionError as exc:
                if attempt == self._max_retries:
                    raise
                last_exc = exc
            backoff = min(2**attempt, 16)
            logger.warning(
                "OpenAI call failed (attempt %d/%d): %s — retrying in %ds",
                attempt + 1,
                self._max_retries + 1,
                last_exc,
                backoff,
            )
            time.sleep(backoff)
        raise RuntimeError("unreachable")  # pragma: no cover

    @staticmethod
    def _normalise(resp: Any) -> LLMResponse:
        msg = resp.choices[0].message
        text = msg.content or ""
        raw_content: list[dict[str, Any]] = []
        if text:
            raw_content.append({"type": "text", "text": text})

        tool_uses: list[ToolUse] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                logger.warning("OpenAI returned non-JSON tool arguments for %s", tc.function.name)
                args = {}
            tool_uses.append(ToolUse(id=tc.id, name=tc.function.name, input=args))
            raw_content.append(
                {"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": args}
            )

        finish = resp.choices[0].finish_reason or ""
        stop_reason = {"tool_calls": "tool_use", "stop": "end_turn", "length": "max_tokens"}.get(
            finish, finish
        )
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            stop_reason=stop_reason,
            text=text,
            tool_uses=tool_uses,
            usage=Usage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            raw_content=raw_content,
        )
