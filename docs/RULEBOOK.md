# StockPilot Rulebook v1.0

> **The complete specification for StockPilot's ~200-rule decision engine.**
> Every rule is objective, codeable, and cites its source book.

**Version**: 1.0 (draft)
**Date**: 2026-07-06
**Status**: For senior review before code implementation
**Companion**: [PLAN.md](PLAN.md)

---

## Legend

- `# TUNABLE — confirm from source` → threshold or parameter that varies between editions/interpretations; use the noted default until backtested
- `# DECISION NEEDED — confirm` → design choice for you to confirm/override
- ⚠️ **HARD GATE** → module or rule that, if failed, rejects the trade regardless of aggregate score

## Source Books (canonical citations)

| Code | Book | Author |
|---|---|---|
| **[O]** | How to Make Money in Stocks | William J. O'Neil |
| **[Mv]** | Trade Like a Stock Market Wizard | Mark Minervini |
| **[Mv2]** | Think & Trade Like a Champion | Mark Minervini |
| **[D]** | How I Made $2,000,000 in the Stock Market | Nicolas Darvas |
| **[W]** | Secrets for Profiting in Bull and Bear Markets | Stan Weinstein |
| **[N]** | Japanese Candlestick Charting Techniques | Steve Nison |
| **[Mu]** | Technical Analysis of the Financial Markets | John Murphy |
| **[Dg]** | Trading in the Zone / The Disciplined Trader | Mark Douglas |
| **[E]** | The New Trading for a Living | Alexander Elder |

Rules are cited with the code in brackets (e.g., `[O]`, `[Mv]`). No rule without a citation.

---

## Rule Format

Every rule follows this shape:

```
### Mx.y — Short name
- Source: [Code] rationale
- Test: pseudocode / formula
- Pass: condition returning true/false OR 0-100 sub-score
- Weight: contribution to module score (0-100 within module)
```

Aggregate score = weighted average of module scores. Module weights are in Section "Scoring Aggregation" below.

---

## Global Constants

Defined once, referenced by many rules.

```
CAPITAL_INR              = 500000                    # user configurable
RISK_PER_TRADE_PCT       = 2.0                       # [E]  Elder 2% rule
MAX_PORTFOLIO_OPEN_RISK  = 6.0                       # [E]  Elder 6% rule
MAX_OPEN_POSITIONS       = 5                         # # DECISION NEEDED — confirm
DEFAULT_STOP_ATR_MULT    = 2.0                       # # TUNABLE — confirm from source
DEFAULT_STOP_PCT         = 7.0                       # [O]  O'Neil recommends 7-8% max
MIN_RR_RATIO             = 2.0                       # [O][E]  Elder ≥ 1:2, O'Neil ≥ 3:1
PREFERRED_RR_RATIO       = 3.0                       # [O]
NIFTY_BENCHMARK          = "NIFTY 50"
```

---

# MODULE 1 — Market Environment ⚠️ HARD GATE

**Weight in aggregate**: 15/100
**Rules**: 15
**Rationale [O]**: "Three out of four stocks follow the general market direction." Buying against a downtrending market has poor expectancy regardless of how strong the stock looks.

### M1.1 — Nifty 50 above 200 SMA
- Source: [O] "M" in CAN SLIM; [W] Stage 2 characteristic
- Test: `NIFTY.close > NIFTY.sma(200)`
- Pass: boolean
- Weight: 10

### M1.2 — Nifty 50 above 50 SMA
- Source: [O] short-term confirmation of "M"
- Test: `NIFTY.close > NIFTY.sma(50)`
- Pass: boolean
- Weight: 8

### M1.3 — Nifty 50's 50 SMA above its 200 SMA
- Source: [O] golden-cross confirmed state
- Test: `NIFTY.sma(50) > NIFTY.sma(200)`
- Pass: boolean
- Weight: 8

### M1.4 — Nifty 50's 200 SMA sloping up
- Source: [W] Stage 2 requires rising long-term MA; [Mv] Trend Template
- Test: `NIFTY.sma(200)[today] > NIFTY.sma(200)[30 days ago]`
- Pass: boolean
- Weight: 8

### M1.5 — Market not in confirmed correction (distribution days)
- Source: [O] Investor's Business Daily / O'Neil methodology — 5+ distribution days in 4 weeks = caution
- Test: `count(NIFTY distribution days in last 20 sessions) < 5`
  where distribution day = close down > 0.2% on higher volume than prior day
- Pass: boolean
- Weight: 10

### M1.6 — Market breadth positive (advance/decline)
- Source: [Mu] intermarket; [O] confirming breadth
- Test: `NSE.advance_count > NSE.decline_count` for latest session
- Pass: boolean
- Weight: 6

### M1.7 — India VIX not spiking
- Source: general risk management principle; [E] volatility-based sizing
- Test: `INDIAVIX.close < 20` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M1.8 — Nifty 50 not near 52-week low
- Source: [Mv] Trend Template requires stock ≥30% above 52w-low; applied to broad market as confirmation
- Test: `NIFTY.close > NIFTY.min(252) * 1.15` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M1.9 — Nifty Midcap 100 in uptrend
- Source: [Mu] market breadth via mid-cap participation
- Test: `NIFTYMIDCAP.close > NIFTYMIDCAP.sma(200)`
- Pass: boolean
- Weight: 5

### M1.10 — Nifty Smallcap 100 in uptrend
- Source: [Mu] breadth; risk-on confirmation
- Test: `NIFTYSMALL.close > NIFTYSMALL.sma(200)`
- Pass: boolean
- Weight: 4

### M1.11 — No confirmed follow-through day required in last 4 weeks (bull market)
- Source: [O] follow-through day methodology
- Test: `days_since_last_follow_through <= 28`
  follow-through day = index up ≥1.7% on higher volume between 4-10 days after low
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 6

### M1.12 — USD/INR not aggressively depreciating
- Source: [Mu] intermarket — currency weakness affects FII flows
- Test: `USDINR pct_change(20d) < 2.0%` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M1.13 — 10-year G-Sec yield not spiking
- Source: [Mu] intermarket — rising rates pressure equity multiples
- Test: `IN10Y_YIELD.change(20d) < 50 bps` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M1.14 — FII net flows positive over trailing 10 sessions
- Source: [O] institutional participation is core to "I"
- Test: `sum(FII_net_equity, last 10 sessions) > 0`
- Pass: boolean
- Weight: 8

### M1.15 — DII net flows positive over trailing 10 sessions
- Source: complements M1.14; domestic institutional support
- Test: `sum(DII_net_equity, last 10 sessions) > 0`
- Pass: boolean
- Weight: 8

**Module 1 Hard Gate**: if M1.1, M1.4, M1.5 all fail → reject trade regardless of aggregate score.

---

# MODULE 2 — Sector Strength

**Weight in aggregate**: 10/100
**Rules**: 10
**Rationale [O]**: "The right stock in the wrong industry group won't work." Leading stocks come from leading groups.

### M2.1 — Stock's sector index above its 50 SMA
- Source: [O] leading sectors
- Test: `sector_index.close > sector_index.sma(50)`
- Pass: boolean
- Weight: 12

### M2.2 — Stock's sector index above its 200 SMA
- Source: [W] Stage 2 applied to sector
- Test: `sector_index.close > sector_index.sma(200)`
- Pass: boolean
- Weight: 12

