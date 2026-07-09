# StockPilot — Software Design Document (SDD)

> **AI-Powered Swing Trading *Research* Platform for Indian Equities**
> Decision-support and explainable research. **Not** an auto-trading bot. **Not** a price predictor.

| | |
|---|---|
| **Document type** | Software Design Document (architecture + module + agent design) |
| **Owner** | Rishi Gupta |
| **Status** | Draft for review |
| **Date** | 2026-07-10 |
| **Supersedes** | Extends `docs/PLAN.md` v1.0; this document is the technical architecture PLAN.md §12 reserved |
| **Authoring stance** | Principal SW Architect + AI Architect + Quant Research Engineer + Senior Full-Stack |

---

## 0. How to read this document

- **[FACT]** — verifiable / grounded in your existing code or a real, documented API.
- **[REC]** — my recommendation. You may override.
- **[UNKNOWN]** — something I cannot verify or that needs your decision. Never silently assumed.
- **[ASSUMPTION]** — a default I adopted to keep moving; stated explicitly so you can reject it.

Nothing below claims guaranteed returns. Nothing invents an API capability. Where a source is unofficial or rate-limited, it is labelled as such.

---

## 1. Unknowns & Assumptions Register (read this first)

These are the open items that change the design. I did **not** resolve them silently.

| # | Item | Status | Default adopted | Why it matters |
|---|---|---|---|---|
| U1 | **Frontend framework** — spec says Next.js 15; diagrams say "Flutter Dashboard" | **[UNKNOWN — confirm]** | **[ASSUMPTION]** Next.js 15 web (Flutter mentions treated as stale copy-paste) | Whole frontend + BFF layer depends on this. Next.js also gives us Route Handlers as the backend, which your stack section requires — Flutter would need a *separate* backend. |
| U2 | **`GPT-5.5`** availability, ID, capabilities, pricing | **[UNKNOWN — unverifiable]** | Model-agnostic **LLM Gateway**; model IDs are config | I will not fabricate a model's existence or limits. Swapping models must cost one config change, not a rewrite. |
| U3 | Backend split: **Next.js Route Handlers** (app/business API) **+ Python service** (quant) | **[REC — coherent as written]** | Adopt exactly as specified | Your spec lists both; they are complementary, not conflicting (see §5). |
| U4 | **Where LangGraph runs** — TypeScript (Vercel serverless) vs Python (long-running service) | **[UNKNOWN — decision needed]** | **[REC]** Python LangGraph in the quant service, invoked async | Vercel serverless has execution-time limits unfriendly to multi-agent runs (see §11.4). |
| U5 | Relationship to **existing `stockpilot` FastAPI + Claude code** | **[FACT-based]** | Reuse Python engine as the quant service; re-tier the API | ~60% of the Python already written maps directly onto this design (see §4). |
| U6 | Data source **licensing/ToS** for redistribution (yfinance scraping, NSE/BSE) | **[UNKNOWN — legal]** | Personal, single-user, non-redistributed use only | yfinance & raw NSE/BSE endpoints are unofficial; commercial/multi-user use may violate ToS. |
| U7 | Real-time cadence actually needed | **[REC]** EOD + optional 15-min delayed intraday | Swing horizon (2–20 days) does not require tick data | Avoids cost/complexity with no edge at this timeframe. |

**Decisions I need from you** are consolidated in §17.

---

## 2. Scope

### 2.1 In scope
Indian equities (NSE/BSE cash segment). Swing horizon (2–20 trading-day holds). Single-user MVP, multi-user-ready schema. Explainable research + ranked candidate recommendations + risk-sized trade plans. Manual order placement by the user.

### 2.2 Explicit non-goals [FACT — matches PLAN.md §4]
- ❌ Auto-execution / order routing
- ❌ Price prediction / return guarantees
- ❌ Options, F&O, intraday scalping
- ❌ AI used where deterministic math is correct (indicators, sizing, risk, backtest)
- ❌ Storing broker credentials in MVP

### 2.3 Quality attributes (ranked)
1. **Capital preservation** (risk rules are hard gates, not suggestions)
2. **Explainability** (every recommendation shows its evidence)
3. **Reproducibility** (same inputs + same code version → same output)
4. **Testability** (deterministic core is unit-tested; AI is contract-tested)
5. **Modularity / scalability**
6. Latency (secondary — EOD workload)

---

## 3. Guiding Architectural Principles

| Principle | Concrete application in this system |
|---|---|
| **Clean Architecture** | Dependencies point inward: `domain` (entities, no framework) ← `application` (use-cases/services) ← `infrastructure` (Supabase, HTTP, LLM, market data) ← `interface` (Route Handlers, UI). LLM/DB/broker are *plugins* behind ports. |
| **DDD** | Bounded contexts = the module groups in §6 (Market Data, Research, Portfolio & Risk, Journaling, Analytics). Each owns its entities and language. |
| **SOLID** | Every agent and every data provider implements an interface (`ILlmClient`, `IMarketDataProvider`, `IRepository<T>`). New provider = new implementation, zero edits to callers (O/D). |
| **Repository Pattern** | All persistence behind `I<Entity>Repository`. Supabase is one implementation; tests use in-memory fakes. |
| **Service Layer** | Business logic lives in application services, never in Route Handlers and never in React components. |
| **Feature-based folders** | Code grouped by capability (`features/technical`, `features/risk`), not by type (`controllers/`, `models/`). |
| **Strong typing end-to-end** | Postgres → generated TS types → Zod schemas at every boundary → typed hooks. Python side uses Pydantic for the same contract. |
| **No duplicated logic / no business logic in UI** | One source of truth per rule. UI renders state; hooks fetch; services decide. |
| **Determinism first** | AI is invoked *only* for genuine natural-language reasoning (§7). |

