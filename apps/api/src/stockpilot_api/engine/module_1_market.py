"""Module 1 — Market Environment (15 rules).

Weight in aggregate: 15/100. HARD GATE for rules M1.1, M1.4, M1.5.

Every rule follows the shape:
  - id, name, source (book code)
  - test: a callable that returns (passed: bool, actual: float|str|None)
  - threshold: string for humans
  - weight: 0-100 within this module

See docs/RULEBOOK.md § Module 1 for the specification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from stockpilot_api.indicators import sma
from stockpilot_api.models import ModuleScore, RuleEvaluation

MODULE_ID = "M1"
MODULE_NAME = "Market Environment"
MODULE_WEIGHT = 15  # in aggregate score
HARD_GATE_RULE_IDS = frozenset({"M1.1", "M1.4", "M1.5"})


@dataclass(frozen=True)
class MarketContext:
    """Latest market state passed to the rule evaluator.

    Attributes:
      nifty: DataFrame indexed by date with column "close" (Nifty 50)
      nifty_midcap: DataFrame same shape (Nifty Midcap 100)
      nifty_smallcap: DataFrame same shape (Nifty Smallcap 100)
      india_vix: latest India VIX close (float)
      fii_net_10d: sum of FII net equity flows in ₹ crore over last 10 sessions
      dii_net_10d: sum of DII net equity flows in ₹ crore over last 10 sessions
      usd_inr_change_20d: pct change of USD/INR over trailing 20 sessions
      in10y_bp_change_20d: change of Indian 10Y G-Sec yield in basis points over 20 sessions
      advance_count: NSE advancing stocks (latest session)
      decline_count: NSE declining stocks (latest session)
      days_since_follow_through: sessions since last confirmed follow-through day
    """

    nifty: pd.DataFrame
    nifty_midcap: pd.DataFrame
    nifty_smallcap: pd.DataFrame
    india_vix: float
    fii_net_10d: float
    dii_net_10d: float
    usd_inr_change_20d: float
    in10y_bp_change_20d: float
    advance_count: int
    decline_count: int
    days_since_follow_through: int


# --- Distribution-day detector ----------------------------------------------


def _count_distribution_days(nifty: pd.DataFrame, lookback: int = 20) -> int:
    """
    Distribution day = close down > 0.2% on higher volume than the prior day.
    Per [O] O'Neil.
    """
    if len(nifty) < lookback + 1 or "volume" not in nifty.columns:
        return 0
    tail = nifty.tail(lookback + 1).copy()
    tail["close_pct"] = tail["close"].pct_change()
    tail["prev_vol"] = tail["volume"].shift(1)
    tail = tail.tail(lookback)
    dist = (tail["close_pct"] < -0.002) & (tail["volume"] > tail["prev_vol"])
    return int(dist.sum())


# --- Rule table -------------------------------------------------------------

# Each rule: (id, name, source, weight, evaluator_fn, threshold_desc)
# evaluator_fn(ctx) -> tuple[bool, actual_value_str_or_none]


def _rule_m1_1(ctx: MarketContext) -> tuple[bool, str]:
    latest_close = ctx.nifty["close"].iloc[-1]
    sma200 = sma(ctx.nifty["close"], 200).iloc[-1]
    passed = bool(latest_close > sma200) if pd.notna(sma200) else False
    return passed, f"close={latest_close:.2f}, sma200={sma200:.2f}"


def _rule_m1_2(ctx: MarketContext) -> tuple[bool, str]:
    latest_close = ctx.nifty["close"].iloc[-1]
    sma50 = sma(ctx.nifty["close"], 50).iloc[-1]
    passed = bool(latest_close > sma50) if pd.notna(sma50) else False
    return passed, f"close={latest_close:.2f}, sma50={sma50:.2f}"


def _rule_m1_3(ctx: MarketContext) -> tuple[bool, str]:
    sma50 = sma(ctx.nifty["close"], 50).iloc[-1]
    sma200 = sma(ctx.nifty["close"], 200).iloc[-1]
    passed = bool(sma50 > sma200) if pd.notna(sma50) and pd.notna(sma200) else False
    return passed, f"sma50={sma50:.2f}, sma200={sma200:.2f}"


def _rule_m1_4(ctx: MarketContext) -> tuple[bool, str]:
    """200 SMA sloping up ≥ 30 sessions ago."""
    sma200_series = sma(ctx.nifty["close"], 200)
    if len(sma200_series) < 31 or pd.isna(sma200_series.iloc[-1]) or pd.isna(sma200_series.iloc[-31]):
        return False, "insufficient data"
    now = sma200_series.iloc[-1]
    ago = sma200_series.iloc[-31]
    return bool(now > ago), f"sma200_now={now:.2f} vs 30d_ago={ago:.2f}"


def _rule_m1_5(ctx: MarketContext) -> tuple[bool, str]:
    dist_days = _count_distribution_days(ctx.nifty, lookback=20)
    return dist_days < 5, f"{dist_days} distribution days in last 20"


def _rule_m1_6(ctx: MarketContext) -> tuple[bool, str]:
    return ctx.advance_count > ctx.decline_count, f"adv={ctx.advance_count} dec={ctx.decline_count}"


def _rule_m1_7(ctx: MarketContext) -> tuple[bool, str]:
    # TUNABLE — confirm from source; 20 is a common threshold for India VIX
    return ctx.india_vix < 20.0, f"VIX={ctx.india_vix:.2f} (threshold 20)"


def _rule_m1_8(ctx: MarketContext) -> tuple[bool, str]:
    """Nifty not near 52-week low: > min(close, 252) * 1.15."""
    if len(ctx.nifty) < 252:
        return False, "insufficient history"
    low_52w = float(ctx.nifty["close"].tail(252).min())
    latest = float(ctx.nifty["close"].iloc[-1])
    return latest > low_52w * 1.15, f"latest={latest:.2f} vs 52w-low*1.15={low_52w*1.15:.2f}"


def _rule_m1_9(ctx: MarketContext) -> tuple[bool, str]:
    latest = ctx.nifty_midcap["close"].iloc[-1]
    sma200 = sma(ctx.nifty_midcap["close"], 200).iloc[-1]
    passed = bool(latest > sma200) if pd.notna(sma200) else False
    return passed, f"midcap={latest:.2f} vs sma200={sma200:.2f}"


def _rule_m1_10(ctx: MarketContext) -> tuple[bool, str]:
    latest = ctx.nifty_smallcap["close"].iloc[-1]
    sma200 = sma(ctx.nifty_smallcap["close"], 200).iloc[-1]
    passed = bool(latest > sma200) if pd.notna(sma200) else False
    return passed, f"smallcap={latest:.2f} vs sma200={sma200:.2f}"


def _rule_m1_11(ctx: MarketContext) -> tuple[bool, str]:
    return ctx.days_since_follow_through <= 28, f"days_since_FTD={ctx.days_since_follow_through}"


def _rule_m1_12(ctx: MarketContext) -> tuple[bool, str]:
    # TUNABLE — 2% pct-change threshold for USD/INR over 20 sessions
    return ctx.usd_inr_change_20d < 0.02, f"USDINR 20d change={ctx.usd_inr_change_20d*100:.2f}%"


def _rule_m1_13(ctx: MarketContext) -> tuple[bool, str]:
    # TUNABLE — 50 bps threshold
    return ctx.in10y_bp_change_20d < 50.0, f"IN10Y 20d change={ctx.in10y_bp_change_20d:.1f} bps"


def _rule_m1_14(ctx: MarketContext) -> tuple[bool, str]:
    return ctx.fii_net_10d > 0, f"FII net 10d=₹{ctx.fii_net_10d:.0f} cr"


def _rule_m1_15(ctx: MarketContext) -> tuple[bool, str]:
    return ctx.dii_net_10d > 0, f"DII net 10d=₹{ctx.dii_net_10d:.0f} cr"


# --- Rule table (declarative) ------------------------------------------------

RULES: list[tuple[str, str, str, int, Callable[[MarketContext], tuple[bool, str]]]] = [
    ("M1.1",  "Nifty 50 above 200 SMA",                     "[O] CAN SLIM 'M' / [W] Stage 2", 10, _rule_m1_1),
    ("M1.2",  "Nifty 50 above 50 SMA",                       "[O]",                              8, _rule_m1_2),
    ("M1.3",  "50 SMA > 200 SMA",                            "[O] golden-cross",                 8, _rule_m1_3),
    ("M1.4",  "200 SMA sloping up (30-day)",                 "[W] Stage 2 requires rising MA",   8, _rule_m1_4),
    ("M1.5",  "< 5 distribution days in last 20 sessions",   "[O]",                             10, _rule_m1_5),
    ("M1.6",  "Advance/decline positive (breadth)",          "[Mu] intermarket / [O]",           6, _rule_m1_6),
    ("M1.7",  "India VIX < 20",                              "risk management (TUNABLE)",        5, _rule_m1_7),
    ("M1.8",  "Nifty > 15% above 52-week low",               "[Mv] Trend Template applied",      5, _rule_m1_8),
    ("M1.9",  "Nifty Midcap 100 above 200 SMA",              "[Mu] breadth via mid-caps",        5, _rule_m1_9),
    ("M1.10", "Nifty Smallcap 100 above 200 SMA",            "[Mu] breadth confirmation",        4, _rule_m1_10),
    ("M1.11", "Follow-through day within last 28 sessions",  "[O] follow-through day method",    6, _rule_m1_11),
    ("M1.12", "USD/INR not aggressively depreciating (20d)", "[Mu] intermarket",                 4, _rule_m1_12),
    ("M1.13", "10Y G-Sec yield not spiking (< 50bp / 20d)",  "[Mu] intermarket",                 4, _rule_m1_13),
    ("M1.14", "FII net flows positive (10d)",                "[O] the 'I' in CAN SLIM",          8, _rule_m1_14),
    ("M1.15", "DII net flows positive (10d)",                "domestic institutional support",   8, _rule_m1_15),
]


def evaluate_market_environment(ctx: MarketContext) -> ModuleScore:
    """
    Run all 15 rules of Module 1 and produce a ModuleScore.

    Score = weighted percent of rules passed (weights sum to 99, we normalize to 100).
    Hard gates: if M1.1, M1.4, or M1.5 fail, `hard_gates_passed=False`.
    """
    evaluations: list[RuleEvaluation] = []
    weighted_pass = 0.0
    total_weight = 0.0
    hard_gate_ok = True

    for rule_id, name, source, weight, fn in RULES:
        passed, actual = fn(ctx)
        is_hard = rule_id in HARD_GATE_RULE_IDS
        if is_hard and not passed:
            hard_gate_ok = False

        total_weight += weight
        if passed:
            weighted_pass += weight

        evaluations.append(
            RuleEvaluation(
                rule_id=rule_id,
                module_id=MODULE_ID,
                passed=passed,
                actual_value=actual,
                threshold=name,
                is_hard_gate=is_hard,
                source_citation=source,
            )
        )

    score = 100.0 * weighted_pass / total_weight if total_weight else 0.0

    return ModuleScore(
        module_id=MODULE_ID,
        module_name=MODULE_NAME,
        score=round(score, 2),
        weight_in_aggregate=MODULE_WEIGHT,
        rule_evaluations=evaluations,
        hard_gates_passed=hard_gate_ok,
    )