### M2.3 — Sector outperforming Nifty over last 3 months
- Source: [O] "L" in CAN SLIM; [Mv] leaders come from leading groups
- Test: `sector.pct_change(63) > NIFTY.pct_change(63)`
- Pass: boolean
- Weight: 15

### M2.4 — Sector outperforming Nifty over last 1 month
- Source: [O] short-term momentum confirmation
- Test: `sector.pct_change(21) > NIFTY.pct_change(21)`
- Pass: boolean
- Weight: 10

### M2.5 — Sector's Relative Strength rank ≥ 70 (top 30% of sectors)
- Source: [O] RS Rating methodology
- Test: `rs_rank(sector, all_sectors, 252) >= 70`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 15

### M2.6 — Sector not in top-of-cycle euphoria (parabolic move)
- Source: [W] Stage 3 warning
- Test: `sector.pct_change(63) < 40%` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M2.7 — Sector 50 SMA sloping up
- Source: [W] rising sector trend
- Test: `sector.sma(50)[today] > sector.sma(50)[10 days ago]`
- Pass: boolean
- Weight: 10

### M2.8 — Multiple stocks in sector making new highs
- Source: [O] "themes come in groups"
- Test: `count(stocks in sector at 52w-high in last 5 days) >= 3` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M2.9 — Sector's ADX above 20 (trending, not choppy)
- Source: [Mu] ADX < 20 = non-trending market
- Test: `sector.adx(14) >= 20`
- Pass: boolean
- Weight: 5

### M2.10 — Sector not the worst-performing over trailing 6 months
- Source: [O] avoid sector laggards
- Test: `rs_rank(sector, all_sectors, 126) > 20`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 5

---

# MODULE 3 — Fundamentals (CAN SLIM)

**Weight in aggregate**: 15/100
**Rules**: 28
**Rationale [O]**: CAN SLIM is a 7-letter framework (C, A, N, S, L, I, M). Six of the seven letters concern the individual stock; M (market) is Module 1.

## C — Current quarterly earnings

### M3.C.1 — Current quarter EPS growth ≥ 25% YoY
- Source: [O] the "C" — minimum threshold cited in the book
- Test: `EPS[latest_quarter] / EPS[same_quarter_prior_year] >= 1.25`
- Pass: boolean
- Weight: 10

### M3.C.2 — Ideally, current quarter EPS growth ≥ 40%
- Source: [O] O'Neil's stronger candidates typically show 40%+
- Test: `EPS_yoy_growth >= 0.40`
- Pass: adds bonus points (not required)
- Weight: 5 (bonus)

### M3.C.3 — Earnings growth accelerating vs prior quarter
- Source: [O] acceleration is one of the strongest signals
- Test: `EPS_yoy_growth[Q_latest] > EPS_yoy_growth[Q_prior]`
- Pass: boolean
- Weight: 8

### M3.C.4 — Current quarter revenue growth ≥ 25% YoY
- Source: [O] rising sales confirm earnings quality
- Test: `revenue_yoy_growth >= 0.25` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M3.C.5 — Earnings surprise positive in latest quarter (if consensus available)
- Source: [O] positive surprise sustains institutional buying
- Test: `actual_EPS > consensus_EPS`
- Pass: boolean
- Weight: 5

## A — Annual earnings growth

### M3.A.1 — 3-year annual EPS growth ≥ 25% CAGR
- Source: [O] the "A" — 25% CAGR minimum over multiple years
- Test: `((EPS[TTM] / EPS[3y_ago]) ^ (1/3)) - 1 >= 0.25`
- Pass: boolean
- Weight: 10

### M3.A.2 — Ideally 3-year EPS CAGR ≥ 30%+
- Source: [O] strongest candidates
- Test: `EPS_3y_cagr >= 0.30`
- Pass: bonus
- Weight: 5 (bonus)

### M3.A.3 — ROE ≥ 17% (annual)
- Source: [O] "return on equity of 17% or higher"
- Test: `ROE_annual >= 0.17`
- Pass: boolean
- Weight: 8

### M3.A.4 — No annual loss in last 3 years
- Source: [O] consistency of profitability
- Test: `min(annual_net_income last 3y) > 0`
- Pass: boolean
- Weight: 5

### M3.A.5 — Debt-to-equity within reasonable bounds
- Source: [Mu] balance-sheet quality; [O] excessive debt = fragile
- Test: `DEBT / EQUITY <= 1.0` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

## N — New (products / management / high)

### M3.N.1 — Stock near or at 52-week high
- Source: [O] the "N"; buy strength, not weakness
- Test: `close >= max(high, 252) * 0.95` (within 5% of 52w-high)
- Pass: boolean
- Weight: 10

### M3.N.2 — Stock made a new 52-week high in last 20 sessions
- Source: [O] fresh strength
- Test: `max(close, 20) == max(close, 252)`
- Pass: boolean
- Weight: 8

### M3.N.3 — Company has recent catalyst (new product, contract, management change) in last 90 days
- Source: [O] the "N" — new catalyst
- Test: news scoring (Module 8) — dedicated
- Pass: reference to M8 news score
- Weight: 5 (soft link)

## S — Supply and demand

### M3.S.1 — Float ≤ 100 crore shares (smaller float preferred)
- Source: [O] smaller supply → easier accumulation moves price
- Test: `shares_outstanding <= 1_000_000_000` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M3.S.2 — Promoter holding ≥ 40%
- Source: adaptation of [O] "management ownership" to Indian context
- Test: `promoter_pct >= 40`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 6

### M3.S.3 — Promoter holding not decreasing over last 4 quarters
- Source: [O] insiders selling is a warning
- Test: `promoter_pct[Q_latest] >= promoter_pct[Q_-4]`
- Pass: boolean
- Weight: 7

### M3.S.4 — Recent share buyback (bonus)
- Source: [O] buybacks reduce supply
- Test: `announced_buyback_in_last_180_days == True`
- Pass: bonus
- Weight: 3 (bonus)

### M3.S.5 — No recent large equity dilution (bonus penalty)
- Source: [O] dilution increases supply
- Test: `shares_outstanding_change(365d) < 5%`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 5

## L — Leader

### M3.L.1 — Relative Strength Rating ≥ 80 (top 20% of market)
- Source: [O] the "L" — RS ≥ 80 minimum; [Mv] RS rank ≥ 70 in Trend Template
- Test: `rs_rank(stock, universe, 252) >= 80`
- Pass: boolean
- Weight: 12

### M3.L.2 — Ideally RS ≥ 90
- Source: [O] top leaders
- Test: `rs_rank >= 90`
- Pass: bonus
- Weight: 5 (bonus)

### M3.L.3 — Stock outperforming its sector over trailing 3 months
- Source: [O] leader within a leading group
- Test: `stock.pct_change(63) > sector_index.pct_change(63)`
- Pass: boolean
- Weight: 8

## I — Institutional support

### M3.I.1 — Institutional (FII+DII+MF) holding increased in last quarter
- Source: [O] the "I" — institutional accumulation
- Test: `sum(FII_pct + DII_pct + MF_pct)[Q_latest] > same[Q_-1]`
- Pass: boolean
- Weight: 10

### M3.I.2 — Number of institutional holders increased in last quarter
- Source: [O] more institutions = broader base of support
- Test: `count(institutional_holders)[Q_latest] > count[Q_-1]`
- Pass: boolean
- Weight: 6

### M3.I.3 — At least one high-quality mutual fund holds the stock
- Source: [O] quality of institutions matters, not just count
- Test: `any(mf in top_indian_funds where holds(mf, stock))`
- Pass: boolean `# DECISION NEEDED — confirm list of "top" funds`
- Weight: 4