---

## 4. Relationship to the Existing Codebase [FACT]

Your repo already contains a working Python engine. This design **re-tiers** it rather than discarding it.

| Existing asset | Fate under this design |
|---|---|
| `apps/api` FastAPI: `engine/` (10 modules), `patterns/` (8), `indicators/`, `scoring/`, `ingestion/yfinance_sync.py` | **Becomes the Python Quant Service** (§5, tier 4). ~60% reusable as-is. This is the deterministic core — keep it. |
| `agents/master.py`, `agents/technical.py`, `agents/base.py`, `agents/prompts/*` | **Refactored into LangGraph nodes** (§10). Prompts and schemas largely survive; orchestration is replaced by LangGraph. |
| `llm/client.py`, `llm/config.py` | **Becomes the LLM Gateway** (§7.3) — generalized to multi-provider (Claude + [U2] GPT-5.5). |
| `mcp/` technical tools | Reused as **agent tools** (LangGraph tool nodes) or exposed to the Route Handler tier. |
| `apps/web` Next.js pages (Portfolio/Journal/Watchlist/Stock Detail) | **Kept and extended** to Next.js 15 App Router + the module set in §6. |
| Supabase migrations (13 tables) | **Extended** per §8 (add sentiment, macro, sector, backtest, agent-run, evidence tables). |
| `docs/PLAN.md`, `docs/RULEBOOK.md` | Remain authoritative for *rule definitions*; this doc is authoritative for *architecture*. |

**Net change:** we add a **Next.js Route Handler API/BFF tier** and a **LangGraph orchestrator**; the Python engine you already wrote becomes a called-not-calling quant microservice.

---

## 5. High-Level Architecture

Reconciled from your three diagrams. Frontend = Next.js per [U1]. Backend = Next.js Route Handlers per spec. Heavy math = Python service. Orchestration = LangGraph per [U4].

```
┌──────────────────────────────────────────────────────────────────────┐
│ TIER 1 — CLIENT                                                        │
│ Next.js 15 (App Router) · TypeScript · Tailwind · shadcn/ui            │
│ Dashboard · Stock Detail · Watchlist · Portfolio · Journal · Backtest  │
│ Supabase Realtime subscription (alerts, run status)                    │
└───────────────┬────────────────────────────────────────────────────────┘
                │ HTTPS (typed fetch via TanStack Query)
┌───────────────▼────────────────────────────────────────────────────────┐
│ TIER 2 — API / BFF   (Next.js Route Handlers, on Vercel)               │
│ Auth guard (Supabase Auth/JWT) · input validation (Zod) · rate limit   │
│ Application services (use-cases) · Repository interfaces               │
│ Orchestrates: DB reads/writes, enqueue research runs, read results     │
│ NO heavy compute here (serverless time limits) — delegates down        │
└───────┬───────────────────────────┬───────────────────────────┬────────┘
        │ SQL/RPC (RLS)             │ enqueue / status          │ read
┌───────▼─────────┐    ┌────────────▼────────────┐    ┌─────────▼─────────┐
│ TIER 3 — DATA   │    │ TIER 5 — ORCHESTRATION  │    │  (results tables) │
│ Supabase        │    │ LangGraph (Python) [U4] │    └───────────────────┘
│ Postgres + RLS  │◄───┤ Research run = a graph  │
│ Auth · Realtime │    │ of agent nodes (§10)    │
│ Storage         │    │ Chief Analyst synthesis │
│ Redis (optional)│    └───────┬─────────────────┘
└───────▲─────────┘            │ calls (tools)
        │                ┌──────▼───────────────────────────────────────┐
        │                │ TIER 4 — PYTHON QUANT SERVICE (deterministic) │
        │                │ indicators · patterns · features · scoring    │
        │                │ risk/position sizing · backtester · validation│
        │  writes ◄──────┤ ingestion (Yahoo/FMP/NSE/BSE/News) [U6]       │
        │                └──────┬────────────────────────────────────────┘
        │                       │ fetch
┌───────┴───────────────────────▼────────────────────────────────────────┐
│ EXTERNAL DATA (§9) — Yahoo · FMP · NewsAPI · NSE · BSE · (prod) Zerodha  │
└──────────────────────────────────────────────────────────────────────────┘
                       ┌──────────────────────────┐
                       │ TIER 6 — LLM GATEWAY (§7) │
                       │ Claude · GPT-5.5 [U2]     │  ← used only by Tier 5
                       └──────────────────────────┘
```

**Request lifecycle — "research NSE candidate X":**
1. Client → Route Handler `POST /api/research/run` (auth + Zod validated).
2. Handler writes a `research_run` row (`status=queued`) and enqueues it (Redis queue or Supabase table poll). Returns `runId` immediately (async — no serverless timeout).
3. LangGraph orchestrator (Tier 5) picks up the run, calls the Python quant service (Tier 4, deterministic) for indicators/patterns/scores, calls agents (Tier 5+6) only for NL reasoning, writes structured evidence + final recommendation to Postgres.
4. Client subscribes via Supabase Realtime → sees `status` transitions and the final explainable report.

