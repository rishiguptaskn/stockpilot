"""Graph nodes — deterministic nodes are pure code; agent nodes wrap BaseAgent.

Failure policy (ARCHITECTURE.md §10.2):
  - Analysis agents are FAIL-SOFT: on any error they contribute a degraded
    finding (stance neutral, confidence 0, data_available False) and the run
    continues.
  - The risk gate is FAIL-CLOSED: if it cannot produce a valid assessment,
    the verdict is VETO. Unassessed risk never passes.
  - The chief analyst is fail-soft, but it can never override a risk veto —
    the veto is applied in code, after synthesis.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from stockpilot_api.agents.master import MasterSynthesis
from stockpilot_api.agents.schemas import DISCLAIMER, AgentFinding
from stockpilot_api.agents.technical import TechnicalAnalysisAgent
from stockpilot_api.agents.base import BaseAgent
from stockpilot_api.llm.client import LLMTransport
from stockpilot_api.llm.config import LLMConfig
from stockpilot_api.mcp import data_access
from stockpilot_api.orchestration.state import ResearchState
from stockpilot_api.workflow import _build_market_context, _score_stock

logger = logging.getLogger(__name__)

_MASTER_PROMPT = (
    Path(__file__).parent.parent / "agents" / "prompts" / "master.md"
).read_text(encoding="utf-8")

# Same convention as mcp/technical_tools.py: single-ticker runs have no scored
# universe, so RS rank is a neutral placeholder and we say so in the report.
_NEUTRAL_RS_RANK = 50.0

NodeFn = Callable[[ResearchState], dict[str, Any]]


def _degraded_finding(agent_name: str, reason: str) -> AgentFinding:
    return AgentFinding(
        agent_name=agent_name,
        stance="neutral",
        confidence=0.0,
        summary=f"Agent failed and contributed no analysis: {reason}",
        evidence=[],
        invalidation="N/A — no view was formed.",
        data_available=False,
    )


# --- deterministic nodes -----------------------------------------------------


def make_quant_node(*, period: str = "2y", capital_inr: float = 500_000.0) -> NodeFn:
    """Run the full deterministic rule engine for the ticker. No LLM."""

    def quant_node(state: ResearchState) -> dict[str, Any]:
        ticker = state["ticker"]
        daily = data_access.load_daily(ticker, period=period)
        if not data_access.has_sufficient_history(daily):
            return {
                "quant": {"data_available": False, "reason": f"<200 bars for {ticker}"},
                "errors": [f"quant: insufficient history for {ticker}"],
            }
        nifty = data_access.load_daily("^NSEI", period=period)
        if not data_access.has_sufficient_history(nifty):
            return {
                "quant": {"data_available": False, "reason": "no Nifty history"},
                "errors": ["quant: could not load ^NSEI for market context"],
            }

        candidate = _score_stock(
            ticker=ticker,
            daily=daily,
            market_ctx=_build_market_context(nifty),
            sector_ctx=None,
            rs_rank=_NEUTRAL_RS_RANK,
            capital_inr=capital_inr,
            include_details=True,
        )
        if candidate is None:
            return {
                "quant": {"data_available": False, "reason": "scoring returned None"},
                "errors": [f"quant: scoring failed for {ticker}"],
            }
        return {
            "quant": {
                "data_available": True,
                "ticker": candidate.ticker,
                "aggregate_score": candidate.aggregate_score,
                "verdict": candidate.verdict,
                "hard_gates_all_passed": candidate.hard_gates_all_passed,
                "module_scores": candidate.module_scores,
                "detected_patterns": candidate.detected_patterns,
                "entry": candidate.entry,
                "stop": candidate.stop,
                "target": candidate.target,
                "shares": candidate.shares,
                "module_details": candidate.metadata.get("module_details", []),
                "notes": ["rs_rank_252 is a neutral placeholder (50); "
                          "real rank needs a scored universe."],
            }
        }

    return quant_node


def make_risk_node() -> NodeFn:
    """Deterministic risk gate — Elder rules via Module 9. FAIL-CLOSED (veto)."""

    def risk_node(state: ResearchState) -> dict[str, Any]:
        quant = state.get("quant") or {}
        reasons: list[str] = []

        if not quant.get("data_available"):
            return {
                "risk": {
                    "verdict": "veto",
                    "reasons": ["Risk cannot be assessed: no quant data. Failing closed."],
                    "plan": None,
                }
            }

        m9 = next(
            (m for m in quant.get("module_details", []) if m.get("module_id") == "M9"),
            None,
        )
        if m9 is None:
            reasons.append("Module 9 (risk) result missing. Failing closed.")
        else:
            for rule in m9.get("rule_evaluations", []):
                if rule.get("is_hard_gate") and not rule.get("passed"):
                    reasons.append(
                        f"Hard gate {rule.get('rule_id')} failed: "
                        f"actual={rule.get('actual_value')} vs "
                        f"threshold={rule.get('threshold')} "
                        f"[{rule.get('source_citation')}]"
                    )

        shares = quant.get("shares") or 0
        entry, stop, target = quant.get("entry"), quant.get("stop"), quant.get("target")
        if shares <= 0:
            reasons.append("Position size is zero — risk per share exceeds the 2% budget.")
        if entry is not None and stop is not None and stop >= entry:
            reasons.append("Stop is at/above entry — invalid trade plan.")

        plan = {
            "entry": entry,
            "stop": stop,
            "target": target,
            "shares": shares,
            "risk_inr": round((entry - stop) * shares, 2)
            if entry is not None and stop is not None
            else None,
        }
        return {
            "risk": {
                "verdict": "veto" if reasons else "ok",
                "reasons": reasons,
                "plan": plan,
            }
        }

    return risk_node


def make_decision_node() -> NodeFn:
    """Deterministic decision — score/verdict/gates → action. The LLM cannot change this."""

    def decision_node(state: ResearchState) -> dict[str, Any]:
        quant = state.get("quant") or {}
        risk = state.get("risk") or {"verdict": "veto", "reasons": ["risk missing"]}

        if not quant.get("data_available"):
            action = "no-trade"
        elif risk["verdict"] == "veto":
            action = "no-trade"
        elif quant.get("verdict") == "candidate":
            action = "candidate"
        elif quant.get("verdict") == "watch":
            action = "watch"
        else:
            action = "no-trade"

        return {
            "decision": {
                "action": action,
                "aggregate_score": quant.get("aggregate_score", 0.0),
                "engine_verdict": quant.get("verdict", "reject"),
                "hard_gates_all_passed": quant.get("hard_gates_all_passed", False),
                "risk_verdict": risk["verdict"],
            }
        }

    return decision_node


def make_explain_node() -> NodeFn:
    """Assemble the final explainable report — pure code, no LLM."""

    def explain_node(state: ResearchState) -> dict[str, Any]:
        quant = state.get("quant") or {}
        decision = state.get("decision") or {}
        risk = state.get("risk") or {}
        synthesis = state.get("synthesis") or {}

        rule_breakdown = []
        for m in quant.get("module_details", []):
            rule_breakdown.append(
                {
                    "module_id": m.get("module_id"),
                    "module_name": m.get("module_name"),
                    "score": m.get("score"),
                    "weight": m.get("weight_in_aggregate"),
                    "hard_gates_passed": m.get("hard_gates_passed"),
                    "failed_rules": [
                        {
                            "rule_id": r.get("rule_id"),
                            "actual": r.get("actual_value"),
                            "threshold": r.get("threshold"),
                            "hard_gate": r.get("is_hard_gate"),
                            "citation": r.get("source_citation"),
                        }
                        for r in m.get("rule_evaluations", [])
                        if not r.get("passed")
                    ],
                }
            )

        report = {
            "ticker": state["ticker"],
            "as_of": state.get("as_of") or date.today().isoformat(),
            "action": decision.get("action", "no-trade"),
            "aggregate_score": decision.get("aggregate_score", 0.0),
            "engine_verdict": decision.get("engine_verdict", "reject"),
            "risk": risk,
            "overall_stance": synthesis.get("overall_stance", "neutral"),
            "confidence": synthesis.get("confidence", 0.0),
            "narrative": synthesis.get("master_synthesis", "No synthesis available."),
            "uncertainties": synthesis.get("uncertainties", []),
            "findings": state.get("findings", []),
            "detected_patterns": quant.get("detected_patterns", []),
            "rule_breakdown": rule_breakdown,
            "notes": quant.get("notes", []),
            "errors": state.get("errors", []),
            "disclaimer": DISCLAIMER,  # server-owned, never model-generated
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"report": report}

    return explain_node


# --- agent nodes (LLM — fail-soft) --------------------------------------------


def make_technical_node(transport: LLMTransport, config: LLMConfig) -> NodeFn:
    def technical_node(state: ResearchState) -> dict[str, Any]:
        try:
            agent = TechnicalAnalysisAgent(transport=transport, config=config)
            result = agent.analyze(state["ticker"])
            return {
                "findings": [result.output.model_dump(mode="json")],
                "stats": [
                    {
                        "agent": result.stats.agent_name,
                        "model": result.stats.model,
                        "input_tokens": result.stats.input_tokens,
                        "output_tokens": result.stats.output_tokens,
                        "cost_usd": result.stats.cost_usd,
                    }
                ],
            }
        except Exception as exc:  # fail-soft: degraded finding, run continues
            logger.exception("technical agent failed for %s", state["ticker"])
            return {
                "findings": [_degraded_finding("technical", str(exc)).model_dump(mode="json")],
                "errors": [f"technical agent failed: {exc}"],
            }

    return technical_node


def make_chief_node(transport: LLMTransport, config: LLMConfig) -> NodeFn:
    """Chief Analyst — synthesizes findings + deterministic results into narrative.

    It composes and explains; it CANNOT change the deterministic decision or
    override a risk veto (both applied in code downstream).
    """

    def chief_node(state: ResearchState) -> dict[str, Any]:
        import json as _json

        findings = state.get("findings", [])
        decision = state.get("decision") or {}
        risk = state.get("risk") or {}
        try:
            agent = BaseAgent(
                name="chief_analyst",
                model=config.master_model,
                system_prompt=_MASTER_PROMPT,
                output_model=MasterSynthesis,
                transport=transport,
                config=config,
                registry=None,  # synthesis composes findings; it fetches nothing
                submit_tool_name="submit_report",
                submit_tool_description="Submit your final synthesis. Call exactly once.",
            )
            task = (
                f"Ticker: {state['ticker']}\n\n"
                f"Deterministic decision (authoritative — do not contradict):\n"
                f"{_json.dumps(decision, indent=2)}\n\n"
                f"Risk gate (authoritative — a veto is final):\n"
                f"{_json.dumps(risk, indent=2, default=str)}\n\n"
                f"Specialist findings to synthesize (do NOT introduce new numbers):\n"
                f"{_json.dumps(findings, indent=2)}"
            )
            result = agent.run(task)
            synthesis: MasterSynthesis = result.output  # type: ignore[assignment]
            out = synthesis.model_dump(mode="json")
            stats = [
                {
                    "agent": "chief_analyst",
                    "model": result.stats.model,
                    "input_tokens": result.stats.input_tokens,
                    "output_tokens": result.stats.output_tokens,
                    "cost_usd": result.stats.cost_usd,
                }
            ]
        except Exception as exc:  # fail-soft — report still assembles
            logger.exception("chief analyst failed for %s", state["ticker"])
            out = {
                "overall_stance": "neutral",
                "confidence": 0.0,
                "master_synthesis": f"Synthesis unavailable (agent failed: {exc}). "
                "Deterministic results above are unaffected.",
                "uncertainties": ["Chief analyst synthesis failed — narrative missing."],
            }
            stats = []
            return {"synthesis": out, "stats": stats, "errors": [f"chief analyst failed: {exc}"]}

        # Code-level guard: stance can never be bullish when the engine said no-trade.
        if decision.get("action") == "no-trade" and out.get("overall_stance") == "bullish":
            out["overall_stance"] = "neutral"
            out["uncertainties"] = [
                *out.get("uncertainties", []),
                "Model stance was bullish but the deterministic decision is no-trade; "
                "stance clamped to neutral.",
            ]
        return {"synthesis": out, "stats": stats}

    return chief_node