**Module 3 Hard Gate**: if M3.C.1 fails (current EPS growth < 25%) AND M3.A.1 fails (3y EPS CAGR < 25%) → reject.

---

# MODULE 4 — Technical Analysis

**Weight in aggregate**: 15/100
**Rules**: 40
**Rationale [Mu]**: The chart is the accumulated result of all market participants' decisions. Read the chart before the story.

## The 18-Point Pre-Buy Checklist (Rules M4.1 – M4.18)

Copied verbatim from Doc 1 reference. Every candidate must pass all 18 for full technical score.

### M4.1 — Overall market bullish
- Source: reference to Module 1 aggregate score ≥ 70
- Test: `module_1_score >= 70`
- Pass: boolean
- Weight: 5

### M4.2 — Price > 20 EMA
- Source: [Mv] short-term uptrend
- Test: `close > ema(20)`
- Pass: boolean
- Weight: 4

### M4.3 — Price > 50 SMA
- Source: [Mv] Trend Template #5
- Test: `close > sma(50)`
- Pass: boolean
- Weight: 5

### M4.4 — Price > 200 SMA
- Source: [Mv] Trend Template #1; [W] Stage 2 requirement
- Test: `close > sma(200)`
- Pass: boolean
- Weight: 6

### M4.5 — 50 SMA > 200 SMA
- Source: [Mv] Trend Template #4 (part)
- Test: `sma(50) > sma(200)`
- Pass: boolean
- Weight: 5

### M4.6 — Relative Strength > market (RS rank ≥ 70)
- Source: [Mv] Trend Template #8; [O] the "L"
- Test: `rs_rank(stock, universe, 252) >= 70`
- Pass: boolean
- Weight: 6

### M4.7 — Institutional buying visible in volume
- Source: [O] volume as institutional footprint
- Test: `count(days where close > open AND vol > avg_vol_50 * 1.5, last 20d) >= 3`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 5

### M4.8 — Daily volume above average
- Source: [O] confirmation of interest
- Test: `vol[today] > avg_vol_50`
- Pass: boolean
- Weight: 3

### M4.9 — Tight consolidation / base present
- Source: [O] proper base; [Mv] VCP characteristic
- Test: `(max(high, 20) - min(low, 20)) / close < 0.15` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M4.10 — Breakout on high volume (if entry setup is breakout)
- Source: [O] volume on breakout day should be ≥ 40-50% above 50-day avg
- Test: `vol[breakout_day] >= avg_vol_50 * 1.4`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 8

### M4.11 — Positive earnings + revenue growth (fundamentals module)
- Source: reference to Module 3
- Test: `module_3_score >= 70`
- Pass: boolean
- Weight: 5

### M4.12 — Sector is leading (sector module)
- Source: reference to Module 2
- Test: `module_2_score >= 70`
- Pass: boolean
- Weight: 5

### M4.13 — Strong price momentum
- Source: [Mv] momentum characteristic of Trend Template
- Test: `stock.pct_change(63) >= 20%` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M4.14 — Clear stop-loss level identifiable
- Source: [E] never enter without stop; [O] 7-8% max stop
- Test: `abs(entry - stop) / entry <= 0.08` (stop within 8% of entry)
- Pass: boolean
- Weight: 6

### M4.15 — R:R ≥ 1:2, preferably 1:3
- Source: [O] 3:1 preferred; [E] 2:1 minimum
- Test: `(target - entry) / (entry - stop) >= 2.0`
- Pass: boolean
- Weight: 6

### M4.16 — Position size fits risk limit (risk module)
- Source: [E] 2% rule; reference to Module 9
- Test: `module_9_score >= 90` (risk sizing must fully pass)
- Pass: boolean
- Weight: 6

### M4.17 — No major overhead resistance within reasonable target distance
- Source: [Mu] resistance limits price appreciation
- Test: `count(swing_highs within (entry, target)) == 0`
  where swing_high = local peak in trailing 6 months
- Pass: boolean
- Weight: 4

### M4.18 — Predefined exit rules exist
- Source: [E] every trade has entry AND exit plan
- Test: `stop is defined AND target is defined AND trailing_rule is defined`
- Pass: boolean
- Weight: 4

## Additional Technical Rules (M4.19 – M4.40)

### M4.19 — Higher highs and higher lows over trailing 3 months
- Source: [Mu] definition of an uptrend
- Test: `swing_high(recent) > swing_high(prior) AND swing_low(recent) > swing_low(prior)`
- Pass: boolean
- Weight: 4

### M4.20 — Price above prior swing high (breakout of structure)
- Source: [Mu] trend continuation via structural break
- Test: `close > prior_significant_swing_high`
- Pass: boolean
- Weight: 3

### M4.21 — No lower low in last 20 sessions
- Source: [Mu] uptrend integrity
- Test: `min(low, 20) > min(low, 40)[shifted 20]`
- Pass: boolean
- Weight: 3

### M4.22 — Volatility (ATR%) not excessive
- Source: [Mu] high ATR = wider stops = smaller size
- Test: `atr(14) / close < 0.05` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 3

### M4.23 — No large gap-down in last 5 sessions
- Source: [Mu] gap-down signals distribution
- Test: `min(open/prev_close - 1, last 5) > -0.03`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 3

### M4.24 — Recent close in upper half of the day's range (buying pressure)
- Source: [Mu] intraday closing behavior
- Test: `(close - low) / (high - low) > 0.6` on latest session
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 3

### M4.25 — Latest candle bullish (green)
- Source: [N] entry-day confirmation
- Test: `close > open`
- Pass: boolean
- Weight: 2

### M4.26 — Bullish candlestick pattern on breakout day
- Source: [N] hammer / bullish engulfing / three white soldiers etc.
- Test: `candle_pattern in {hammer, bullish_engulfing, morning_star, ...}`
- Pass: boolean
- Weight: 3

### M4.27 — No bearish reversal pattern in last 3 sessions
- Source: [N] shooting star / bearish engulfing / evening star as warnings
- Test: `candle_pattern NOT in {shooting_star, bearish_engulfing, evening_star, ...}`
- Pass: boolean
- Weight: 3

### M4.28 — Weekly chart also in uptrend (multi-timeframe alignment)
- Source: [Mu] multi-timeframe analysis
- Test: `weekly.close > weekly.sma(30)` (30-week = ~200-day equivalent)
- Pass: boolean
- Weight: 4

### M4.29 — Weekly close above prior week's high (weekly breakout)
- Source: [Mu] weekly-scale momentum
- Test: `close[this_week] > high[last_week]`
- Pass: boolean
- Weight: 3

### M4.30 — Stock ≥ 30% above 52-week low
- Source: [Mv] Trend Template #6
- Test: `close / min(low, 252) - 1 >= 0.30`
- Pass: boolean
- Weight: 4

### M4.31 — Stock within 25% of 52-week high
- Source: [Mv] Trend Template #7
- Test: `close / max(high, 252) >= 0.75`
- Pass: boolean
- Weight: 4

### M4.32 — At least one recognized pattern present (VCP, Cup&Handle, Flat Base, Bull Flag, Darvas Box, Ascending Triangle, Stage 2 Breakout, EMA Pullback)
- Source: reference to Pattern Detectors section
- Test: `any(pattern.detected for pattern in PATTERN_LIST)`
- Pass: boolean
- Weight: 6

