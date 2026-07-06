"""Module 8 — News & Events (15 rules).

Weight in aggregate: 5/100. HARD GATES: M8.1, M8.4, M8.14.

Rules that depend on external feeds (Claude API sentiment, NSE ban lists, macro
calendars) accept the values from the context. In v1 we accept defaults that
correspond to "no negative news". Enrich via Claude in Month 4 per PLAN.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M8"
MODULE_NAME = "News & Events"
MODULE_WEIGHT = 5
HARD_GATE_RULE_IDS = frozenset({"M8.1", "M8.4", "M8.14"})


@dataclass(frozen=True)
class NewsContext:
    days_until_next_earnings: int = 30
    latest_earnings_surprise: float = 0.0
    news_sentiment_30d: float = 0.0  # -1..+1 from Claude
    has_regulatory_flags: bool = False
    days_since_mgmt_change: int = 999
    has_recent_dilution_180d: bool = False
    next_corp_action_within_days: int = 999
    sector_news_sentiment_14d: float = 0.0
    has_recent_analyst_upgrade: bool = False
    vix_change_5d_pct: float = 0.0
    days_until_next_rbi_meeting: int = 999
    days_until_next_budget: int = 999
    in_fno_ban_list: bool = False
    in_gsm_or_asm_list: bool = False
    promoter_pledge_pct: float = 0.0
    has_recent_audit_qualification: bool = False


def _rule(fn):
    return fn


@_rule
def _n1(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.days_until_next_earnings >= 3, f"{ctx.days_until_next_earnings}d to earnings"


@_rule
def _n2(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.latest_earnings_surprise >= 0, f"surprise={ctx.latest_earnings_surprise:.2f}"


@_rule
def _n3(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.news_sentiment_30d >= 0, f"sentiment={ctx.news_sentiment_30d:.2f}"


@_rule
def _n4(ctx: NewsContext) -> tuple[bool, str]:
    return not ctx.has_regulatory_flags, "no regulatory flags" if not ctx.has_regulatory_flags else "regulatory flag set"


@_rule
def _n5(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.days_since_mgmt_change >= 60, f"{ctx.days_since_mgmt_change}d since mgmt change"


@_rule
def _n6(ctx: NewsContext) -> tuple[bool, str]:
    return not ctx.has_recent_dilution_180d, "no dilution 180d"


@_rule
def _n7(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.next_corp_action_within_days > 20, f"{ctx.next_corp_action_within_days}d to next corp action"


@_rule
def _n8(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.sector_news_sentiment_14d >= -0.3, f"sector sentiment={ctx.sector_news_sentiment_14d:.2f}"


@_rule
def _n9(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.has_recent_analyst_upgrade, "recent upgrade" if ctx.has_recent_analyst_upgrade else "no upgrade"


@_rule
def _n10(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.vix_change_5d_pct < 0.20, f"VIX Δ5d={ctx.vix_change_5d_pct*100:.1f}%"


@_rule
def _n11(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.days_until_next_rbi_meeting > 20, f"{ctx.days_until_next_rbi_meeting}d to RBI"


@_rule
def _n12(ctx: NewsContext) -> tuple[bool, str]:
    return ctx.days_until_next_budget > 20, f"{ctx.days_until_next_budget}d to budget"


@_rule
def _n13(ctx: NewsContext) -> tuple[bool, str]:
    return not ctx.in_fno_ban_list, "not in F&O ban" if not ctx.in_fno_ban_list else "in F&O ban"


@_rule
def _n14(ctx: NewsContext) -> tuple[bool, str]:
    return not ctx.in_gsm_or_asm_list, "not in GSM/ASM" if not ctx.in_gsm_or_asm_list else "in GSM/ASM"


@_rule
def _n15(ctx: NewsContext) -> tuple[bool, str]:
    return (ctx.promoter_pledge_pct < 20 and not ctx.has_recent_audit_qualification), (
        f"pledge={ctx.promoter_pledge_pct:.1f}%, audit_qual={ctx.has_recent_audit_qualification}"
    )


RULES: list[tuple[str, str, str, int, Callable[[NewsContext], tuple[bool, str]]]] = [
    ("M8.1",  "≥ 3 sessions until next earnings",          "[O][E]",         12, _n1),
    ("M8.2",  "Last earnings beat or in-line",              "[O]",             8, _n2),
    ("M8.3",  "News sentiment 30d ≥ 0",                     "Claude API",     8, _n3),
    ("M8.4",  "No regulatory flags",                        "governance",     10, _n4),
    ("M8.5",  "No mgmt change in last 60d",                 "[O]",             6, _n5),
    ("M8.6",  "No recent equity dilution (180d)",           "[O]",             6, _n6),
    ("M8.7",  "No corp action within 20 sessions",          "mechanical adj",  5, _n7),
    ("M8.8",  "Sector news sentiment ≥ -0.3 (14d)",          "Claude API",     5, _n8),
    ("M8.9",  "Recent analyst upgrade (bonus)",             "[O]",             3, _n9),
    ("M8.10", "No global macro shock (VIX 5d < 20%)",       "[Mu]",            5, _n10),
    ("M8.11", "No RBI meeting within trade horizon",         "IN-specific",    4, _n11),
    ("M8.12", "No Union Budget within trade horizon",        "IN-specific",    4, _n12),
    ("M8.13", "Not in F&O ban list",                          "NSE",            6, _n13),
    ("M8.14", "Not in GSM/ASM list",                          "NSE surveillance", 8, _n14),
    ("M8.15", "Governance clean (pledge < 20% + no audit qual)", "[O]",         6, _n15),
]


def evaluate_news(ctx: NewsContext) -> ModuleScore:
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    hard_ok = True
    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
        is_hard = rule_id in HARD_GATE_RULE_IDS
        if is_hard and not passed:
            hard_ok = False
        total_weight += weight
        if passed:
            weighted_pass += weight
        evaluations.append(RuleEvaluation(
            rule_id=rule_id, module_id=MODULE_ID, passed=passed,
            actual_value=actual, threshold=name, is_hard_gate=is_hard, source_citation=source,
        ))
    score = 100.0 * weighted_pass / total_weight if total_weight else 0.0
    return ModuleScore(
        module_id=MODULE_ID, module_name=MODULE_NAME, score=round(score, 2),
        weight_in_aggregate=MODULE_WEIGHT, rule_evaluations=evaluations, hard_gates_passed=hard_ok,
    )
