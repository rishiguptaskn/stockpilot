-- ============================================================================
-- StockPilot — Agent Runs (audit + cost tracking)
-- Migration 00003
-- ============================================================================
-- One row per AI agent invocation. The Master run is the parent; each specialist
-- (technical, and later news/fundamental/…) is a child linked via parent_run_id.
-- The latest succeeded master run for a (user, ticker, day) IS the report.
-- User-owned + RLS: a user only ever sees their own runs.
-- ============================================================================

create table public.agent_runs (
  id             uuid primary key default uuid_generate_v4(),
  user_id        uuid references auth.users(id) on delete cascade,
  ticker         text references public.stocks(ticker),
  agent_name     text not null,          -- 'master' | 'technical' | ...
  parent_run_id  uuid references public.agent_runs(id) on delete cascade,
  status         text not null default 'running'
                 check (status in ('running', 'succeeded', 'failed', 'partial')),
  model          text not null,          -- 'claude-sonnet-5' | 'claude-opus-4-8'
  input          jsonb not null,         -- {ticker, params}
  output         jsonb,                  -- AgentFinding / ResearchReport
  tool_calls     jsonb,                  -- [{tool, args}]
  input_tokens   int,
  output_tokens  int,
  cost_usd       numeric(10, 6),
  latency_ms     int,
  error          text,
  created_at     timestamptz default now() not null
);

create index idx_agent_runs_user_ticker on public.agent_runs(user_id, ticker, created_at desc);
create index idx_agent_runs_parent       on public.agent_runs(parent_run_id);

alter table public.agent_runs enable row level security;

-- Own rows only. NULL user_id rows (anonymous local-dev runs) are not visible
-- to any authenticated user, which is the intended default-deny behaviour.
create policy "agent_runs_own" on public.agent_runs
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

-- ============================================================================
-- End of migration 00003
-- ============================================================================