### M4.33 — Pattern quality score ≥ 70 (if pattern present)
- Source: [Mv] not all patterns are equal; VCP quality varies
- Test: `best_pattern.quality_score >= 70`
- Pass: boolean
- Weight: 4

### M4.34 — Handle / base depth within acceptable range (12-30% typical)
- Source: [O] cup depth 12-33%; deeper = weaker
- Test: `base_depth in [0.12, 0.33]` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 3

### M4.35 — Handle drift downward on light volume (Cup & Handle specific)
- Source: [O] handle should drift down, not up
- Test: `handle.slope < 0 AND avg(vol in handle) < avg(vol in cup) * 0.8`
- Pass: boolean (conditional on pattern = Cup&Handle) `# TUNABLE — confirm from source`
- Weight: 3

### M4.36 — Prior base preceded by 30%+ prior uptrend (proper base requires prior uptrend)
- Source: [O] a base without prior uptrend is not a proper base
- Test: `pct_change from 6 months before base start to base start >= 0.30`
- Pass: boolean
- Weight: 4

### M4.37 — Not a "late-stage" base (3rd or 4th base in the cycle)
- Source: [O] later bases have lower success rates
- Test: `base_count_since_last_bear_market <= 2` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 3

### M4.38 — Not extended beyond 5% from pivot (if buying breakout)
- Source: [O] don't chase extended breakouts
- Test: `close <= pivot_price * 1.05`
- Pass: boolean
- Weight: 4

### M4.39 — Not near round-number psychological resistance
- Source: [Mu] round numbers act as resistance
- Test: `distance(close, nearest_round_number_100) > 2%` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 2

### M4.40 — Historical volatility not spiking (stable price action leading to setup)
- Source: [Mu][Mv] VCP requires *contracting* volatility
- Test: `stdev(returns, 20) < stdev(returns, 60)`
- Pass: boolean
- Weight: 3

---

# MODULE 5 — Moving Averages

**Weight in aggregate**: 10/100
**Rules**: 20
**Rationale [Mv][W]**: The alignment and slope of multiple moving averages describes the health of the trend more reliably than any single MA.

## Minervini Trend Template (8 checks — the core of this module)

### M5.1 — Trend Template #1: Price above 150 SMA and 200 SMA
- Source: [Mv] TT #1
- Test: `close > sma(150) AND close > sma(200)`
- Pass: boolean
- Weight: 8

### M5.2 — Trend Template #2: 150 SMA above 200 SMA
- Source: [Mv] TT #2
- Test: `sma(150) > sma(200)`
- Pass: boolean
- Weight: 7

### M5.3 — Trend Template #3: 200 SMA sloping up ≥ 1 month
- Source: [Mv] TT #3 — "trending up for at least 1 month, preferably 4-5 months"
- Test: `sma(200)[today] > sma(200)[21 days ago]`
- Pass: boolean
- Weight: 8

### M5.4 — Trend Template #4: 50 SMA above 150 SMA and 200 SMA
- Source: [Mv] TT #4
- Test: `sma(50) > sma(150) AND sma(50) > sma(200)`
- Pass: boolean
- Weight: 7

### M5.5 — Trend Template #5: Price above 50 SMA
- Source: [Mv] TT #5
- Test: `close > sma(50)`
- Pass: boolean
- Weight: 6

### M5.6 — Trend Template #6: Price ≥ 30% above 52-week low
- Source: [Mv] TT #6
- Test: `close / min(low, 252) - 1 >= 0.30`
- Pass: boolean
- Weight: 6

### M5.7 — Trend Template #7: Price within 25% of 52-week high
- Source: [Mv] TT #7
- Test: `close / max(high, 252) >= 0.75`
- Pass: boolean
- Weight: 6

### M5.8 — Trend Template #8: RS rank ≥ 70
- Source: [Mv] TT #8
- Test: `rs_rank(stock, universe, 252) >= 70`
- Pass: boolean
- Weight: 8

## MA Alignment (stacked in trend order)

### M5.9 — 20 EMA > 50 SMA
- Source: [Mv][Mu] short-medium term alignment
- Test: `ema(20) > sma(50)`
- Pass: boolean
- Weight: 4

### M5.10 — 50 SMA > 150 SMA
- Source: [Mv] medium-long alignment
- Test: `sma(50) > sma(150)`
- Pass: boolean
- Weight: 5

### M5.11 — Full stack: price > 20 EMA > 50 SMA > 150 SMA > 200 SMA
- Source: [Mv] "textbook uptrend"
- Test: chain of inequalities
- Pass: boolean
- Weight: 6

## MA Slope

### M5.12 — 50 SMA sloping up over trailing 20 sessions
- Source: [W] rising medium-term MA
- Test: `sma(50)[today] > sma(50)[20 days ago]`
- Pass: boolean
- Weight: 5

### M5.13 — 20 EMA sloping up over trailing 10 sessions
- Source: [Mv] short-term slope
- Test: `ema(20)[today] > ema(20)[10 days ago]`
- Pass: boolean
- Weight: 4

## Distance from MA (avoid overextension)

### M5.14 — Price not more than 25% above 50 SMA (overextension guard)
- Source: [O][Mv] overextended = poor entry
- Test: `close / sma(50) - 1 <= 0.25` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M5.15 — Price not more than 50% above 200 SMA (climax guard)
- Source: [W] Stage 3 warning; parabolic risk
- Test: `close / sma(200) - 1 <= 0.50` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

## Pullback opportunity (EMA support)

### M5.16 — Recent pullback touched 20 EMA and bounced (setup pattern)
- Source: [Mv][Mu] pullback-to-EMA entry
- Test: `min(low, last_10d) <= ema(20) * 1.02 AND close > ema(20)`
- Pass: boolean (conditional on setup = EMA_Pullback) `# TUNABLE — confirm from source`
- Weight: 4

### M5.17 — Recent pullback touched 50 SMA and held (deeper pullback setup)
- Source: [O] proper base can pull back to 50 SMA
- Test: `min(low, last_10d) <= sma(50) * 1.02 AND close > sma(50)`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 3

## Weinstein 30-week (weekly chart)

### M5.18 — Weinstein Stage 2: weekly close above rising 30-week SMA
- Source: [W] Stage 2 definition
- Test: `weekly.close > weekly.sma(30) AND weekly.sma(30) sloping up`
- Pass: boolean
- Weight: 6

### M5.19 — Weekly 30 SMA sloping up ≥ 5 weeks
- Source: [W] confirmed Stage 2
- Test: `weekly.sma(30)[this week] > weekly.sma(30)[5 weeks ago]`
- Pass: boolean
- Weight: 4

### M5.20 — No death cross (50 SMA crossing below 200 SMA) in last 60 sessions
- Source: [Mu] death cross = trend deterioration
- Test: `not any(sma(50) crossed below sma(200) in last 60 sessions)`
- Pass: boolean
- Weight: 4

---

# MODULE 6 — Momentum Indicators

**Weight in aggregate**: 5/100
**Rules**: 20
**Rationale [Mu]**: Momentum indicators confirm price action; they rarely lead it. RSI in particular is **context only**, never a standalone entry signal per plan.

## RSI (context only)

### M6.1 — RSI(14) between 50 and 70 (healthy uptrend zone)
- Source: [Mu] RSI in uptrend usually oscillates 40-80
- Test: `rsi(14) between 50 and 70`
- Pass: boolean
- Weight: 8

### M6.2 — RSI not overbought (> 80) — extension warning
- Source: [Mu] extreme readings warn of pullback
- Test: `rsi(14) < 80`
- Pass: boolean
- Weight: 6

