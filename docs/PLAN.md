# StockPilot — Build Plan v1.0

> **AI-Powered Swing Trading Operating System for Indian Equities (NSE)**

**Document owner**: Rishi Gupta (personal side project)
**Status**: Draft for senior review
**Date**: 2026-07-06
**Version**: 1.0

Items marked `# DECISION NEEDED — confirm` are my sensible defaults. Override any you disagree with.

---

## 1. Executive Summary

StockPilot is a multi-month software engineering effort to build a professional, AI-assisted **swing trading operating system** for Indian equities. It ingests NSE market data, evaluates every candidate stock against ~200 objective rules derived from named swing-trading literature, scores candidates on a 0–100 scale, and surfaces only those crossing a high-confidence threshold for the user's manual review.

The platform is **decision-support**, not auto-execution. Orders are placed manually in Groww (or any broker). The platform's value is in the **quality and consistency of decisions**, not in guaranteed profits.

---

## 2. Vision & Mission

**Vision**: Build an AI-assisted professional swing trading operating system that helps identify high-probability swing trades, manage risk systematically, preserve capital, and compound wealth over the long term through disciplined, data-driven decisions.

**Mission**: Turn the collective wisdom of the most respected swing-trading literature (O'Neil, Minervini, Weinstein, Darvas, Elder, Murphy, Nison, Douglas) into a deterministic, testable, and inspectable rule engine — augmented by AI only where AI genuinely adds value (news interpretation, trade critique).

---

## 3. Success Metrics — What "Done" Means

Success is measured by **decision quality**, not P&L.

| Metric | Target |
|---|---|
| Rule adherence rate | > 90% |
| Journal completeness | 100% (every trade has documented reason, stop, target) |
| Backtest edge on 5 years of NSE data | Positive expectancy after costs |
| Time from candidate identification to trade plan | < 5 minutes |
| Every candidate surfaced explains *why* it scored | 100% (transparency requirement) |

Financial outcomes (win rate, R:R, drawdown) are tracked but treated as consequences, not primary metrics.

---

## 4. Non-Goals (What This Platform Will NOT Do)

- ❌ Auto-execute trades (v1)
- ❌ Predict prices
- ❌ Guarantee returns
- ❌ Give random stock tips
- ❌ Trade options, F&O, or intraday
- ❌ Add any indicator/pattern not traceable to a referenced book
- ❌ Store broker credentials in v1
- ❌ Mobile-native app in v1 (responsive web only)

---

## 5. Scope

- **Market**: Indian equities, NSE cash segment only
- **Universe**: NSE 500 in v1; expandable later
- **Timeframe**: Swing trading — 2 to 20 trading day holds
- **User count**: 1 (personal use). Multi-tenant is v2+.
- **Data cadence**: End-of-day (EOD) OHLCV. Real-time is v2+.

---

## 6. Tech Stack

| Layer | Choice | Confirmed? |
|---|---|---|
| **Frontend framework** | Next.js 14 (App Router) + TypeScript | ✅ locked |
| **UI library** | shadcn/ui + Tailwind CSS + Radix primitives | ✅ locked |
| **Icons** | Lucide | ✅ locked |
| **Data fetching (client)** | **TanStack Query (React Query)** | ✅ locked |
| **Candlestick charts** | TradingView Lightweight Charts | ✅ locked |
| **Analytics charts** | Recharts | `# DECISION NEEDED — confirm (alternatives: Visx, Nivo)` |
| **Backend (data + auth)** | Supabase (Postgres + Auth + Storage + Edge Functions + Realtime) | ✅ locked |
| **Rule engine + backtester** | FastAPI (Python 3.11) + pandas + numpy + TA-Lib | ✅ locked |
| **Market data (v1)** | `yfinance` (Yahoo Finance, `.NS` suffix for NSE) | ✅ locked |
| **AI layer** | Anthropic Claude API | ✅ locked |
| **Package manager (JS)** | pnpm | ✅ locked |
| **Package manager (Python)** | `uv` | `# DECISION NEEDED — confirm (alternative: pip + venv)` |
| **Monorepo tool** | pnpm workspaces (optionally Turborepo later) | ✅ locked |
| **Background jobs** | Supabase Edge Functions + `pg_cron` | ✅ locked |
| **Web hosting** | Vercel | `# DECISION NEEDED — confirm` |
| **API hosting** | Fly.io | `# DECISION NEEDED — confirm (alternative: Railway)` |
| **Database hosting** | Supabase Cloud | ✅ locked |
| **Version control** | GitHub (private: `rishiguptaskn/stockpilot`) | ✅ locked |
| **CI** | GitHub Actions | ✅ locked |

---

## 7. System Architecture

```
                    ┌───────────────────────────────────┐
                    │   Next.js 14 + shadcn/ui (Web)    │
                    │   Dashboard · Journal · Analytics │
                    └────────────────┬──────────────────┘
                                     │
                    ┌────────────────▼──────────────────┐
                    │           Supabase                │
                    │   Postgres · Auth · Realtime      │
                    └────────────────┬──────────────────┘
                                     │
                    ┌────────────────▼──────────────────┐
                    │       FastAPI Rule Engine         │
                    │       (Python 3.11)               │
                    │                                   │
                    │  Data Ingestion (yfinance)        │
                    │  10 Rule Modules (~200 checks)    │
                    │  8 Pattern Detectors              │
                    │  Scoring Aggregator               │
                    │  Backtester                       │
                    └────────────────┬──────────────────┘
                                     │
                    ┌────────────────▼──────────────────┐
                    │       Anthropic Claude API        │
                    │   News interpretation · critique  │
                    └───────────────────────────────────┘
```

Broker (Groww) is **not** integrated. User places orders manually.

---

## 8. Rule Engine — 200 Checks Across 10 Modules

Every rule is:
1. **Objective** — evaluates to a boolean or 0–100 score
2. **Codeable** — deterministic, no LLM guesswork
3. **Traceable** — cites the book/author it derives from

Where a book gives an exact numeric threshold, we use it. Where the reference is ambiguous, the code will contain `# TUNABLE — confirm from source` and use a commonly-cited default until validated via backtest.

| # | Module | Checks | Primary source |
|---|---|---:|---|
| 1 | Market Environment | 15 | O'Neil ("M" in CAN SLIM), Weinstein market stages |
| 2 | Sector Strength | 10 | O'Neil (leading sectors), Murphy (intermarket) |
| 3 | Fundamentals (CAN SLIM) | 25–30 | O'Neil |
| 4 | Technical Analysis | 40 | Murphy + Minervini Trend Template + 18-point checklist |
| 5 | Moving Averages | 20 | Minervini + Weinstein (30-week MA) |
| 6 | Momentum Indicators | 20 | Murphy (RSI = context only, MACD, ADX, ATR) |
| 7 | Volume Analysis | 15 | O'Neil (institutional footprints), Elder |
| 8 | News / Events | 15 | Claude API for interpretation |
| 9 | Risk Management | 25 | Elder (2% per trade, 6% portfolio open risk) |
| 10 | Portfolio Fit | 10 | Portfolio construction principles |
| **Total** | | **~200** | |

### Pattern Detectors (8, no more)

VCP · Cup & Handle · Flat Base · Bull Flag · Darvas Box · Ascending Triangle · Stage 2 Breakout · EMA Pullback

### Indicators Computed (from reference — no more)

20 EMA · 50 SMA · 150 SMA · 200 SMA · Volume · Relative Strength (RS) · Average Daily Volume (ADV) · ATR · RSI (context only)

### Scoring Model

- Each module produces a 0–100 score
- Module scores are weighted (weights defined in `RULEBOOK.md`)
- Aggregate score ≥ 90 → candidate surfaces for user review
- **Every surfaced candidate must show which rules passed, which failed, and per-module scores** (transparency requirement)

### The 18-Point Pre-Buy Checklist (verbatim from reference — must pass all)

1. Overall market bullish
2. Price > 20 EMA
3. Price > 50 SMA
4. Price > 200 SMA
5. 50 SMA > 200 SMA
6. Relative Strength > market
7. Institutional buying visible in volume
8. Daily volume above average
9. Tight consolidation / base
10. Breakout on high volume
11. Positive earnings + revenue growth
12. Sector is leading
13. Strong price momentum
14. Clear stop-loss level
15. R:R ≥ 1:2 (prefer 1:3)
16. Position size fits risk limit
17. No major overhead resistance
18. Predefined exit rules

### Source Books — Every Rule Cites One

| Book | Author | Used For |
|---|---|---|
| How to Make Money in Stocks | William O'Neil | CAN SLIM, market direction, institutional buying |
| Trade Like a Stock Market Wizard | Mark Minervini | Trend Template, VCP, position sizing |
| Think & Trade Like a Champion | Mark Minervini | Entry timing refinements |
| How I Made $2,000,000 in the Stock Market | Nicolas Darvas | Darvas Box detection, momentum |
| Secrets for Profiting in Bull and Bear Markets | Stan Weinstein | 4-Stage classifier, 30-week MA |
| Japanese Candlestick Charting Techniques | Steve Nison | Entry-candle confirmation |
| Technical Analysis of the Financial Markets | John Murphy | Trend, S/R, chart patterns, indicators |
| Trading in the Zone | Mark Douglas | Journal prompts, rule adherence |
| The Disciplined Trader | Mark Douglas | Psychology principles baked into workflow |
| The New Trading for a Living | Alexander Elder | 2%/6% risk rules, stops, journal schema |

**No indicator, pattern, or rule will be added unless traceable to one of these books.**

---

## 9. Database Schema (Supabase Postgres — 13 tables)

| Table | Purpose |
|---|---|
| `users` | Auth (Supabase Auth managed) |
| `stocks` | NSE ticker master list |
| `stock_prices` | Daily OHLCV |
| `company_financials` | Quarterly + annual fundamentals |
| `company_news` | News + earnings announcements |
| `technical_indicators` | Pre-computed daily indicators per stock |
| `watchlists` | User-curated stock lists |
| `trade_candidates` | Stocks passing threshold on a given date |
| `trades` | Executed trades (manually recorded) |
| `portfolio` | Current holdings snapshot |
| `journal_entries` | Per-trade journal (Douglas-style) |
| `performance_metrics` | Aggregated stats |
| `rule_evaluations` | Which rule fired for which stock on which date — critical for auditability |

All tables get **Row Level Security (RLS)** policies keyed to `auth.uid()` so a compromised client can never see another user's data.

---

## 10. Roadmap — 5 Months to v1.0

| Month | Weeks | Deliverables |
|---|---|---|
| **1 — Foundation** | 1–4 | `RULEBOOK.md` (all 200 rules cited) · Supabase schema · Next.js scaffold + shadcn/ui · Auth · Dashboard shell (empty) |
| **2 — Data** | 5–8 | yfinance ingestion · daily OHLCV for NSE 500 · fundamentals ingestion · Stock Detail page with TradingView chart |
| **3 — Rule Engine** | 9–12 | Rule engine (Modules 1–7) · scoring pipeline · Watchlist page · Top 10 Candidates page |
| **4 — Trade Workflow** | 13–16 | Trade planning (position size, stop, targets) · Journal · Analytics · Claude API for news |
| **5 — Validation** | 17–20 | Backtester on 5 years of history · rule threshold tuning · UI polish · paper trading beta |

**No live capital until Month 5 completes with positive backtest expectancy.**

---

## 11. UI/UX Design System

**North star**: the polish and clarity of Linear, Stripe, Vercel, Ramp, Cal.com. Professional-grade dashboard software.

### Design Principles

1. Clarity over decoration
2. Information-dense without being cluttered
3. One primary action per screen
4. Motion with meaning — never distract
5. Every candidate explains itself (why it scored X)
6. Journal is a first-class citizen
7. Keyboard-first for power users
8. Every state is designed — loading, empty, error, offline
9. Consistency > cleverness

### Visual System — sensible defaults, confirm to override

| Aspect | Default | Status |
|---|---|---|
| Typography | Geist Sans (UI) + Geist Mono (numbers/tickers) | `# DECISION NEEDED — confirm` |
| Base font size | 14px | `# DECISION NEEDED — confirm` |
| Color mode | Dark by default, light toggle | `# DECISION NEEDED — confirm` |
| Bullish accent | Tailwind Emerald 500 | `# DECISION NEEDED — confirm` |
| Bearish accent | Tailwind Rose 500 | `# DECISION NEEDED — confirm` |
| Warning accent | Tailwind Amber 500 | `# DECISION NEEDED — confirm` |
| Info accent | Tailwind Blue 500 | `# DECISION NEEDED — confirm` |
| Neutral grays | Tailwind Zinc scale | `# DECISION NEEDED — confirm` |
| Border radius | `rounded-md` (6px) default | `# DECISION NEEDED — confirm` |
| Motion library | Framer Motion | `# DECISION NEEDED — confirm (alternative: none/CSS-only)` |
| Icons | Lucide, 16px body / 20px header, stroke 1.5 | ✅ locked |

### Accessibility (non-negotiable)

- WCAG 2.1 AA color contrast
- Keyboard-reachable interactive elements
- Visible focus rings
- Screen reader labels on icon-only buttons
- `prefers-reduced-motion` respected

### Primary Screens (v1)

1. **Today** — market status, sector heatmap, top candidates, open positions, alerts
2. **Stock Detail** — TradingView chart + rule breakdown card + score card + trade plan generator
3. **Portfolio** — open positions, risk exposure, sector allocation, cash
4. **Journal** — chronological log, filter/search, rule adherence per trade
5. **Analytics** — equity curve, win rate, R:R distribution, drawdown, per-rule performance
6. **Backtest** — configure rule set + date range → run → results + equity curve

### Component Polish Standards

- **Buttons**: 3 sizes × 4 variants (primary/secondary/ghost/destructive)
- **Cards**: consistent padding, hover elevation only on interactive
- **Data tables**: sortable columns, sticky header, keyboard nav, right-aligned numerics, monospace numbers
- **Score badges**: color-mapped (90+ emerald, 75+ amber, <75 rose), number visible
- **Empty states**: icon + one sentence + primary action
- **Error states**: what went wrong + retry + link to details
- **Loading**: skeleton screens matching final layout — never spinners on primary content

---

## 12. Repo Structure & Reusable UI Package

**Full monorepo using pnpm workspaces.** `packages/ui` is the reusable component library — shared across the web app and any future frontends.

```
stockpilot/
├── apps/
│   ├── web/                       # Next.js 14 app
│   │   ├── app/                   # App Router pages
│   │   ├── components/            # App-specific compositions only
│   │   └── package.json
│   └── api/                       # FastAPI Python service
│       ├── engine/                # 10 rule modules
│       ├── patterns/              # 8 pattern detectors
│       ├── indicators/            # Technical indicators
│       ├── backtest/              # Backtester
│       ├── ingestion/             # yfinance ingestion
│       └── pyproject.toml
├── packages/
│   ├── ui/                        # ← SHARED reusable components
│   │   ├── src/
│   │   │   ├── components/        # Button, Card, DataTable, ScoreBadge, ...
│   │   │   ├── hooks/             # useStock, usePortfolio, useTopCandidates
│   │   │   ├── lib/               # utils, formatters (₹, %, dates)
│   │   │   ├── styles/            # design tokens, Tailwind preset
│   │   │   └── index.ts
│   │   └── package.json
│   ├── types/                     # Shared TypeScript types
│   ├── services/                  # Data access services (Supabase client)
│   └── config/                    # Shared eslint, prettier, tsconfig, tailwind
├── supabase/
│   ├── migrations/                # SQL schema migrations
│   ├── functions/                 # Edge Functions
│   └── seed.sql
├── docs/
│   ├── PLAN.md
│   ├── RULEBOOK.md                # ← Week 1 deliverable
│   └── ARCHITECTURE.md
├── .github/
│   └── workflows/                 # CI
├── pnpm-workspace.yaml
├── package.json
└── README.md
```

**Why this structure**:
- Every UI component imported from `@stockpilot/ui` — one source of truth
- Design tokens live in `packages/ui/styles` — change once, updates everywhere
- Types shared across all TypeScript via `@stockpilot/types`
- Services layer testable in isolation
- FastAPI stays a separate deployable — clean language boundary

---

## 13. Data Flow Architecture (Hook → Service → RPC → Supabase)

**Every data interaction in the web app follows the same 4-layer pattern.**

```
┌──────────────────────────────────────────────┐
│  UI Component                                 │
└────────────────┬─────────────────────────────┘
                 │ uses
┌────────────────▼─────────────────────────────┐
│  Custom Hook  ── packages/ui/src/hooks/       │
│  TanStack Query wrapper                       │
│  e.g. useTopCandidates(date)                  │
└────────────────┬─────────────────────────────┘
                 │ calls
┌────────────────▼─────────────────────────────┐
│  Service  ── packages/services/               │
│  Pure TS, no React                            │
│  e.g. candidatesService.getTopByDate(date)    │
└────────────────┬─────────────────────────────┘
                 │ invokes
┌────────────────▼─────────────────────────────┐
│  Supabase RPC / Query                         │
│  e.g. supabase.rpc('get_top_candidates', ..)  │
└────────────────┬─────────────────────────────┘
                 │ hits
┌────────────────▼─────────────────────────────┐
│  Postgres Table + RLS Policy                  │
└──────────────────────────────────────────────┘
```

### Concrete Example — "Show me today's top candidates"

**Layer 1 — Postgres function** (`supabase/migrations/*.sql`):

```sql
create or replace function get_top_candidates(
  p_date date,
  p_min_score int default 90
)
returns setof trade_candidates
language sql stable security definer
as $$
  select *
  from trade_candidates
  where candidate_date = p_date
    and overall_score >= p_min_score
    and user_id = auth.uid()
  order by overall_score desc
  limit 20;
$$;
```

**Layer 2 — Service** (`packages/services/src/candidates.ts`):

```typescript
import { supabase } from './client';
import type { TradeCandidate } from '@stockpilot/types';

export const candidatesService = {
  async getTopByDate(date: Date, minScore = 90): Promise<TradeCandidate[]> {
    const { data, error } = await supabase.rpc('get_top_candidates', {
      p_date: date.toISOString().split('T')[0],
      p_min_score: minScore,
    });
    if (error) throw error;
    return data ?? [];
  },
};
```

**Layer 3 — Hook** (`packages/ui/src/hooks/useTopCandidates.ts`):

```typescript
import { useQuery } from '@tanstack/react-query';
import { candidatesService } from '@stockpilot/services';

export function useTopCandidates(date: Date, minScore = 90) {
  return useQuery({
    queryKey: ['candidates', 'top', date.toISOString().slice(0, 10), minScore],
    queryFn: () => candidatesService.getTopByDate(date, minScore),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}
```

**Layer 4 — Component** (`apps/web/app/today/page.tsx`):

```typescript
import { useTopCandidates, CandidatesList, SkeletonCard, ErrorCard, EmptyCard } from '@stockpilot/ui';

export function TodayCandidatesCard() {
  const { data, isLoading, error } = useTopCandidates(new Date());

  if (isLoading) return <SkeletonCard />;
  if (error)     return <ErrorCard error={error} />;
  if (!data?.length) return <EmptyCard message="No candidates today" />;

  return <CandidatesList items={data} />;
}
```

### Why This Pattern

- **Testable in layers** — mock service to test hook; mock RPC to test service
- **Type-safe end to end** — Postgres → generated TS types → services → hooks → components
- **Business logic in Postgres** — fast, portable, secure via RLS
- **TanStack Query handles async plumbing** — caching, deduplication, refetch, offline
- **Zero business logic in components** — components render, hooks fetch, services define how
- **RLS by default** — every table has row-level security policies

---

## 14. What v1 Deliberately Excludes

- Auto-execution (broker API integration)
- Options, futures, F&O
- Intraday scalping timeframes
- Social/community features
- Mobile-native app
- Multi-tenant / multi-user
- Real-time price streaming (EOD is enough for swing)
- Alerts via SMS/email/push (in-app only)

Each becomes a v2+ decision, only if v1 proves an edge.

---

## 15. Risk & Reality Disclosure

- Even with 200 rules, **market risk cannot be eliminated**
- Every referenced author (O'Neil, Minervini, Weinstein, Elder, Douglas) explicitly states losing trades are unavoidable
- Edge comes from probability + discipline over many trades, not certainty on any single trade
- The ₹5 lakh → ₹5 crore ambition is a *direction*, not a promise
- The platform maximizes probability and controls risk; it cannot guarantee returns

---

## 16. Governance & Working Method

**Working method (from Doc 2, adopted verbatim)**:

1. Define requirements (this document)
2. Design the architecture (Section 7)
3. Implement one module at a time
4. Test each module
5. Only then move to the next module

**Forbidden anti-patterns**:

- ❌ Skipping ahead to "cool features" before rulebook is complete
- ❌ Adding indicators/patterns/rules not in the approved list
- ❌ Guessing numeric thresholds — always cite or mark `# TUNABLE — verify source`
- ❌ Committing without tests for numerical logic
- ❌ Using AI for price prediction or entry signals

**Data safety rules**:

- ✅ Every meaningful change is committed to git before moving to the next task
- ✅ Destructive operations (delete, rename, reset) require explicit user confirmation
- ✅ Nothing is deleted without a fresh commit preceding it
- ✅ `.gitignore` excludes secrets, data dumps, and API keys

---

## 17. Immediate Next Steps

### For approval (senior review)

- [ ] Confirm the tech stack (Section 6)
- [ ] Confirm 5-month roadmap (Section 10)
- [ ] Confirm scope (Section 5) and non-goals (Section 4, 14)
- [ ] Confirm books list (Section 8) is complete
- [ ] Review `# DECISION NEEDED` items in Section 6 and Section 11 and confirm/override

### For me (once approved)

- [ ] Install missing local tools (see Appendix A)
- [ ] Push repo to `github.com/rishiguptaskn/stockpilot` (private)
- [ ] Write `docs/RULEBOOK.md` — full spec for all ~200 rules, strictly from reference books
- [ ] Set up Supabase project + write schema migrations
- [ ] Scaffold Next.js app with shadcn/ui inside `apps/web`
- [ ] Scaffold shared packages (`packages/ui`, `packages/types`, `packages/services`)

**No application code will be written until `RULEBOOK.md` is complete and approved.**

---

## Appendix A — Local Environment Prerequisites

Current status of your machine (checked 2026-07-06):

| Tool | Required version | Installed | Action |
|---|---|---|---|
| Node.js | ≥ 20 | ✅ v24.11.0 | None |
| Git | ≥ 2.40 | ✅ 2.45.2 | None |
| pnpm | ≥ 9 | ❌ Not installed | Install: `npm install -g pnpm` |
| Python | 3.11 or 3.12 | ❌ Not installed | Install from python.org (not Microsoft Store) |
| GitHub CLI | ≥ 2.40 | ❌ Not installed | `winget install --id GitHub.cli` |
| Docker Desktop | Latest | ⚠️ Unverified | Needed for Month 5 |

Accounts needed:

- [ ] Supabase account (free tier is sufficient for v1) — https://supabase.com
- [ ] Vercel account (free tier) — https://vercel.com
- [ ] Anthropic API key (Month 4) — https://console.anthropic.com
- [ ] Fly.io or Railway account (Month 3+) — one of the two

---

## Appendix B — Cost Estimate (Monthly, After Setup)

| Item | v1 (first 6 months) | v2+ |
|---|---|---|
| Supabase | ₹0 (free tier) | ₹0–2,000 |
| Vercel | ₹0 (Hobby tier) | ₹0 |
| Fly.io / Railway | ₹0–500 | ₹500–2,000 |
| Anthropic Claude API | ₹500–2,000 (light usage) | ₹2,000–10,000 |
| yfinance data | ₹0 | ₹0 |
| Domain (optional) | ₹800/year | ₹800/year |
| **Total monthly** | **~₹500–2,500** | **~₹2,500–14,000** |

---

## Appendix C — Glossary

- **Swing trading**: Holding stocks for 2–20 trading days
- **CAN SLIM**: O'Neil's 7-criteria stock selection framework
- **VCP (Volatility Contraction Pattern)**: Minervini's setup — shrinking pullbacks on declining volume before breakout
- **Stage 2**: Weinstein's classification for confirmed uptrend above rising 30-week SMA
- **Trend Template**: Minervini's 8-criteria checklist for a stock in a healthy long-term uptrend
- **Relative Strength (RS)**: A stock's performance relative to a benchmark
- **R:R (Risk:Reward)**: (Target − Entry) ÷ (Entry − Stop). Elder recommends ≥ 1:2
- **2% rule**: Elder — never risk more than 2% of trading capital on a single trade
- **6% rule**: Elder — total open risk across all positions ≤ 6% of capital
- **RLS**: Row-Level Security (Postgres) — database-enforced multi-tenancy
- **RPC**: Remote Procedure Call — a Postgres function callable from client via Supabase

---

**End of plan document.**

*Next step: on approval, write `docs/RULEBOOK.md` — the full ~200-rule spec strictly derived from the source books listed in Section 8.*