---

## 6. System Modules (24)

Each module: **responsibility · determinism · primary data · key interfaces**. "Determinism" is the load-bearing column — it enforces *"never use AI where deterministic code is more reliable."*

### 6.1 Data & Feature contexts

| Module | Responsibility | Determinism | Primary data | Interface |
|---|---|---|---|---|
| **1. Market Data** | Ingest OHLCV + corporate actions for the universe | 100% deterministic | Yahoo/FMP/NSE/BSE (§9) | `IMarketDataProvider.getOHLCV(ticker, range)` |
| **2. Data Validation** | Reject/flag bad bars (gaps, splits, zero-volume, outliers, stale) | 100% deterministic | raw ingested data | `validate(bars) → {clean, quarantined, report}` |
| **3. Feature Engineering** | Compute indicators + derived features (RS, ADV, ATR-normalized moves) | 100% deterministic | validated OHLCV | Python quant service |
| **4. Historical Storage** | Point-in-time OHLCV, fundamentals, features (no look-ahead) | 100% deterministic | Postgres | `stock_prices`, `technical_indicators`, `features` |
| **5. Realtime Storage** | Latest snapshot + intraday (if enabled), TTL cache | 100% deterministic | Redis/Postgres | `getLatest(ticker)` |

### 6.2 Analysis contexts (deterministic compute + optional AI reasoning on top)

| Module | Responsibility | Determinism | Notes |
|---|---|---|---|
| **6. Fundamental Analysis** | CAN SLIM metrics, growth, margins, debt | **Metrics deterministic**; AI only to *read* annual reports/MD&A | AI = Claude for long docs [U2] |
| **7. Technical Analysis** | Trend template, MAs, S/R, indicator states | 100% deterministic | Your existing modules 4–7 |
| **8. Pattern Recognition** | VCP, Cup&Handle, Flat Base, Bull Flag, Darvas, Ascending Triangle, Stage-2, EMA pullback | 100% deterministic geometry | Your existing `patterns/` |
| **9. Volume Analysis** | Institutional footprint, dry-up, breakout volume | 100% deterministic | O'Neil/Elder rules |
| **10. News Analysis** | Fetch, dedupe, classify materiality of headlines/filings | Fetch deterministic; **classification = AI** | NewsAPI + filings |
| **11. Sentiment Analysis** | Aggregate directional sentiment with source weighting | **AI scores; aggregation deterministic** | Confidence-weighted |
| **12. Macro Analysis** | Rates/inflation/index regime context | Regime flags deterministic; narrative = AI | RBI/index data [U6] |
| **13. Sector Analysis** | Sector RS, rotation, leadership | 100% deterministic | O'Neil/Murphy |

### 6.3 Decision, risk & portfolio contexts

| Module | Responsibility | Determinism | Notes |
|---|---|---|---|
| **14. Risk Management** | Position size, 2%/6% (Elder), stop distance, R:R, hard gates | **100% deterministic — never AI** | Veto power over Decision Engine |
| **15. Portfolio** | Holdings, exposure, sector concentration, open risk | 100% deterministic | Extends existing Portfolio page |
| **16. Watchlist** | Curated lists, per-list scans | Deterministic | Existing |
| **17. Trading Journal** | Douglas-style reflection, rule-adherence log | Deterministic storage; AI *optional* critique | Existing |
| **18. Decision Engine** | Combine module scores + agent evidence into a ranked, gated recommendation | **Scoring deterministic; synthesis = AI (Chief Analyst)** | §12 |
| **19. Explainability Engine** | Render *why* — which rules passed/failed, evidence chain, confidence | Deterministic assembly; AI writes prose summary | §13 |
| **20. Backtesting** | Walk-forward, point-in-time, costs/slippage, expectancy | **100% deterministic — never AI** | §14 gate for trust |

### 6.4 Platform contexts

| Module | Responsibility | Determinism | Notes |
|---|---|---|---|
| **21. Learning Analytics** | Per-rule / per-setup hit-rate, equity curve, drawdown, calibration of confidence vs realized outcome | 100% deterministic | Feeds rule tuning; **no auto-retraining in MVP** |
| **22. Alerts** | Threshold + event alerts via Supabase Realtime (in-app) | Deterministic triggers | PLAN.md: in-app only MVP |
| **23. Dashboard** | Today view, candidates, positions, run status | Presentation | Next.js |
| **24. Settings** | Universe, thresholds, risk %, model config, data-source keys | Config store | Drives U2/U7 |

---

## 7. The Determinism Boundary (core principle)

### 7.1 Deterministic (Python quant service — unit-tested, no LLM) [FACT: mostly already built]
RSI, MACD, EMA/SMA, ATR, ADX, relative strength, ADV, volume ratios, all 8 pattern geometries, position sizing, 2%/6% risk math, stop/target/R:R, scoring aggregation, backtest engine, data validation. **These are pure functions of numeric input. An LLM here would only add nondeterminism and error — forbidden.**

### 7.2 AI-appropriate (genuine NL reasoning only)
- Reading annual reports / MD&A / earnings-call transcripts → structured facts (**Claude**, long-context).
- Classifying news materiality and sentiment with rationale.
- Macro/narrative synthesis.
- **Chief Analyst synthesis**: reconcile conflicting deterministic signals into an explained recommendation + confidence.
- Journal trade critique (optional).