### M6.3 — RSI not oversold coming into breakout (< 30)
- Source: [Mu] breakouts from oversold are often weak
- Test: `rsi(14) >= 30`
- Pass: boolean
- Weight: 4

### M6.4 — No bearish RSI divergence in last 20 sessions
- Source: [Mu] price makes new high but RSI doesn't → weakening
- Test: `not (max(price, 20) at latest AND max(rsi, 20) NOT at latest)`
- Pass: boolean
- Weight: 6

### M6.5 — Bullish RSI divergence (if in pullback pattern)
- Source: [Mu] price makes lower low but RSI doesn't
- Test: `min(price, 20) at latest AND min(rsi, 20) NOT at latest`
- Pass: bonus
- Weight: 4 (bonus)

## MACD

### M6.6 — MACD line above signal line
- Source: [Mu] MACD bullish confirmation
- Test: `macd_line > macd_signal`
- Pass: boolean
- Weight: 6

### M6.7 — MACD histogram positive
- Source: [Mu]
- Test: `macd_hist > 0`
- Pass: boolean
- Weight: 5

### M6.8 — MACD histogram increasing over last 5 sessions
- Source: [Mu] momentum acceleration
- Test: `macd_hist[today] > macd_hist[5 days ago]`
- Pass: boolean
- Weight: 5

### M6.9 — MACD line above zero (long-term momentum positive)
- Source: [Mu]
- Test: `macd_line > 0`
- Pass: boolean
- Weight: 5

### M6.10 — No MACD bearish crossover in last 10 sessions
- Source: [Mu]
- Test: `not any(macd_line crossed below macd_signal in last 10 sessions)`
- Pass: boolean
- Weight: 4

## ADX (trend strength)

### M6.11 — ADX(14) ≥ 20 (trending, not choppy)
- Source: [Mu] ADX < 20 = non-trending
- Test: `adx(14) >= 20`
- Pass: boolean
- Weight: 6

### M6.12 — ADX rising over last 10 sessions
- Source: [Mu] strengthening trend
- Test: `adx(14)[today] > adx(14)[10 days ago]`
- Pass: boolean
- Weight: 4

### M6.13 — +DI above -DI (bullish directional dominance)
- Source: [Mu] DI+ > DI-
- Test: `di_plus(14) > di_minus(14)`
- Pass: boolean
- Weight: 5

### M6.14 — ADX not extreme (>50) — potential exhaustion
- Source: [Mu] very high ADX = potentially over-trended
- Test: `adx(14) < 50` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 3

## ATR (volatility for sizing)

### M6.15 — ATR(14)/close < 5% (normal volatility)
- Source: [Mu] high volatility = wider stops
- Test: `atr(14) / close < 0.05` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M6.16 — ATR contracting during base (VCP characteristic)
- Source: [Mv] contracting volatility precedes breakouts
- Test: `atr(14) < atr(14)[20 days ago]`
- Pass: boolean
- Weight: 4

## Rate of change

### M6.17 — 12-week ROC positive
- Source: [Mu] medium-term momentum
- Test: `close / close[63 days ago] - 1 > 0`
- Pass: boolean
- Weight: 4

### M6.18 — 4-week ROC positive
- Source: [Mu] short-term momentum
- Test: `close / close[21 days ago] - 1 > 0`
- Pass: boolean
- Weight: 3

### M6.19 — 26-week ROC higher than sector's 26-week ROC
- Source: [O] relative strength via ROC
- Test: `stock.roc(126) > sector.roc(126)`
- Pass: boolean
- Weight: 4

### M6.20 — Stochastic %K > %D (short-term momentum confirmation, non-entry)
- Source: [Mu] stochastic — context only
- Test: `stoch_k(14) > stoch_d(14)`
- Pass: boolean
- Weight: 2

---

# MODULE 7 — Volume Analysis

**Weight in aggregate**: 10/100
**Rules**: 15
**Rationale [O][E]**: "Volume is the fingerprint of institutions." Institutions can't buy quietly — their activity shows up in volume. Volume confirms every meaningful price move.

### M7.1 — Average daily rupee turnover ≥ ₹5 crore (liquidity floor)
- Source: [O] avoid illiquid stocks
- Test: `mean(volume * close, 50) >= 50_000_000` `# TUNABLE — confirm from source`
- Pass: boolean ⚠️ **HARD GATE for tradability**
- Weight: 10

### M7.2 — 50-day average volume ≥ 100,000 shares
- Source: [O] minimum liquidity threshold
- Test: `mean(volume, 50) >= 100_000` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

### M7.3 — Volume today ≥ 1.5× 50-day average (if breakout day)
- Source: [O] breakout confirmation — volume ≥ 40-50% above avg
- Test: `volume[today] >= mean(volume, 50) * 1.5`
- Pass: boolean (conditional on setup = breakout) `# TUNABLE — confirm from source`
- Weight: 10

### M7.4 — Up-day volume > down-day volume in trailing 20 sessions (accumulation)
- Source: [O] institutional accumulation footprint
- Test: `sum(vol on up-days, 20) > sum(vol on down-days, 20)`
- Pass: boolean
- Weight: 8

### M7.5 — At least 3 "power" up-days (close +2%, volume ≥ 1.5× avg) in last 20 sessions
- Source: [O] institutional buying signals
- Test: `count(days where close_change > 2% AND vol > avg_vol_50 * 1.5, last 20) >= 3` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M7.6 — Distribution days ≤ 3 in last 20 sessions (stock-level, not market)
- Source: [O] stock distribution days
- Test: `count(days where close_change < -0.2% AND vol > prior_vol, last 20) <= 3` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M7.7 — Volume drying up during base formation (VCP-specific)
- Source: [Mv] VCP characteristic
- Test: `avg(volume, last 10 in base) < avg(volume, base_len - 10)`
- Pass: boolean (conditional on setup = VCP) `# TUNABLE — confirm from source`
- Weight: 6

### M7.8 — OBV (on-balance volume) making new 20-day high
- Source: [Mu] OBV confirmation
- Test: `obv[today] == max(obv, 20)`
- Pass: boolean
- Weight: 5

### M7.9 — OBV trending up over trailing 60 sessions
- Source: [Mu]
- Test: `linreg_slope(obv, 60) > 0`
- Pass: boolean
- Weight: 5

### M7.10 — Volume-weighted average price (VWAP) below current close
- Source: [Mu] closing above VWAP = buyers in control
- Test: `close > vwap(intraday)` `# TUNABLE — confirm from source`
- Pass: boolean (intraday data required — may be optional in v1 EOD-only)
- Weight: 4

### M7.11 — Delivery percentage (delivered qty / total qty) ≥ 40% (Indian NSE-specific)
- Source: NSE-specific — high delivery % = investor buying, not day-trading churn
- Test: `delivery_pct(today) >= 40` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

### M7.12 — Delivery percentage rising over trailing 20 sessions
- Source: NSE-specific — increasing conviction
- Test: `mean(delivery_pct, last 5) > mean(delivery_pct, prior 15)`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 5

### M7.13 — No unusual volume spike accompanied by price decline (churning)
- Source: [O] high-volume down day = distribution
- Test: `not any(day where vol > avg_vol_50 * 2.0 AND close_change < -1%, last 20)`
- Pass: boolean `# TUNABLE — confirm from source`
- Weight: 6

