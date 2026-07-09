# Backtest Findings — Round 1 (2026-07-10)

**Status:** ❌ **No demonstrated edge yet. No live capital.** (PLAN.md §10 gate: requires positive expectancy after costs — not met with statistical confidence.)

## Methodology

- Engine: `stockpilot_api.backtest` — point-in-time walk-forward; signals on day T fill at day T+1 open; conservative fills (gap-through-stop at open, stop-before-target in one bar); Elder 2%/6% sizing enforced; Indian delivery costs (brokerage/STT/exchange/SEBI/stamp/GST) + 0.1% slippage per side.
- Signals: the **production** `_score_stock` (same code as the live workflow), on point-in-time slices. Zero duplicated logic.
- Universe: 29 liquid NSE large caps (TATAMOTORS dropped — delisted from Yahoo). Period `5y`; RS-252 warm-up consumes ~13 months → **~4 years of effective scans**, weekly cadence.
- Trade plan (current production geometry): entry = signal close, stop = −7% flat, target = +3R, max hold 20 trading days.
- Variants: score threshold {75, 80, 85} × entry trigger {score-only (current wiring), pattern-required (18-pt checklist items 9–10 as written)}.

## Results (after costs)

| Variant | Trades | Win % | Expectancy (R) | CAGR | Max DD | PnL (₹) |
|---|---|---|---|---|---|---|
| 75 · score-only | 88 | 52.3% | −0.025 | −1.0% | 12.8% | −25,030 |
| 80 · score-only | 89 | 51.7% | −0.030 | −1.4% | 15.2% | −33,405 |
| 85 · score-only | 74 | 50.0% | +0.029 | +0.6% | 17.0% | +14,398 |
| 75 · pattern | 88 | 48.9% | −0.058 | −2.3% | 21.6% | −54,807 |
| 80 · pattern | 89 | 55.1% | +0.011 | +0.2% | 11.6% | +4,717 |
| **85 · pattern** | **73** | **49.3%** | **+0.047** | **+1.1%** | **15.5%** | **+27,972** |

Earlier 2y/10-ticker run at threshold 90: **0 trades** — 90 is unreachable while M3/M8 run on neutral defaults (observed max ≈ 88–91 only on the wider universe).

## What the data actually says

1. **Higher threshold → higher expectancy, monotonically, in both variants.** The aggregate score has real *ordering* power — the rules rank stocks meaningfully. This is the most encouraging finding.
2. **Pattern-required beats score-only at 80/85.** The 18-point checklist's "consolidation + breakout" requirement (currently scored but not required to act) adds value when selectivity is already high.
3. **Best variant (+0.047R, n=73) is NOT statistically distinguishable from zero** (SE ≈ 0.12R). Encouraging direction; not a validated edge.
4. **The exit geometry is broken:** 59/74 exits are 20-day time stops; the +3R target was hit **once in 4 years**. A ~21%-in-20-days target on mega caps is decorative. The strategy degenerates to "hold 20 days and see."
5. **Costs ate ~2/3 of the gross edge:** ≈ ₹28k costs vs ≈ ₹42k gross PnL on th85 (≈ 0.075R per trade). With edges this thin, cost drag dominates; fewer/bigger-R trades matter.

## Known biases and limitations

- Modules 3 (fundamentals) & 8 (news): **neutral defaults** — only price/technical/volume/risk rules validated. The books' core discriminator (earnings growth) is absent.
- Market context: only index trend is real; VIX/FII/breadth static.
- Survivorship bias (today's listings); yfinance data quality; mega-cap universe while O'Neil/Minervini setups target growth mid/small caps.
- Single 4-year window ≈ one-and-a-half regime cycles; no walk-forward split yet.

## Round 2 (same day): trailing-exit variants — HYPOTHESIS REJECTED

Replayed the cached th85 signals through exit variants (EMA-trail per Minervini
sell-backstop; 10/21-day; 20/40-day holds):

| Variant (th85) | Trades | Win % | Expectancy (R) | Exit mix |
|---|---|---|---|---|
| fixed3R + 20d (baseline) | 73–74 | ~50% | **+0.029 / +0.047** | 80% time |
| trail EMA21 · 20d | 86–87 | ~32% | −0.027 / −0.054 | 72% trail |
| trail EMA21 · 40d | 74–76 | ~23% | −0.056 / −0.071 | 87% trail |
| trail EMA10 · 20d | 109 | ~30% | −0.059 / −0.071 | 91% trail |

**Every trailing variant is worse than the baseline.** Large caps oscillate
around their EMAs at this timeframe; the trail fires on noise and cuts winners
early (win rate 50%→~25-30%, average hold halved). Conclusion: the exit
geometry was NOT the main problem — the **universe** likely is. Mega caps
rarely deliver the 20%+ swing moves these setups (O'Neil/Minervini growth
mid/small-cap playbooks) are designed to capture.

## Round 3 (same day): mid-cap universe — ALL VARIANTS POSITIVE (with a serious caveat)

Same methodology, 30 liquid non-mega-cap growth names, 5y:

| Variant | Trades | Win % | Expectancy (R) | CAGR | Max DD |
|---|---|---|---|---|---|
| th80 · score-only | 98 | 50.0% | +0.098 | +3.3% | 17.2% |
| th85 · score-only | 91 | 48.4% | +0.043 | +1.1% | 19.1% |
| **th80 · pattern** | 94 | 51.1% | **+0.127** | **+4.3%** | 20.2% |
| th85 · pattern | 87 | 50.6% | +0.099 | +3.1% | 15.2% |

Directional confirmation of the universe hypothesis: 4/4 positive (large caps
were 1/4); target exits 4-5× more frequent; pattern-required consistently best.

**⚠ Serious caveat:** the universe was hand-picked "liquid, well-known mid caps"
*as of today* — names famous precisely because they rose for 5 years. This is
survivorship bias at its strongest and inflates absolute numbers by an unknown
amount. +0.127R at n=94 is ~1.3 SE above zero — encouraging, NOT validated.
The *relative* findings (mid > mega, pattern > score-only) are more robust since
the bias applies across the whole grid. A trustworthy absolute number requires
**point-in-time index membership** (historical Nifty Midcap 150 constituents).

## Next experiments (re-ranked after round 3)

1. **Point-in-time universe** — historical index membership to remove
   survivorship bias; the single biggest credibility gap in round 3.
2. **Real fundamentals ingestion (M3)** — restores the primary CAN SLIM
   discriminator; also unlocks honest 90+ scores.
3. Wider ATR-based stops (Elder 2×ATR, cap 8%) to reduce fixed-cost drag per R.
4. Walk-forward split (tune on 2021-24, validate on 2025-26) before believing
   any tuned number.
5. ~~Mid-cap universe~~ — tested round 3; directionally positive, needs #1 to trust.
6. ~~Trailing exits~~ — tested, rejected (round 2).

*Every conclusion above is reproducible: `python -m stockpilot_api.backtest.run` (single config) or the sweep scripts in the session scratchpad; full trade lists in `sweep5y_results.json`.*
