"""LLM configuration — model IDs, pricing, and runtime caps.

Single source of truth for which Claude models the agent layer uses, how much
they cost (for the ``agent_runs`` cost column), and the guardrails that stop a
runaway tool-use loop. All values are overridable via environment variables so
deployments can tune cost/latency without a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# --- Model IDs (latest capable Claude models as of this build) --------------
SONNET = "claude-sonnet-5"
OPUS = "claude-opus-4-8"
HAIKU = "claude-haiku-4-5-20251001"

# --- Pricing: USD per 1M tokens as (input, output) --------------------------
# Used only to populate agent_runs.cost_usd for observability. Keep in sync
# with the pricing page; a wrong number here never affects behaviour.
PRICING: dict[str, tuple[float, float]] = {
    SONNET: (3.0, 15.0),
    OPUS: (15.0, 75.0),
    HAIKU: (1.0, 5.0),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for a completed call. Unknown models cost 0 (logged)."""
    inp, out = PRICING.get(model, (0.0, 0.0))
    return round(input_tokens / 1_000_000 * inp + output_tokens / 1_000_000 * out, 6)


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class LLMConfig:
    """Runtime configuration for the agent layer.

    ``sub_agent_model`` runs the per-domain agents (fast, cheap); ``master_model``
    runs the final synthesis where cross-agent reasoning matters. Set
    ``STOCKPILOT_SONNET_ONLY=1`` to run everything on Sonnet and roughly halve
    per-report cost.
    """

    sub_agent_model: str = SONNET
    master_model: str = OPUS
    temperature: float = 0.0  # deterministic extraction — no creative drift
    max_tokens: int = 4096
    max_tool_iterations: int = 8  # hard cap on tool-use rounds per agent
    max_total_tokens_per_run: int = 60_000  # budget guard across all iterations
    request_timeout_s: float = 60.0
    max_retries: int = 4

    @property
    def api_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def openai_api_key(self) -> str | None:
        return os.environ.get("OPENAI_API_KEY")

    @classmethod
    def from_env(cls) -> LLMConfig:
        sonnet_only = _env_bool("STOCKPILOT_SONNET_ONLY")
        return cls(
            sub_agent_model=os.environ.get("STOCKPILOT_SUB_AGENT_MODEL", SONNET),
            master_model=(
                SONNET if sonnet_only else os.environ.get("STOCKPILOT_MASTER_MODEL", OPUS)
            ),
            max_tool_iterations=int(os.environ.get("STOCKPILOT_MAX_TOOL_ITERS", "8")),
            max_total_tokens_per_run=int(
                os.environ.get("STOCKPILOT_MAX_RUN_TOKENS", "60000")
            ),
        )