### M7.14 — 20-day average volume ≥ 90% of 50-day average volume (consistent activity)
- Source: [O] sustained interest
- Test: `mean(vol, 20) >= mean(vol, 50) * 0.9`
- Pass: boolean
- Weight: 4

### M7.15 — Volume on latest breakout day ranks in top 10% of last 50 sessions
- Source: [O] breakout distinguishing signal
- Test: `vol[breakout_day] >= percentile(vol, 50, 90)`
- Pass: boolean (conditional on breakout setup)
- Weight: 5

---

# MODULE 8 — News & Events

**Weight in aggregate**: 5/100
**Rules**: 15
**Rationale**: News can invalidate a technically perfect setup. Claude API handles interpretation; deterministic checks handle calendar and rules.

`# DECISION NEEDED — news feed source: (a) NSE announcements + BSE + moneycontrol scraping, (b) paid API like tickertape/screener, (c) both`

### M8.1 — No earnings announcement scheduled within 3 trading days
- Source: [O][E] avoid earnings binary events
- Test: `days_until_next_earnings >= 3` `# TUNABLE — confirm from source`
- Pass: boolean ⚠️ **HARD GATE — earnings uncertainty**
- Weight: 12

### M8.2 — Most recent earnings result was positive (last quarter beat or in-line)
- Source: [O] positive momentum
- Test: `latest_earnings_surprise >= 0`
- Pass: boolean
- Weight: 8

### M8.3 — No negative news events in last 30 days (via Claude interpretation)
- Source: general — negative news undermines setup
- Test: `claude_news_sentiment(30d) >= 0`  (LLM-scored, -1 to +1)
- Pass: boolean
- Weight: 8

### M8.4 — No pending regulatory action or investigation
- Source: general — legal/regulatory overhang
- Test: `claude_check_regulatory_flags() == None`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M8.5 — No pending management churn (CEO/CFO exit) in last 60 days
- Source: [O] management stability
- Test: `not any(management_change in last 60d)` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

### M8.6 — No recent large equity dilution announcement (QIP / preferential issue)
- Source: [O] dilution increases supply
- Test: `not any(equity_dilution_announcement in last 90d)`
- Pass: boolean
- Weight: 6

### M8.7 — No ex-dividend, bonus, split, or rights issue within trade horizon (~20 sessions)
- Source: mechanical price adjustments distort technicals
- Test: `next_corp_action_date > today + 20 business_days`
- Pass: boolean
- Weight: 5

### M8.8 — No major sector-level negative news
- Source: [O] sector news affects all constituents
- Test: `claude_sector_news_sentiment(sector, 14d) >= -0.3`
- Pass: boolean
- Weight: 5

### M8.9 — Positive analyst upgrade / target-price raise in last 60 days (bonus)
- Source: [O] sponsorship signal
- Test: `any(analyst_upgrade_or_target_raise in last 60d)`
- Pass: bonus
- Weight: 3 (bonus)

### M8.10 — No global macro shock in last 5 sessions (VIX spike, credit spread blowout)
- Source: [Mu] intermarket risk
- Test: `INDIAVIX.change(5d) < 20%` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M8.11 — No RBI policy meeting within trade horizon
- Source: India-specific — RBI meetings cause broad volatility
- Test: `next_RBI_meeting_date > today + 20 business_days` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M8.12 — No Union Budget within trade horizon (Jan-Feb only)
- Source: India-specific — Budget causes sector rotation
- Test: `next_budget_date > today + 20 business_days`
- Pass: boolean
- Weight: 4

### M8.13 — No F&O ban / SEBI restrictions on stock
- Source: NSE-specific — F&O ban restricts liquidity
- Test: `stock NOT in nse_fno_ban_list`
- Pass: boolean
- Weight: 6

### M8.14 — Stock not part of GSM / ASM (Graded / Additional Surveillance Measure) list
- Source: NSE-specific — surveillance stocks have restrictions
- Test: `stock NOT in nse_gsm_list AND stock NOT in nse_asm_list`
- Pass: boolean ⚠️ **HARD GATE — regulatory risk**
- Weight: 8

### M8.15 — Corporate governance not flagged (audit qualifications, promoter pledges)
- Source: [O] governance quality
- Test: `promoter_pledge_pct < 20 AND no_recent_audit_qualification` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

---

# MODULE 9 — Risk Management ⚠️ HARD GATE

**Weight in aggregate**: 10/100
**Rules**: 25
**Rationale [E]**: "Risk management is the single most important thing." Every rule in this module can veto an otherwise-perfect trade.

## Elder's 2% Rule (per-trade risk)

### M9.1 — Risk on this trade ≤ 2% of trading capital
- Source: [E] "the 2% rule" — chapter dedicated
- Test: `(entry - stop) * shares <= CAPITAL_INR * 0.02`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 15

### M9.2 — Position size auto-calculated from stop distance
- Source: [E] position size = risk_amount / (entry - stop)
- Test: `shares == floor((CAPITAL_INR * 0.02) / (entry - stop))`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M9.3 — Notional position ≤ 30% of capital in a single stock
- Source: [E] concentration cap
- Test: `entry * shares <= CAPITAL_INR * 0.30` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

## Elder's 6% Rule (portfolio open risk)

### M9.4 — Sum of open risk across all positions ≤ 6% of capital
- Source: [E] the "6% rule"
- Test: `sum((entry - stop) * shares for all open positions) <= CAPITAL_INR * 0.06`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 15

### M9.5 — After adding this trade, open risk still ≤ 6%
- Source: [E]
- Test: `current_open_risk + new_trade_risk <= CAPITAL_INR * 0.06`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M9.6 — No new positions added in the month if previous month lost > 4%
- Source: [E] drawdown-based cooling-off
- Test: `if last_month_pnl_pct < -4: no_new_trades = True` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

## Stop-loss placement

### M9.7 — Stop-loss ≤ 8% below entry (absolute cap)
- Source: [O] 7-8% max stop-loss cited across the book
- Test: `(entry - stop) / entry <= 0.08`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M9.8 — Stop-loss placed below a technical level (swing low, prior base, MA)
- Source: [Mu][Mv] technical stops are structurally meaningful
- Test: `stop <= max(recent_swing_low, sma_50, ema_20 - atr(14))` — some technical anchor
- Pass: boolean
- Weight: 6

### M9.9 — Stop-loss ≥ 1× ATR below entry (not too tight for noise)
- Source: [E][Mv] stops tighter than 1 ATR often triggered by noise
- Test: `(entry - stop) >= atr(14) * 1.0` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M9.10 — Stop-loss ≤ 3× ATR below entry (not too wide)
- Source: [E] over-wide stops = poor R:R
- Test: `(entry - stop) <= atr(14) * 3.0` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

## R:R minimum

### M9.11 — Reward-to-risk ratio ≥ 2:1
- Source: [E][O] minimum acceptable R:R
- Test: `(target - entry) / (entry - stop) >= 2.0`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 12

### M9.12 — Reward-to-risk ratio preferably ≥ 3:1
- Source: [O] 3:1 as O'Neil's preference
- Test: `(target - entry) / (entry - stop) >= 3.0`
- Pass: bonus
- Weight: 6 (bonus)

## Portfolio-level correlation

### M9.13 — Not already holding 3+ stocks in the same sector
- Source: [O] avoid over-concentration in leading sector
- Test: `count(open_positions in stock.sector) < 3` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M9.14 — Stock not highly correlated (>0.85) with any current holding
- Source: [E] correlated positions = concealed leverage
- Test: `max(corr(stock.returns, hold.returns) for hold in open_positions) < 0.85` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