### 7.3 LLM Gateway [REC — generalizes existing `llm/client.py`]
```
interface ILlmClient {
  complete(req: { model: ModelId; system: string; messages: Msg[];
                  tools?: ToolDef[]; responseSchema?: JsonSchema;
                  maxTokens: number; temperature: number })
    : Promise<{ content; toolCalls?; usage; stopReason }>
}
```
- **Model IDs are config**, not hardcoded [U2]. Providers: `anthropic` (Claude — already integrated), `openai` (for the "GPT-5.5" slot, **pending verification**).
- Structured output enforced via response schema / tool-forced JSON — never regex-parse free text.
- Every call logged with prompt hash, model, tokens, latency, cost for reproducibility & spend control.

---

## 8. Data Model (Supabase Postgres, RLS on every table)

Extends the 13 tables in PLAN.md §9. **New/changed** tables in **bold**.

| Table | Purpose |
|---|---|
| `users`, `stocks`, `stock_prices`, `company_financials`, `company_news`, `technical_indicators`, `watchlists`, `trade_candidates`, `trades`, `portfolio`, `journal_entries`, `performance_metrics`, `rule_evaluations` | As per PLAN.md §9 |
| **`features`** | Point-in-time engineered features per (ticker, date) — reproducibility |
| **`data_quality_events`** | Validation quarantine log (Module 2) |
| **`sentiment_scores`** | Per (ticker, date, source) AI sentiment + confidence + rationale |
| **`macro_snapshots`** | Regime flags + narrative per date |
| **`sector_strength`** | Sector RS/rotation per date |
| **`research_runs`** | One row per orchestrated run: status, inputs, cost, timings |
| **`agent_outputs`** | Structured JSON output per agent per run (audit + explainability) |
| **`evidence`** | Atomic evidence items linked to a recommendation (the explainability chain) |
| **`recommendations`** | Final gated, ranked recs + confidence + Chief-Analyst prose |
| **`backtest_runs`** / **`backtest_trades`** | Reproducible backtest results |
| **`llm_calls`** | Prompt hash, model, tokens, cost, latency per call |
| **`agent_memory`** | Long-term agent memory (see §10 memory) |

**Reproducibility invariant [REC]:** every `recommendation` references the exact `code_version`, `feature` rows, and `llm_calls` that produced it. Re-running a past date must not see future data (point-in-time joins only).

---

## 9. Data Sources — Facts, Limits, and Honest Caveats

**I am not inventing capabilities.** Verify auth/pricing against each provider's current docs at build time.

| Source | What it gives | Official? | Auth | Cost | Caveats [U6] |
|---|---|---|---|---|---|
| **Yahoo Finance (`yfinance`)** | EOD + delayed intraday OHLCV, some fundamentals | ❌ Unofficial (scrapes) | none | free | No SLA; can break; ~15-min delay; **ToS discourages redistribution**. Already integrated in your repo [FACT]. |
| **Financial Modeling Prep (FMP)** | Fundamentals, statements, ratios, some prices | ✅ Official API | API key | free tier + paid | Free tier rate-limited; verify India coverage/depth. |
| **NewsAPI** | News headlines/articles | ✅ Official | API key | free (dev) / paid | Free tier: delayed, non-commercial, limited history. |
| **NSE** | Indian equity prices, indices, corporate actions | ⚠️ Site/endpoints unofficial for programmatic use | none/session | free | Aggressive rate-limiting/blocking; ToS unclear for automated use. Treat as best-effort. |
| **BSE** | Same for BSE | ⚠️ Same as NSE | none | free | Same caveats. |
| **Zerodha Kite Connect** (production) | Real-time + historical, official | ✅ Official | API key + login (broker acct) | ~₹2,000/mo | The production-grade path. Needs Zerodha account; historical data has usage terms. |
| **RBI** (macro) | Policy rates, inflation references | ✅ Public | none | free | Manual/low-frequency; parse published data. |

**[REC]** MVP: Yahoo (prices) + FMP (fundamentals) + NewsAPI (news), single-user, non-redistributed. Production: migrate prices to **Kite Connect** for reliability and legitimacy. Abstract all of them behind `IMarketDataProvider` / `IFundamentalsProvider` / `INewsProvider` so migration is a config swap.

---

## 10. AI Agents

**Design rule:** an agent exists only where §7.2 reasoning is required. Deterministic modules are **tools** the agents call — they are *not* agents. Orchestration = LangGraph [U4: Python].

### 10.1 Common agent contract
Every agent implements:
```
interface IAgent<In, Out> {
  name: string
  run(input: In, ctx: RunContext): Promise<AgentResult<Out>>
}
type AgentResult<Out> = {
  output: Out                 // validated against a JSON schema
  confidence: number          // 0..1, see §10.14
  evidence: EvidenceItem[]     // atomic, cited — feeds Explainability
  toolCalls: ToolCallLog[]
  usage: { tokens; costUsd; latencyMs }
  status: 'ok' | 'degraded' | 'failed'
}
```

### 10.2 Cross-cutting policies (apply to all agents)

