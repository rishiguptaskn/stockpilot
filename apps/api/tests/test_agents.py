"""Agent-layer tests — MCP tools, cost math, structured-output loop, orchestration.

All LLM calls go through a scripted FakeTransport: no network, no API key,
fully deterministic. Market data is seeded into the data-access cache so tools
never hit yfinance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import stockpilot_api.mcp.data_access as data_access
from stockpilot_api.agents.base import AgentError, BaseAgent
from stockpilot_api.agents.master import MasterAgent, MasterSynthesis
from stockpilot_api.agents.schemas import AgentFinding, ResearchReport
from stockpilot_api.agents.technical import TechnicalAnalysisAgent
from stockpilot_api.llm.client import LLMResponse, ToolUse, Usage
from stockpilot_api.llm.config import LLMConfig, cost_usd
from stockpilot_api.mcp.registry import TECHNICAL_REGISTRY

TEST_TICKER = "TEST.NS"


# --- fixtures ---------------------------------------------------------------
def _synthetic_daily(n: int = 320) -> pd.DataFrame:
    """A clean uptrend so the engine has real, non-degenerate values."""
    idx = pd.bdate_range(end="2026-07-01", periods=n)
    trend = np.linspace(100.0, 300.0, n)
    noise = np.sin(np.linspace(0, 40, n)) * 3.0
    close = trend + noise
    high = close * 1.01
    low = close * 0.99
    open_ = close * 0.995
    volume = np.linspace(1_000_000, 2_000_000, n).astype(int)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


@pytest.fixture(autouse=True)
def _seed_cache():
    data_access.clear_cache()
    data_access._CACHE[TEST_TICKER] = _synthetic_daily()
    yield
    data_access.clear_cache()


class FakeTransport:
    """Pops pre-scripted LLMResponses in order; records the calls it received."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> LLMResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeTransport ran out of scripted responses")
        return self._responses.pop(0)


def _tool_use_response(name: str, inp: dict, *, in_tok=100, out_tok=50) -> LLMResponse:
    return LLMResponse(
        stop_reason="tool_use",
        text="",
        tool_uses=[ToolUse(id=f"tu_{name}", name=name, input=inp)],
        usage=Usage(input_tokens=in_tok, output_tokens=out_tok),
        raw_content=[{"type": "tool_use", "id": f"tu_{name}", "name": name, "input": inp}],
    )


# --- MCP tool tests ---------------------------------------------------------
def test_get_indicators_shape():
    out = TECHNICAL_REGISTRY.call("get_indicators", {"ticker": TEST_TICKER})
    assert out["data_available"] is True
    assert out["close"] > 0
    assert out["sma_200"] is not None
    assert out["rsi_14"] is not None


def test_get_module_score_m5_is_real_and_cited():
    out = TECHNICAL_REGISTRY.call("get_module_score", {"ticker": TEST_TICKER, "module": "M5"})
    assert out["data_available"] is True
    assert out["module_id"] == "M5"
    assert 0 <= out["score"] <= 100
    assert len(out["rule_evaluations"]) > 0
    # placeholder must be surfaced honestly
    assert any("placeholder" in n.lower() for n in out["notes"])


def test_get_module_score_rejects_unknown_module():
    out = TECHNICAL_REGISTRY.call("get_module_score", {"ticker": TEST_TICKER, "module": "M99"})
    assert out["data_available"] is False


def test_tool_unavailable_when_no_history():
    data_access._CACHE["EMPTY.NS"] = pd.DataFrame()
    out = TECHNICAL_REGISTRY.call("get_indicators", {"ticker": "EMPTY.NS"})
    assert out["data_available"] is False


def test_registry_unknown_tool_is_data_not_exception():
    out = TECHNICAL_REGISTRY.call("does_not_exist", {})
    assert out["data_available"] is False
    assert "unknown tool" in out["error"]


# --- cost math --------------------------------------------------------------
def test_cost_math():
    # Sonnet: $3/1M in, $15/1M out
    assert cost_usd("claude-sonnet-5", 1_000_000, 0) == 3.0
    assert cost_usd("claude-sonnet-5", 0, 1_000_000) == 15.0
    assert cost_usd("unknown-model", 1_000_000, 1_000_000) == 0.0


