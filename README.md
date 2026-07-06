# StockPilot

**AI-Powered Swing Trading Operating System for Indian Equities**

A professional, decision-support platform that evaluates NSE stocks against ~200 objective rules derived from respected swing-trading literature (O'Neil, Minervini, Weinstein, Darvas, Elder, Murphy, Nison, Douglas), scores candidates on a 0–100 scale, and surfaces only high-confidence setups for the trader's review.

> **Not** auto-execution. **Not** price prediction. **Not** stock tips.
> **Yes** to consistent, transparent, book-grounded decision support.

---

## Status

🚧 **Pre-implementation** — currently in plan review.

**Current phase**: Documentation & senior review of the build plan.

**Next milestone**: `docs/RULEBOOK.md` — full spec of the ~200-rule engine.

---

## Documentation

- [📋 Build Plan (v1.0)](docs/PLAN.md) — **read this first**
- 📖 Rulebook — *coming next, once plan is approved*
- 🏗️ Architecture — *coming with Month 1*

---

## Vision

Build an AI-assisted professional swing trading operating system that helps identify high-probability swing trades, manage risk systematically, preserve capital, and compound wealth over the long term through disciplined, data-driven decisions.

**Success metric**: quality and consistency of decisions — not guaranteed profit.

---

## Tech Stack (locked)

- **Web**: Next.js 14 + TypeScript + shadcn/ui + Tailwind
- **Data fetching**: TanStack Query (React Query)
- **Backend**: Supabase (Postgres + Auth + Realtime + Edge Functions)
- **Rule engine**: FastAPI (Python 3.11) + pandas + numpy + TA-Lib
- **Market data**: `yfinance` (v1) → Kite Connect (v2)
- **AI**: Anthropic Claude API (news interpretation & trade critique only)
- **Deploy**: Vercel (web) + Fly.io (API) + Supabase Cloud
- **Monorepo**: pnpm workspaces

Full rationale in [`docs/PLAN.md`](docs/PLAN.md#6-tech-stack).

---

## Scope

- **Market**: Indian equities, NSE cash segment
- **Timeframe**: Swing trading (2–20 trading day holds)
- **Universe**: NSE 500 in v1
- **Users**: 1 (personal use)

---

## Repo Structure (planned)

```
stockpilot/
├── apps/
│   ├── web/          # Next.js app
│   └── api/          # FastAPI rule engine
├── packages/
│   ├── ui/           # Reusable UI components
│   ├── types/        # Shared TS types
│   ├── services/     # Data access services
│   └── config/       # Shared configs
├── supabase/         # Migrations, edge functions
└── docs/             # PLAN.md, RULEBOOK.md, ARCHITECTURE.md
```

---

## Roadmap Summary

| Month | Focus |
|---|---|
| 1 | Rulebook + Supabase schema + Next.js scaffold |
| 2 | Data ingestion + Stock Detail page |
| 3 | Rule engine + scoring + watchlists |
| 4 | Trade planning + journal + analytics |
| 5 | Backtester + validation + UI polish |

---

## Risk Disclosure

Even with 200 rules, market risk cannot be eliminated. Every referenced author explicitly states that losing trades are unavoidable — edge comes from probability and discipline over many trades, not certainty on any single trade. The ₹5L → ₹5cr ambition is a direction, not a promise.

---

## License

Private. All rights reserved. Not for redistribution. Not investment advice.