- **Failure handling:** every agent is *fail-soft*. On tool/LLM/schema failure it returns `status: 'degraded'|'failed'` with partial/empty evidence and `confidence: 0`. **A failed non-critical agent never fails the whole run** — the Decision Engine down-weights it and the Explainability Engine records "N/A: agent failed." The **Risk Agent is the exception** — if it cannot produce a valid risk assessment, the candidate is **hard-vetoed** (fail-closed on safety).
- **Retry policy:** transient errors (5xx, timeout, rate-limit) → exponential backoff, max 3 attempts (0.5s, 2s, 8s), jittered. Schema-validation failure → 1 self-repair retry with the validator error appended to the prompt, then fail. Deterministic tool errors → no retry, surface immediately.
- **Confidence scoring:** each agent returns 0..1. It is **not** the LLM "feeling lucky" — it is computed: `confidence = f(data_completeness, signal_agreement, historical_reliability_of_this_signal)`. Calibration is tracked by Learning Analytics (Module 21) against realized outcomes.
- **Memory:**
  - *Short-term (run):* scratchpad in `RunContext`, discarded after the run.
  - *Long-term (`agent_memory`):* durable, per-ticker facts (e.g., "management guidance history", "prior pattern outcomes"). Retrieved at run start, written at run end. **Not** a vector free-for-all — schema'd, cited, expirable.
- **DB access:** agents access data **only through repositories / the quant service**, never raw SQL. Most agents are **read-only** on market/feature tables and **write-only** to `agent_outputs`/`evidence`.

### 10.3 Agent roster

Below, each agent lists: **Purpose · Responsibilities · Inputs · Outputs · Tools · DB · Prompt skeleton · Confidence · notes.** (Failure/retry/memory follow §10.2 unless overridden.)

---

#### A1. Fundamental Agent
- **Purpose:** Turn financial statements + long filings into structured CAN SLIM-relevant facts and a fundamental verdict.
- **Responsibilities:** Pull deterministic ratios from the quant service; read annual report / MD&A (Claude, long-context [U2]) to extract qualitative facts (guidance, risks, one-offs); reconcile.
- **Inputs:** `ticker`, `company_financials`, filing documents (Storage).
- **Outputs:** `{ canslim: {...booleans+values}, growthTrend, marginTrend, debtRisk, qualitativeFlags[], verdict: 'strong'|'neutral'|'weak' }`.
- **Tools:** `quant.fundamentals(ticker)`, `docs.fetchFiling(ticker)`, LLM(Claude).
- **DB:** read `company_financials`, `stocks`; write `agent_outputs`, `evidence`.
- **Prompt skeleton:**
  > *System:* "You are a conservative equity fundamental analyst. Use ONLY the provided figures and document excerpts. Never estimate missing numbers. Return JSON matching the schema. Cite the source line for every qualitative claim."
  > *User:* `{deterministic_ratios}` + `{filing_excerpts}` + `{schema}`
- **Confidence:** `f(statements_completeness, filing_availability, YoY consistency)`.

#### A2. Technical Agent
- **Purpose:** Interpret the deterministic technical state into a swing-relevant technical read.
- **Responsibilities:** Consume indicator/trend-template outputs; identify entry zone, trend stage, momentum posture. **Computes nothing itself** — the quant service does.
- **Inputs:** `ticker`, `technical_indicators`, trend-template result.
- **Outputs:** `{ trendStage, entryZone, momentum, alignment: {above20/50/200}, technicalVerdict, notes }`.
- **Tools:** `quant.technical(ticker, date)` (deterministic), LLM.
- **DB:** read `technical_indicators`, `stock_prices`; write `agent_outputs`.
- **Prompt skeleton:** *"You are a Minervini/O'Neil-style technician. The numbers below are computed and authoritative — do not recompute. Classify the setup. If data is insufficient, say so."*
- **Confidence:** `f(bars_available, trend-template pass ratio, indicator agreement)`.

#### A3. Pattern Agent
- **Purpose:** Explain and rank detected chart patterns (detection itself is deterministic geometry).
- **Responsibilities:** Take the pattern detector outputs (VCP, C&H, etc.), assess quality/context, flag the highest-conviction setup + trigger/invalidation levels.
- **Inputs:** pattern-detector results + price context.
- **Outputs:** `{ patterns: [{name, quality, trigger, invalidation}], primarySetup }`.
- **Tools:** `quant.detectPatterns(ticker)`, LLM.
- **DB:** read features/prices; write `agent_outputs`.
- **Confidence:** `f(pattern completeness score, volume confirmation)`.

#### A4. Volume Agent
- **Purpose:** Interpret volume behaviour (institutional accumulation/distribution, dry-up, breakout confirmation).
- **Responsibilities:** Consume deterministic volume metrics; narrate footprint; confirm/deny breakouts.
- **Inputs:** volume metrics, ADV, up/down volume.
- **Outputs:** `{ accumulation: bool, dryUp: bool, breakoutConfirmed: bool, verdict }`.
- **Tools:** `quant.volume(ticker)`, LLM. **DB:** read prices; write outputs.
- **Confidence:** `f(ADV sample size, signal clarity)`.

#### A5. News Agent
- **Purpose:** Fetch and classify **materiality** of news/filings for the ticker.
- **Responsibilities:** Dedupe headlines; classify each as material/immaterial + direction + event type (earnings, order win, regulatory, litigation). **Fetch is deterministic; classification is AI.**
- **Inputs:** `ticker`, date window, NewsAPI/filings.
- **Outputs:** `{ items: [{headline, source, materiality, direction, eventType, url}], summary }`.
- **Tools:** `news.fetch(ticker, window)`, LLM. **DB:** read/write `company_news`.
- **Confidence:** `f(source count, source reliability weights, recency)`.