## Drawdown-based trading gates

### M9.15 — Portfolio drawdown from equity peak ≤ 10% (else reduce size 50%)
- Source: [E] drawdown-aware sizing
- Test: `if drawdown_from_peak > 10%: risk_per_trade_pct = 1.0` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

### M9.16 — Portfolio drawdown > 20% → stop trading, review process
- Source: [E] escalation gate
- Test: `if drawdown_from_peak > 20%: trading_halted = True`
- Pass: boolean ⚠️ **HARD GATE — halt trading**
- Weight: 6

### M9.17 — Max 3 losing trades in a row without a review pause
- Source: [E][Dg] emotional/system review after losing streak
- Test: `if consecutive_losses >= 3: force_journal_review = True`
- Pass: boolean
- Weight: 4

## Position lifecycle

### M9.18 — Never add to a losing position (no averaging down)
- Source: [E][O] averaging down = compounding a mistake
- Test: `not (new_add.entry < existing_position.avg_entry AND existing_position in loss)`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M9.19 — Never move stop-loss further from entry (only tighter)
- Source: [E] stops can trail up, never widen
- Test: `stop[new] >= stop[prev]` (for a long position)
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M9.20 — Booked partial profits at 2R (locks in some gain)
- Source: [Mv] partial profit-taking at first target
- Test: `if unrealized_gain >= 2 * initial_risk: consider_partial_exit`
- Pass: advisory (not a gate) `# TUNABLE — confirm from source`
- Weight: 3

### M9.21 — Trail stop to breakeven after 1R gain
- Source: [E][Mv] risk-free trade after 1R
- Test: `if unrealized_gain >= 1 * initial_risk: stop = max(stop, entry)`
- Pass: advisory
- Weight: 4

## Sizing modifiers

### M9.22 — Reduce size to 1% risk if aggregate score is 85-89 (borderline candidate)
- Source: [Mv][E] sizing scaled to conviction
- Test: `if aggregate_score in [85, 90): risk_pct = 1.0` `# TUNABLE — confirm from source`
- Pass: advisory
- Weight: 3

### M9.23 — Skip trade if slippage > 0.5% of entry (thin liquidity)
- Source: [E] execution quality
- Test: `abs(fill_price - intended_entry) / intended_entry <= 0.005` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 4

### M9.24 — Round shares down (never up) to fit risk budget
- Source: [E] never round in a way that exceeds risk
- Test: `shares == floor(risk_amount / (entry - stop))`
- Pass: boolean
- Weight: 3

### M9.25 — Trade rejected if position size < 10 shares (too small to be worth costs)
- Source: [E] costs consume small positions
- Test: `shares >= 10` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 2

**Module 9 Hard Gates**: M9.1, M9.2, M9.4, M9.5, M9.7, M9.11, M9.16, M9.18, M9.19 — any failure = trade rejected.

---

# MODULE 10 — Portfolio Fit

**Weight in aggregate**: 5/100
**Rules**: 10
**Rationale**: A trade that's perfect in isolation may be wrong for *this* portfolio *right now*.

### M10.1 — Total open positions after adding this trade ≤ MAX_OPEN_POSITIONS (default 5)
- Source: [E] cognitive bandwidth; portfolio management
- Test: `count(open_positions) + 1 <= MAX_OPEN_POSITIONS`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 15

### M10.2 — Portfolio cash sufficient for full position + reserve
- Source: [E] never fully invested; keep dry powder
- Test: `available_cash >= (entry * shares) + (CAPITAL_INR * 0.05)`
- Pass: boolean
- Weight: 12

### M10.3 — Sector concentration ≤ 40% after this trade
- Source: [O] sector concentration cap
- Test: `sum(notional in stock.sector after trade) / total_portfolio <= 0.40` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 12

### M10.4 — Single-stock concentration ≤ 30%
- Source: [E]
- Test: `entry * shares / total_portfolio <= 0.30` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 10

### M10.5 — Cash allocation ≥ 20% (never fully invested)
- Source: [E] keep opportunistic cash
- Test: `available_cash / total_portfolio >= 0.20` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 10

### M10.6 — New trade improves portfolio Sharpe-like ratio (or does not degrade it materially)
- Source: portfolio construction principle
- Test: `estimated_sharpe(portfolio + new_trade) >= estimated_sharpe(portfolio) * 0.95`
- Pass: boolean `# DECISION NEEDED — Sharpe estimation model`
- Weight: 8

### M10.7 — No open trade in this same stock currently
- Source: [E] no doubling up
- Test: `stock NOT in currently_open_positions`
- Pass: boolean ⚠️ **HARD GATE**
- Weight: 10

### M10.8 — Not trading same stock within 20 sessions of a prior stop-out
- Source: [E] rebound-trap protection
- Test: `days_since_last_stopout(stock) >= 20 OR days_since_last_stopout(stock) is None` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 6

### M10.9 — Portfolio beta after this trade ≤ 1.3 (not over-concentrated in high-beta)
- Source: portfolio risk shaping
- Test: `weighted_beta(portfolio + new_trade) <= 1.3` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 8

### M10.10 — Diversification across market caps (not all micro-cap or all large-cap)
- Source: portfolio construction
- Test: `count(distinct market_cap_bucket in portfolio) >= 2 after trade` `# TUNABLE — confirm from source`
- Pass: boolean
- Weight: 5

---

# PATTERN DETECTORS

**Eight patterns, no more.** Each is a boolean detector that either fires (pattern present) or doesn't. Rule M4.32 references these.

### P1 — VCP (Volatility Contraction Pattern)
- Source: [Mv]
- Definition: series of 2-6 progressively-shrinking pullbacks on declining volume within an established uptrend, culminating in a tight pivot ready to break out
- Detector logic:
  ```
  1. Stock in uptrend (Trend Template M5.1-M5.8 all pass)
  2. Identify 2-6 pullbacks in the last 3-6 months
  3. Each successive pullback smaller than previous (contraction)
     e.g., pullback depths: 20%, 12%, 8%, 5%
  4. Volume declines during each contraction
  5. Latest range (last 5-10 days) tightest of all
  6. Pivot = high of the last contraction
  ```
- Quality score: contribution to `pattern.quality_score` based on:
  - Number of contractions (3-5 optimal)
  - Depth ratio (each ≤ 50% of prior)
  - Volume decline slope
- `# TUNABLE — confirm from source` for exact contraction depth ratios

### P2 — Cup & Handle
- Source: [O]
- Definition: U-shaped consolidation (cup) followed by a shorter, shallower drift downward (handle), then breakout
- Detector logic:
  ```
  1. Prior uptrend of ≥ 30% (M4.36)
  2. Cup: rounded bottom, depth 12-33% (M4.34)
  3. Cup duration: 7-65 weeks # TUNABLE — confirm from source
  4. Handle: shorter, downward-drifting, depth ≤ half of cup
  5. Handle volume declining (M4.35)
  6. Pivot = high of handle
  ```
- Quality score:
  - Symmetry of cup
  - Handle depth vs cup depth
  - Handle drift direction and volume

### P3 — Flat Base
- Source: [O]
- Definition: sideways consolidation within 15% range after a prior uptrend, minimum 5 weeks
- Detector logic:
  ```
  1. Prior uptrend of ≥ 20%
  2. Sideways range: (max - min) / max <= 15%
  3. Duration: >= 5 weeks (25 sessions)
  4. Volume drying during base
  ```
