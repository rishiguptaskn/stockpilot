"""LangGraph orchestration tests — scripted transports, seeded data, no network."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import stockpilot_api.mcp.data_access as data_access
from stockpilot_api.agents.schemas import DISCLAIMER
from stockpilot_api.llm.client import LLMResponse, ToolUse, Usage
from stockpilot_api.llm.config import LLMConfig
from stockpilot_api.llm.gateway import RoutingTransport
from stockpilot_api.orchestration import build_research_graph, run_research
from stockpilot_api.orchestration.nodes import make_decision_node, make_risk_node

TEST_TICKER = "TEST.NS"


def _synthetic_daily(n: int = 320, start: float = 100.0, end: float = 300.0) -> pd.DataFrame:
    idx = pd.bdate_range(end="2026-07-01", periods=n)
    trend = np.linspace(start, end, n)
    noise = np.sin(np.linspace(0, 40, n)) * 3.0
    close = trend + noise
    return pd.DataFrame(
        {
            "open": close * 0.995,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.linspace(1_000_000, 2_000_000, n).astype(int),
        },
        index=idx,
    )


@pytest.fixture(autouse=True)
def _seed_cache():
    data_access.clear_cache()
    data_access._CACHE[TEST_TICKER] = _synthetic_daily()
    data_access._CACHE["^NSEI"] = _synthetic_daily(start=15000.0, end=26000.0)
    yield
    data_access.clear_cache()


class FakeTransport:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> LLMResponse:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("FakeTransport ran out of scripted responses")
        return self._responses.pop(0)


class ExplodingTransport:
    def create(self, **kwargs) -> LLMResponse:
        raise ConnectionError("LLM unreachable")


def _submit(name: str, payload: dict) -> LLMResponse:
    return LLMResponse(
        stop_reason="tool_use",
        text="",
        tool_uses=[ToolUse(id=f"tu_{name}", name=name, input=payload)],
        usage=Usage(input_tokens=100, output_tokens=50),
        raw_content=[{"type": "tool_use", "id": f"tu_{name}", "name": name, "input": payload}],
    )


FINDING = {
    "agent_name": "technical",
    "stance": "bullish",
    "confidence": 0.8,
    "summary": "Strong uptrend, price above all MAs.",
    "evidence": [{"claim": "close above 200 SMA", "source_tool": "get_indicators"}],
    "invalidation": "Close below the 50 SMA.",
    "data_available": True,
}

SYNTHESIS = {
    "overall_stance": "bullish",
    "confidence": 0.7,
    "master_synthesis": "Technicals are constructive; deterministic engine verdict applies.",
    "uncertainties": ["Fundamentals not analyzed."],
}


def _happy_transport() -> FakeTransport:
    return FakeTransport(
        [
            _submit("submit_finding", FINDING),  # technical agent
            _submit("submit_report", SYNTHESIS),  # chief analyst
        ]
    )


# --- full graph ---------------------------------------------------------------


def test_graph_end_to_end_produces_explainable_report():
    report = run_research(TEST_TICKER, _happy_transport(), LLMConfig())
    assert report["ticker"] == TEST_TICKER
    assert report["action"] in {"candidate", "watch", "no-trade"}
    assert report["disclaimer"] == DISCLAIMER
    assert report["rule_breakdown"], "explainability requires the rule breakdown"
    module_ids = {m["module_id"] for m in report["rule_breakdown"]}
    assert {"M1", "M9"} <= module_ids
    assert report["findings"][0]["agent_name"] == "technical"
    assert report["risk"]["verdict"] in {"ok", "veto"}
    assert "generated_at" in report


def test_decision_is_deterministic_ignores_llm_stance():
    """Same quant data, wildly different LLM outputs → identical decision."""
    bearish = {**SYNTHESIS, "overall_stance": "bearish", "confidence": 0.99}
    r1 = run_research(TEST_TICKER, _happy_transport(), LLMConfig())
    r2 = run_research(
        TEST_TICKER,
        FakeTransport([_submit("submit_finding", FINDING), _submit("submit_report", bearish)]),
        LLMConfig(),
    )
    assert r1["action"] == r2["action"]
    assert r1["aggregate_score"] == r2["aggregate_score"]


def test_agents_fail_soft_report_still_assembles():
    """LLM completely down → degraded findings, but a full report still emerges."""
    report = run_research(TEST_TICKER, ExplodingTransport(), LLMConfig())
    assert report["ticker"] == TEST_TICKER
    assert report["findings"][0]["data_available"] is False
    assert report["confidence"] == 0.0
    assert report["errors"], "failures must be recorded, not hidden"
    assert report["rule_breakdown"], "deterministic results unaffected by LLM outage"


def test_unknown_ticker_fails_closed():
    """No data → quant unavailable → risk veto → action no-trade."""
    data_access._CACHE["EMPTY.NS"] = pd.DataFrame()
    report = run_research("EMPTY.NS", ExplodingTransport(), LLMConfig())
    assert report["action"] == "no-trade"
    assert report["risk"]["verdict"] == "veto"


# --- node-level guards ---------------------------------------------------------


def test_risk_node_vetoes_on_failed_hard_gate():
    state = {
        "ticker": TEST_TICKER,
        "quant": {
            "data_available": True,
            "entry": 100.0,
            "stop": 93.0,
            "target": 121.0,
            "shares": 100,
            "module_details": [
                {
                    "module_id": "M9",
                    "rule_evaluations": [
                        {
                            "rule_id": "M9.1",
                            "passed": False,
                            "is_hard_gate": True,
                            "actual_value": "2.5%",
                            "threshold": "<=2%",
                            "source_citation": "[E] Elder 2% rule",
                        }
                    ],
                }
            ],
        },
    }
    out = make_risk_node()(state)
    assert out["risk"]["verdict"] == "veto"
    assert "M9.1" in out["risk"]["reasons"][0]


def test_risk_node_vetoes_zero_shares():
    state = {
        "ticker": TEST_TICKER,
        "quant": {
            "data_available": True,
            "entry": 100.0,
            "stop": 93.0,
            "target": 121.0,
            "shares": 0,
            "module_details": [{"module_id": "M9", "rule_evaluations": []}],
        },
    }
    out = make_risk_node()(state)
    assert out["risk"]["verdict"] == "veto"


def test_decision_no_trade_on_veto_even_with_high_score():
    state = {
        "quant": {
            "data_available": True,
            "aggregate_score": 95.0,
            "verdict": "candidate",
            "hard_gates_all_passed": True,
        },
        "risk": {"verdict": "veto", "reasons": ["x"]},
    }
    out = make_decision_node()(state)
    assert out["decision"]["action"] == "no-trade"


def test_chief_bullish_stance_clamped_on_no_trade():
    """LLM says bullish, engine says no-trade → stance forced to neutral in report."""
    data_access._CACHE["EMPTY2.NS"] = pd.DataFrame()
    report = run_research(
        "EMPTY2.NS",
        FakeTransport(
            [
                _submit("submit_finding", FINDING),
                _submit("submit_report", {**SYNTHESIS, "overall_stance": "bullish"}),
            ]
        ),
        LLMConfig(),
    )
    assert report["action"] == "no-trade"
    assert report["overall_stance"] == "neutral"


# --- gateway routing -----------------------------------------------------------


def test_routing_transport_routes_by_prefix():
    class Recording:
        def __init__(self):
            self.models = []

        def create(self, *, model, **kw):
            self.models.append(model)
            return LLMResponse(stop_reason="end_turn", text="", tool_uses=[], usage=Usage())

    a, o = Recording(), Recording()
    router = RoutingTransport(anthropic=a, openai=o)
    router.create(model="claude-sonnet-5", system="", messages=[], tools=[],
                  max_tokens=10, temperature=0.0)
    router.create(model="gpt-4.1", system="", messages=[], tools=[],
                  max_tokens=10, temperature=0.0)
    assert a.models == ["claude-sonnet-5"]
    assert o.models == ["gpt-4.1"]


def test_routing_transport_missing_provider_is_loud():
    router = RoutingTransport(anthropic=None, openai=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        router.create(model="claude-sonnet-5", system="", messages=[], tools=[],
                      max_tokens=10, temperature=0.0)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        router.create(model="gpt-4.1", system="", messages=[], tools=[],
                      max_tokens=10, temperature=0.0)
    with pytest.raises(RuntimeError, match="Unknown model family"):
        router.create(model="mystery-model", system="", messages=[], tools=[],
                      max_tokens=10, temperature=0.0)