# --- BaseAgent structured-output loop --------------------------------------
def _valid_finding_input() -> dict:
    return {
        "agent_name": "technical",
        "stance": "bullish",
        "confidence": 0.7,
        "summary": "Clean stage-2 uptrend above all key moving averages.",
        "evidence": [
            {"claim": "Price above 50-DMA and 200-DMA", "source_tool": "get_price_action"},
            {"claim": "M5 moving-average structure aligned", "source_tool": "get_module_score",
             "rule_id": "M5.3"},
        ],
        "invalidation": "A daily close below the 50-DMA.",
        "data_available": True,
    }


def test_base_agent_repairs_invalid_output():
    invalid = dict(_valid_finding_input())
    invalid.pop("stance")  # required field missing -> validation error
    transport = FakeTransport(
        [
            _tool_use_response("submit_finding", invalid),
            _tool_use_response("submit_finding", _valid_finding_input()),
        ]
    )
    agent = BaseAgent(
        name="technical",
        model="claude-sonnet-5",
        system_prompt="x",
        output_model=AgentFinding,
        transport=transport,
        config=LLMConfig(),
        registry=TECHNICAL_REGISTRY,
        submit_tool_name="submit_finding",
    )
    result = agent.run("analyze")
    assert isinstance(result.output, AgentFinding)
    assert result.stats.iterations == 2  # repaired on the second round


def test_base_agent_raises_when_budget_exhausted():
    always_invalid = dict(_valid_finding_input())
    always_invalid.pop("stance")
    transport = FakeTransport([_tool_use_response("submit_finding", always_invalid)] * 3)
    agent = BaseAgent(
        name="technical",
        model="claude-sonnet-5",
        system_prompt="x",
        output_model=AgentFinding,
        transport=transport,
        config=LLMConfig(max_tool_iterations=1),  # force submit immediately
        registry=TECHNICAL_REGISTRY,
        submit_tool_name="submit_finding",
    )
    with pytest.raises(AgentError):
        agent.run("analyze")


# --- anti-fabrication invariant ---------------------------------------------
def test_technical_agent_calls_tool_and_evidence_is_traceable():
    transport = FakeTransport(
        [
            _tool_use_response("get_module_score", {"ticker": TEST_TICKER, "module": "M5"}),
            _tool_use_response("submit_finding", _valid_finding_input()),
        ]
    )
    agent = TechnicalAnalysisAgent(transport=transport, config=LLMConfig())
    result = agent.analyze(TEST_TICKER)
    finding: AgentFinding = result.output  # type: ignore[assignment]

    # A tool was actually invoked before a verdict was formed.
    assert any(c["tool"] == "get_module_score" for c in result.stats.tool_calls)
    # agent_name is authoritative regardless of the model.
    assert finding.agent_name == "technical"
    # Every evidence item names a real MCP tool — the anti-fabrication invariant.
    real_tools = set(TECHNICAL_REGISTRY.names())
    assert finding.evidence
    for ev in finding.evidence:
        assert ev.source_tool in real_tools


# --- Master orchestration ---------------------------------------------------
def test_master_produces_report_with_disclaimer_and_findings():
    master_synth = {
        "overall_stance": "bullish",
        "confidence": 0.65,
        "master_synthesis": "Constructive technical setup; primary risk is a 50-DMA break.",
        "uncertainties": ["No fundamental, news, or macro coverage in this milestone."],
    }
    transport = FakeTransport(
        [
            _tool_use_response("get_module_score", {"ticker": TEST_TICKER, "module": "M5"}),
            _tool_use_response("submit_finding", _valid_finding_input()),
            _tool_use_response("submit_report", master_synth),
        ]
    )
    master = MasterAgent(transport=transport, config=LLMConfig())
    report, stats = master.analyze(TEST_TICKER)

    assert isinstance(report, ResearchReport)
    assert report.ticker == TEST_TICKER
    assert report.disclaimer  # server-owned, always present
    assert "not investment advice" in report.disclaimer.lower()
    assert len(report.findings) == 1
    assert report.findings[0].agent_name == "technical"
    assert report.uncertainties
    # stats = [technical, master]
    assert len(stats) == 2
    assert stats[-1].agent_name == "master"


def test_master_synthesis_schema_has_no_data_fields():
    # Guards the design rule: the model synthesizes narrative only; code owns data fields.
    fields = set(MasterSynthesis.model_fields)
    assert "aggregate_score" not in fields
    assert "ticker" not in fields
    assert "disclaimer" not in fields