- Quality score: tightness (lower range = higher quality)

### P4 — Bull Flag
- Source: [Mu]
- Definition: strong pole (rally) followed by tight downward-sloping consolidation (flag), then breakout
- Detector logic:
  ```
  1. Pole: 15-30% rally in 1-4 weeks
  2. Flag: parallel channel drift downward, 3-15 days, depth ≤ 40% of pole
  3. Volume declines in flag
  4. Breakout on volume ≥ 1.5× flag average
  ```
- Quality score: pole slope, flag tightness, volume behavior

### P5 — Darvas Box
- Source: [D]
- Definition: consolidation range formed after a new 52-week high; box top = highest high, box bottom = lowest low that holds; buy on breakout above box top
- Detector logic:
  ```
  1. Stock made a new 52-week high recently (last 60 sessions)
  2. Since that high, price has consolidated in a definable range for at least 3 days
  3. Box top = highest high in range
  4. Box bottom = lowest low since box start that hasn't been broken
  5. Latest close above box top with volume confirmation
  ```
- Quality score: box duration, range tightness

### P6 — Ascending Triangle
- Source: [Mu]
- Definition: flat horizontal resistance at top; rising trendline of higher lows below; breakout above horizontal resistance
- Detector logic:
  ```
  1. Identify 3+ touches of a horizontal resistance (variance ≤ 2%)
  2. Identify 3+ higher lows below (linear regression positive slope)
  3. Duration ≥ 3 weeks
  4. Breakout above resistance with volume ≥ 1.5× avg
  ```
- Quality score: number of touches, slope of lows

### P7 — Stage 2 Breakout
- Source: [W]
- Definition: transition from Stage 1 (base) to Stage 2 (uptrend) — breakout above resistance with 30-week SMA turning up
- Detector logic:
  ```
  1. Stock in Stage 1 for at least 10 weeks (defined by weekly.close within 15% of weekly.sma(30))
  2. Weekly.close breaks above the resistance high of Stage 1
  3. Weekly.sma(30) is flat or turning up
  4. Volume on breakout week ≥ 2× 30-week avg
  ```
- Quality score: Stage 1 duration, 30-week slope, volume ratio

### P8 — EMA Pullback
- Source: [Mv][Mu]
- Definition: within a strong uptrend, price pulls back to touch 10 EMA or 20 EMA, then bounces
- Detector logic:
  ```
  1. Trend Template (M5.1-M5.8) all pass
  2. In last 5-10 days, low touched ema(10) or ema(20)
  3. Latest close back above ema(20)
  4. Volume declines during pullback, then expands on bounce
  ```
- Quality score: precision of touch, bounce candle strength

---

# INDICATORS (formulas, definitions)

Only these are computed. Every rule uses only these — no others.

| Code | Indicator | Formula |
|---|---|---|
| I1 | 20 EMA | Exponential MA, α = 2/(20+1) |
| I2 | 50 SMA | Simple MA of last 50 closes |
| I3 | 150 SMA | Simple MA of last 150 closes |
| I4 | 200 SMA | Simple MA of last 200 closes |
| I5 | 30-week SMA (weekly) | Simple MA of last 30 weekly closes |
| I6 | RSI(14) | Wilder's smoothed 14-period RSI |
| I7 | MACD | 12/26/9 EMA convention |
| I8 | ADX(14) | Wilder's ADX with +DI/-DI |
| I9 | ATR(14) | Wilder's Average True Range |
| I10 | Volume 50-day avg | Simple mean of last 50 volumes |
| I11 | Relative Strength Rank | Percentile rank of stock's 252-day return vs universe |
| I12 | OBV | On-Balance Volume (cumulative) |
| I13 | Stochastic 14,3 | %K and %D per Murphy definitions |

`# TUNABLE — confirm from source` for exact smoothing method (Wilder's vs standard EMA) where applicable per book.

---

# SCORING AGGREGATION

## Module Weights (sum to 100)

| Module | Weight | Hard Gate? |
|---|---:|:---:|
| M1 Market Environment | 15 | ✅ |
| M2 Sector Strength | 10 | |
| M3 Fundamentals (CAN SLIM) | 15 | ✅ (partial) |
| M4 Technical Analysis | 15 | |
| M5 Moving Averages | 10 | |
| M6 Momentum | 5 | |
| M7 Volume | 10 | ✅ (liquidity floor) |
| M8 News/Events | 5 | ✅ (partial) |
| M9 Risk Management | 10 | ✅ |
| M10 Portfolio Fit | 5 | ✅ (partial) |
| **Total** | **100** | |

## Aggregate Score Formula

```
aggregate_score = sum(module_score[i] * module_weight[i] / 100 for i in modules)
```

## Decision Thresholds

| Aggregate Score | Action |
|---|---|
| ≥ 90 | **Candidate** — surface for user review |
| 85 – 89 | **Watch** — track but do not enter unless multiple candidates >90 unavailable |
| 75 – 84 | **Reject** — score visible in journal, not surfaced |
| < 75 | **Filter out** — not shown |

## Hard Gate Precedence

If **any** hard-gate rule fails, `aggregate_score` is set to 0 and the stock is filtered out regardless of other rules. Hard gates are listed under each module.

## Transparency Requirement

For every candidate surfaced to the user:
1. Show the aggregate score
2. Show per-module scores as a bar chart
3. Show the full list of hard gates and their status (all should be passed)
4. Show the top 5 rules that scored highest AND the top 3 rules that came closest to failing
5. Every rule is clickable → shows source book citation + threshold used

---

# GLOBAL VALIDATION CHECKLIST (before adding any new rule)

Before adding, modifying, or removing any rule in this document, verify:

- [ ] Cites a specific book from the approved list (Section "Source Books")
- [ ] Objectively computable from OHLCV + fundamentals + news feed
- [ ] Has a stated pass/fail (boolean) or 0-100 (score) output
- [ ] Has a weight relative to its module (0-100 within module)
- [ ] If threshold is inferred, marked `# TUNABLE — confirm from source`
- [ ] If it's a hard gate, that's explicitly labeled ⚠️
- [ ] Does not duplicate an existing rule (dedup)
- [ ] Can be backtested against 5 years of NSE data

**Any rule that fails these criteria does not enter production.**

---

## Appendix — Rule Count Verification

| Module | Rules |
|---|---:|
| M1 Market Environment | 15 |
| M2 Sector Strength | 10 |
| M3 Fundamentals (CAN SLIM) | 28 |
| M4 Technical Analysis | 40 |
| M5 Moving Averages | 20 |
| M6 Momentum Indicators | 20 |
| M7 Volume Analysis | 15 |
| M8 News & Events | 15 |
| M9 Risk Management | 25 |
| M10 Portfolio Fit | 10 |
| **Total rules** | **198** |
| **Plus 8 pattern detectors** | 8 |
| **Grand total** | **206** |

Meets the ~200-check target from the reference.

---

## Next Steps (once this rulebook is approved)

1. `packages/services` — Postgres schema migrations from Section 9 of PLAN.md
2. `apps/api/engine/` — implement Module 1 (Market Environment) rules first as the reference implementation
3. Unit tests for every rule (input → expected pass/fail)
4. Fixture data for NSE 500 for last 5 years for backtesting
5. Backtest results feed back into `# TUNABLE` items — each threshold gets validated or adjusted

---

**End of RULEBOOK.md v1.0.**

*This document is the source of truth for what rules the engine implements. Application code must match this document. Any behavioral divergence is a bug in code, not in this document.*