#### A6. Sentiment Agent
- **Purpose:** Aggregate directional sentiment with source weighting.
- **Responsibilities:** Score sentiment per item (AI); **aggregate deterministically** with source-reliability weights; output net sentiment + dispersion.
- **Inputs:** news items (A5 output), optional social (if a real source is added — none assumed).
- **Outputs:** `{ net: -1..1, dispersion, byEvent }`.
- **Tools:** LLM for per-item scoring; deterministic aggregator. **DB:** write `sentiment_scores`.
- **Confidence:** `f(sample size, dispersion)` — high dispersion → low confidence.

#### A7. Sector Rotation Agent
- **Purpose:** Place the stock's sector in the rotation cycle.
- **Responsibilities:** Consume deterministic sector RS; identify leading/lagging sectors; state whether ticker's sector supports a long swing.
- **Inputs:** `sector_strength` table. **Outputs:** `{ sector, rsRank, rotationPhase, supportsLong }`.
- **Tools:** `quant.sectorStrength()`, LLM. **DB:** read `sector_strength`.
- **Confidence:** `f(sector breadth, RS stability)`.

#### A8. Macro / Market-Regime Agent
- **Purpose:** Establish market environment (O'Neil "M"): risk-on/off, index trend, breadth, rate backdrop.
- **Responsibilities:** Deterministic regime flags (index vs MAs, breadth); AI narrative. **Gate:** a bearish regime lowers all long-candidate scores globally.
- **Inputs:** index data, breadth, RBI macro snapshot [U6]. **Outputs:** `{ regime: 'risk-on'|'neutral'|'risk-off', indexTrend, breadth, narrative }`.
- **Tools:** `quant.marketRegime()`, LLM. **DB:** read/write `macro_snapshots`.
- **Confidence:** `f(index data freshness, breadth agreement)`.

#### A9. Portfolio Agent
- **Purpose:** Assess how a candidate fits the *existing* portfolio.
- **Responsibilities:** Check sector concentration, correlation, open-risk headroom, position count vs limits. **Mostly deterministic**, AI only summarizes fit trade-offs.
- **Inputs:** `portfolio`, candidate, risk limits. **Outputs:** `{ fits: bool, concentrationWarnings[], suggestedMaxSize }`.
- **Tools:** `quant.portfolioFit(...)`. **DB:** read `portfolio`, `trades`.
- **Confidence:** deterministic → high unless data missing.

#### A10. Risk Agent **(safety-critical, fail-closed)**
- **Purpose:** Produce the risk-sized trade plan and enforce hard gates.
- **Responsibilities:** Position size from 2% rule; verify 6% portfolio open-risk cap (Elder); compute stop (ATR/structure), targets, R:R (≥1:2, prefer 1:3). **100% deterministic — no LLM in the calculation.** Emits **VETO** if any hard gate fails.
- **Inputs:** entry, ATR, capital, existing open risk. **Outputs:** `{ shares, riskAmount, stop, targets[], rr, gates: {twoPct, sixPct, rrMin, stopValid}, verdict: 'ok'|'veto', reasons[] }`.
- **Tools:** `quant.riskPlan(...)` only. **DB:** read `portfolio`, `settings`.
- **Failure override:** if it cannot compute → **veto** the candidate (never pass unassessed risk).
- **Confidence:** always high (pure math) or veto.

#### A11. Backtesting Agent (on-demand, not per-run)
- **Purpose:** Validate a rule-set/strategy over history and report expectancy.
- **Responsibilities:** Trigger the deterministic backtester; interpret results; **never fabricate metrics.** AI only writes the narrative around real numbers.
- **Inputs:** ruleset, universe, date range, costs. **Outputs:** `{ cagr, winRate, avgRR, maxDD, expectancy, equityCurveRef, perRuleEdge }`.
- **Tools:** `quant.backtest(...)`. **DB:** write `backtest_runs`, `backtest_trades`.
- **Confidence:** `f(trade count, out-of-sample coverage)`.

#### A12. Learning Agent (analytics, **no auto-retrain in MVP**)
- **Purpose:** Surface which rules/setups/agents actually worked, and whether confidence was calibrated.
- **Responsibilities:** Deterministic aggregation over closed trades + recommendations; produce tuning suggestions for **human approval** (never silently changes thresholds).
- **Inputs:** `trades`, `recommendations`, `rule_evaluations`. **Outputs:** `{ perRuleHitRate, confidenceCalibration, suggestedTuning[] }`.
- **Tools:** `quant.learningAnalytics(...)`. **DB:** read all outcome tables; write `performance_metrics`.
- **Confidence:** deterministic.

#### A13. Chief Analyst (synthesis — the "CIO" node)
- **Purpose:** The single reasoning node that **combines all evidence, resolves conflicts, explains, and scores confidence** into one recommendation.
- **Responsibilities:** Take every agent's structured output + the deterministic aggregate score + the Risk verdict; if Risk = veto → recommendation is **"No trade" (hard)**; otherwise synthesize a ranked, explained recommendation with an overall confidence and a written rationale citing evidence IDs.
- **Inputs:** all `agent_outputs`, deterministic score, risk plan. **Outputs:** `{ action: 'watch'|'candidate'|'no-trade', overallScore, confidence, rationale, evidenceRefs[], tradePlanRef }`.
- **Tools:** LLM (the strongest available model [U2]); **read-only** — cannot override Risk veto or recompute numbers.
- **Prompt skeleton:**
  > *System:* "You are the Chief Analyst. You DO NOT compute indicators or prices — those are authoritative inputs. You reconcile conflicting signals, weight by each agent's confidence, and produce an explained recommendation. If the Risk Agent returned VETO, you MUST return action='no-trade'. Never claim certainty. Cite evidence IDs for every claim. Output JSON matching the schema."
  > *User:* `{all_agent_outputs_json}` + `{deterministic_score}` + `{risk_plan}` + `{schema}`
- **Confidence:** weighted aggregate of contributing agents, penalized by signal conflict; **capped** when regime is risk-off or data is incomplete.

---

## 11. Orchestration (LangGraph)

### 11.1 Graph shape (per-ticker research run)
```
        ┌────────────── ingest+validate+features (deterministic, tool) ─────────┐
        ▼                                                                        │
   [Macro/Regime A8]  (global gate; run once per session, cached)               │
        ▼                                                                        │
   ── fan-out (parallel) ──────────────────────────────────────────────────     │
   [Fundamental A1] [Technical A2] [Pattern A3] [Volume A4]                      │
   [News A5→Sentiment A6] [Sector A7] [Portfolio A9]                            │
   ── join ────────────────────────────────────────────────────────────────    │
        ▼                                                                        │
   [Risk Agent A10]  (deterministic; may VETO)                                   │
        ▼                                                                        │
   [Decision & Ranking Engine §12] (deterministic scoring)                       │
        ▼                                                                        │
   [Chief Analyst A13] (synthesis + explanation)                                 │
        ▼                                                                        │
   [Explainability Engine §13] → persist recommendation + evidence              ─┘
```
- **Fan-out is parallel** (independent agents) with a join barrier before Risk.
- **Regime (A8)** runs once and is shared across all tickers in a scan (cheap, avoids N× cost).
- A failed non-critical branch resolves to a `degraded` node result; the join proceeds.

### 11.2 Why LangGraph [REC]
Deterministic control flow (branches, retries, checkpoints), explicit state, resumability after failure, and per-node observability — better than free-form agent-calls-agent for a system that must be reproducible and auditable.

### 11.3 State & checkpointing
Graph state persisted to Postgres (`research_runs` + `agent_outputs`) at each node boundary → a crashed run resumes from the last completed node; a completed run is fully reconstructable for audit.

### 11.4 **[U4] Where it runs — trade-off (decision needed)**
| Option | Pros | Cons |
|---|---|---|
| **A. Python LangGraph in the Quant Service** **[REC]** | Long-running, no serverless timeout; co-located with quant tools; matches your existing Python | Needs a persistent host (Fly.io/Railway/Render), not pure Vercel |
| B. TypeScript LangGraph in Next.js/Vercel | One language, one deploy | Vercel function time limits break multi-agent runs; must offload to background jobs anyway; duplicates quant calls over network |
Recommendation: **A** — orchestrator + quant in one Python service on a persistent host; Next.js Route Handlers enqueue and read results.

---

## 12. Decision & Ranking Engine (deterministic)

- **Input:** per-module scores (0–100), agent confidences, Risk verdict, regime gate.
- **Algorithm:** weighted aggregate (weights from `RULEBOOK.md`) → apply **hard gates** (Risk veto, regime risk-off cap, 18-point checklist must-pass items) → produce `overallScore`, then **rank** candidates within a scan.
- **Determinism requirement:** the score is a pure function; the Chief Analyst *explains* it but **cannot change the number**. This keeps recommendations reproducible and testable.
- **Threshold:** surface candidates ≥ configurable score (PLAN.md uses 90) **and** Risk=ok **and** required checklist items pass.

---

## 13. Explainability Engine

Every recommendation renders a complete, inspectable chain — this is a first-class requirement, not a footnote.

- **What passed / what failed:** per-rule booleans with the cited book (from `rule_evaluations`).
- **Per-module scores** + weights + how they rolled up.
- **Evidence chain:** each `evidence` item links agent → claim → source (a price fact, a filing line, a news URL).
- **Risk plan:** exact sizing math, stop, targets, R:R, which gates passed.
- **AI rationale:** the Chief Analyst prose, with every claim tagged to an evidence ID.
- **Confidence + its drivers** (data completeness, signal agreement, regime).
- **Reproducibility footer:** code version, data as-of date, model IDs, `llm_calls` refs.

**Rule:** if it cannot be explained, it is not shown. No black-box scores.

---

## 14. Backtesting (deterministic — the trust gate)

- **Point-in-time only:** no look-ahead; features as they were known on the bar date.
- **Costs & slippage:** brokerage, STT, slippage modeled and configurable.
- **Metrics:** CAGR, win rate, avg R:R, max drawdown, expectancy after costs, per-rule edge, exposure.
- **Walk-forward:** in-sample tuning, out-of-sample validation reported separately.
- **[FACT/PLAN.md §10]:** *No live capital until backtest shows positive expectancy after costs.* This is the single most important validation before trusting any recommendation.

---

## 15. Folder Structure (feature-based, both stacks)

```
apps/
  web/                         # Next.js 15 App Router (Tier 1 + Tier 2)
    app/
      (dashboard)/ stock/[ticker]/ watchlist/ portfolio/ journal/ backtest/
      api/                     # Route Handlers = BFF (Tier 2)
        research/ portfolio/ watchlist/ journal/ backtest/ alerts/
    features/                  # feature-based, not type-based
      research/ { components, hooks, services, schema.ts }
      portfolio/ risk/ journal/ watchlist/ ...
    lib/ { supabase, query-client, zod }
  quant/                       # Python Quant Service (Tier 4) — evolves apps/api
    domain/                    # entities, value objects (no framework)
    application/               # use-cases / services
    infrastructure/
      market_data/ { yahoo, fmp, nse, bse, kite }   # IMarketDataProvider impls
      persistence/             # repositories (Supabase)
      llm/                     # LLM Gateway (Claude, GPT-5.5 slot [U2])
    features/
      indicators/ patterns/ features_eng/ scoring/ risk/ backtest/ validation/
    orchestration/             # LangGraph graph + agent nodes (Tier 5)
      agents/ { fundamental, technical, pattern, volume, news, sentiment,
                sector, macro, portfolio, risk, backtest, learning, chief }
      graph.py checkpoints.py
packages/
  types/     # shared TS types (generated from Postgres)
  ui/        # shared shadcn components + design tokens
  config/    # eslint, tsconfig, tailwind preset
supabase/
  migrations/  functions/  seed.sql
docs/
  PLAN.md  RULEBOOK.md  ARCHITECTURE.md (this)
```
- **Clean Architecture layering** inside `quant/` (`domain` ← `application` ← `infrastructure`).
- **No business logic** in `app/` components or Route Handlers beyond validation + delegation.

---

## 16. Cross-Cutting Concerns

| Concern | Design |
|---|---|
| **Testing** | Quant core: property + golden-value unit tests (indicators, sizing, backtest). Agents: contract tests with recorded LLM fixtures + schema validation. Route Handlers: integration tests with a test Supabase. **CI must pass before merge.** |
| **Reproducibility** | Point-in-time data, pinned `code_version`, logged `llm_calls`, deterministic scoring. A recommendation is replayable. |
| **Security** | RLS on every table keyed to `auth.uid()`; service-role key server-only; broker/API keys in server env / secret store, never client; no broker credentials in MVP. |
| **Observability** | Per-run trace (LangGraph node timings), per-agent cost/latency, LLM spend dashboard, data-quality events, error alerting. |
| **Cost control** | Regime computed once per scan; Claude only for long docs; response caching keyed by (ticker, as-of, prompt-hash); token budget per run in Settings. |
| **Config** | Universe, thresholds, risk %, model IDs, data-source keys in `settings` + env. Model choice is data, not code [U2]. |
| **Idempotency** | Ingestion upserts on (ticker,date) [FACT: already so]; a re-run for the same (ticker, as-of, code_version) returns the cached recommendation. |

---

## 17. Decisions I Need From You

1. **[U1] Frontend: Next.js or Flutter?** I designed for Next.js. Confirm, or say "Flutter" (then Tier 2 becomes a standalone API and the UI package changes).
2. **[U2] The "GPT-5.5" slot** — do you have confirmed access + the exact model ID? If not, I keep the gateway abstract and default synthesis to Claude (already integrated) until verified.
3. **[U4] Orchestrator host** — approve Python LangGraph on a persistent host (Fly.io/Railway), or require everything on Vercel?
4. **[U6] Usage posture** — confirm this stays **single-user, personal, non-redistributed** (keeps yfinance/NSE/BSE within reasonable bounds). Commercial/multi-user use needs licensed data.
5. **Build order** — do you want me to start implementation, and if so from which module? (My recommendation in §18.)

---

## 18. Recommended Build Order [REC]

Grounded in "validate the edge before trusting it," and reusing what you've built:

1. **Consolidate the Python Quant Service** — fold existing `engine/patterns/indicators/scoring` behind the `IMarketDataProvider` + repository interfaces; add **Data Validation (Module 2)**. *(Mostly refactor of existing code.)*
2. **Backtester (Module 20 / §14)** — the trust gate. Prove expectancy before anything else. *(This is the highest-value missing piece.)*
3. **LLM Gateway + one agent end-to-end** (Technical Agent → Chief Analyst) on a real ticker, with Explainability output.
4. **LangGraph orchestrator** wiring the deterministic modules + Risk veto + Chief Analyst.
5. **Route Handler BFF + Next.js dashboard** surfacing runs, candidates, explainability.
6. Remaining agents (Fundamental/News/Sentiment/Sector/Macro), Learning Analytics, Alerts.

**No live capital until step 2 shows positive post-cost expectancy** — restating PLAN.md §10, because it is the load-bearing safety rule.

---

## 19. Restated Guardrails (non-negotiable)

- No guaranteed returns; recommendations are probabilistic, explained, and risk-gated.
- No AI in deterministic math (indicators, sizing, risk, backtest).
- No invented APIs; unofficial/rate-limited sources labelled as such.
- Risk Agent has veto power and fails closed.
- Every recommendation is explainable and reproducible or it is not shown.

*End of Software Design Document.*
