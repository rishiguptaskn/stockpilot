-- ============================================================================
-- StockPilot — Initial Schema
-- Migration 00001
-- ============================================================================
-- Implements the 13-table schema from docs/PLAN.md § 9.
-- Every user-owned table has Row-Level Security (RLS) keyed to auth.uid().
-- Reference data tables (stocks, prices, indicators, news, financials) are
-- readable by any authenticated user but writable only by service_role.
-- ============================================================================

-- Extensions
create extension if not exists "uuid-ossp";

-- ============================================================================
-- 1. profiles  — extends auth.users with StockPilot preferences
-- ============================================================================
create table public.profiles (
  id                       uuid primary key references auth.users(id) on delete cascade,
  full_name                text,
  capital_inr              numeric(15, 2) default 500000 not null,
  risk_per_trade_pct       numeric(4, 2)  default 2.0    not null,
  max_open_positions       int            default 5      not null,
  created_at               timestamptz    default now()  not null,
  updated_at               timestamptz    default now()  not null
);

-- ============================================================================
-- 2. stocks — NSE ticker master list
-- ============================================================================
create table public.stocks (
  ticker      text primary key,               -- e.g. "RELIANCE.NS"
  name        text not null,
  sector      text,
  industry    text,
  exchange    text not null default 'NSE',
  is_active   boolean default true not null,
  created_at  timestamptz default now() not null,
  updated_at  timestamptz default now() not null
);

create index idx_stocks_sector on public.stocks(sector) where is_active = true;

-- ============================================================================
-- 3. stock_prices — Daily OHLCV
-- ============================================================================
create table public.stock_prices (
  id            uuid primary key default uuid_generate_v4(),
  ticker        text not null references public.stocks(ticker),
  date          date not null,
  open          numeric(12, 4) not null,
  high          numeric(12, 4) not null,
  low           numeric(12, 4) not null,
  close         numeric(12, 4) not null,
  volume        bigint         not null,
  delivery_pct  numeric(5, 2),                 -- NSE-specific (nullable)
  unique (ticker, date)
);

create index idx_stock_prices_ticker_date on public.stock_prices(ticker, date desc);

-- ============================================================================
-- 4. company_financials — Quarterly + annual fundamentals
-- ============================================================================
create table public.company_financials (
  id              uuid primary key default uuid_generate_v4(),
  ticker          text not null references public.stocks(ticker),
  period_end      date not null,
  period_type     text not null check (period_type in ('quarterly', 'annual')),
  revenue         numeric(18, 2),
  net_income      numeric(18, 2),
  eps             numeric(10, 4),
  roe             numeric(6, 2),
  debt_to_equity  numeric(6, 2),
  promoter_pct    numeric(6, 2),
  fii_pct         numeric(6, 2),
  dii_pct         numeric(6, 2),
  mf_pct          numeric(6, 2),
  raw_data        jsonb,                       -- raw response from data source
  created_at      timestamptz default now() not null,
  unique (ticker, period_end, period_type)
);

create index idx_financials_ticker_period on public.company_financials(ticker, period_end desc);

-- ============================================================================
-- 5. company_news — News + earnings announcements
-- ============================================================================
create table public.company_news (
  id                uuid primary key default uuid_generate_v4(),
  ticker            text references public.stocks(ticker),   -- nullable if sector-wide
  sector            text,
  headline          text not null,
  body              text,
  source            text,
  url               text,
  published_at      timestamptz not null,
  sentiment_score   numeric(3, 2),   -- -1.00 to 1.00 (from Claude API)
  category          text,            -- earnings, regulatory, mgmt, corp_action, macro
  is_significant    boolean default false,
  created_at        timestamptz default now() not null
);

create index idx_news_ticker_pub on public.company_news(ticker, published_at desc);
create index idx_news_sector_pub on public.company_news(sector, published_at desc) where sector is not null;

-- ============================================================================
-- 6. technical_indicators — Pre-computed daily indicators per stock
-- ============================================================================
create table public.technical_indicators (
  id             uuid primary key default uuid_generate_v4(),
  ticker         text not null references public.stocks(ticker),
  date           date not null,
  ema_20         numeric(12, 4),
  sma_50         numeric(12, 4),
  sma_150        numeric(12, 4),
  sma_200        numeric(12, 4),
  rsi_14         numeric(6, 2),
  atr_14         numeric(12, 4),
  adx_14         numeric(6, 2),
  di_plus_14     numeric(6, 2),
  di_minus_14    numeric(6, 2),
  macd_line      numeric(12, 4),
  macd_signal    numeric(12, 4),
  macd_hist      numeric(12, 4),
  rs_rank        numeric(5, 2),    -- 0-100 percentile vs universe
  volume_avg_50  bigint,
  obv            bigint,
  unique (ticker, date)
);

create index idx_indicators_ticker_date on public.technical_indicators(ticker, date desc);

-- ============================================================================
-- 7. watchlists — User-curated stock lists
-- ============================================================================
create table public.watchlists (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  tickers     text[] not null default '{}',
  created_at  timestamptz default now() not null,
  updated_at  timestamptz default now() not null
);

create index idx_watchlists_user on public.watchlists(user_id);

-- ============================================================================
-- 8. trade_candidates — Stocks passing threshold on a given date
-- ============================================================================
create table public.trade_candidates (
  id                        uuid primary key default uuid_generate_v4(),
  user_id                   uuid not null references auth.users(id) on delete cascade,
  ticker                    text not null references public.stocks(ticker),
  candidate_date            date not null,
  aggregate_score           numeric(5, 2) not null,
  module_scores             jsonb not null,        -- {"M1": 85, "M2": 90, ...}
  hard_gates_all_passed     boolean not null,
  verdict                   text not null check (verdict in ('candidate', 'watch', 'reject')),
  suggested_entry           numeric(12, 4),
  suggested_stop            numeric(12, 4),
  suggested_target          numeric(12, 4),
  suggested_shares          int,
  detected_patterns         text[],                -- ["VCP", "Stage2Breakout"]
  created_at                timestamptz default now() not null,
  unique (user_id, ticker, candidate_date)
);

create index idx_candidates_user_date on public.trade_candidates(user_id, candidate_date desc);
create index idx_candidates_score     on public.trade_candidates(aggregate_score desc);

-- ============================================================================
-- 9. trades — Executed trades (manually recorded by user)
-- ============================================================================
create table public.trades (
  id             uuid primary key default uuid_generate_v4(),
  user_id        uuid not null references auth.users(id) on delete cascade,
  ticker         text not null references public.stocks(ticker),
  candidate_id   uuid references public.trade_candidates(id),
  entry_date     date not null,
  entry_price    numeric(12, 4) not null,
  stop_price     numeric(12, 4) not null,
  target_price   numeric(12, 4),
  shares         int not null check (shares > 0),
  exit_date      date,
  exit_price     numeric(12, 4),
  status         text not null default 'open'
                 check (status in ('open', 'closed_win', 'closed_loss', 'closed_breakeven')),
  created_at     timestamptz default now() not null,
  updated_at     timestamptz default now() not null
);

create index idx_trades_user_status on public.trades(user_id, status);
create index idx_trades_user_date   on public.trades(user_id, entry_date desc);

-- ============================================================================
-- 10. portfolio — Current holdings snapshot
-- ============================================================================
create table public.portfolio (
  id                uuid primary key default uuid_generate_v4(),
  user_id           uuid not null references auth.users(id) on delete cascade,
  ticker            text not null references public.stocks(ticker),
  shares            int not null check (shares > 0),
  avg_entry_price   numeric(12, 4) not null,
  current_stop      numeric(12, 4),
  as_of_date        date not null,
  unique (user_id, ticker, as_of_date)
);

create index idx_portfolio_user_date on public.portfolio(user_id, as_of_date desc);

-- ============================================================================
-- 11. journal_entries — Per-trade journal (Douglas-style)
-- ============================================================================
create table public.journal_entries (
  id                    uuid primary key default uuid_generate_v4(),
  trade_id              uuid not null references public.trades(id) on delete cascade,
  user_id               uuid not null references auth.users(id) on delete cascade,
  entry_reason          text,
  exit_reason           text,
  rule_adherence_pct    numeric(5, 2),   -- 0.00 - 100.00
  lessons               text,
  created_at            timestamptz default now() not null
);

create index idx_journal_trade on public.journal_entries(trade_id);
create index idx_journal_user  on public.journal_entries(user_id);

-- ============================================================================
-- 12. performance_metrics — Aggregated stats over time
-- ============================================================================
create table public.performance_metrics (
  id                  uuid primary key default uuid_generate_v4(),
  user_id             uuid not null references auth.users(id) on delete cascade,
  as_of_date          date not null,
  period_type         text not null check (period_type in ('weekly', 'monthly', 'ytd', 'all_time')),
  trades_count        int not null default 0,
  win_count           int not null default 0,
  loss_count          int not null default 0,
  total_pnl           numeric(15, 2) not null default 0,
  avg_win             numeric(12, 4),
  avg_loss            numeric(12, 4),
  max_drawdown_pct    numeric(5, 2),
  profit_factor       numeric(6, 2),
  unique (user_id, as_of_date, period_type)
);

create index idx_performance_user_date on public.performance_metrics(user_id, as_of_date desc);

-- ============================================================================
-- 13. rule_evaluations — Audit log: which rule fired for which stock, when
-- ============================================================================
create table public.rule_evaluations (
  id                uuid primary key default uuid_generate_v4(),
  candidate_id      uuid not null references public.trade_candidates(id) on delete cascade,
  ticker            text not null,
  rule_id           text not null,      -- e.g. "M1.1", "M4.18", "P1"
  module_id         text not null,      -- "M1" .. "M10", "P"
  passed            boolean not null,
  score             numeric(6, 2),
  actual_value      text,
  threshold         text,
  is_hard_gate      boolean not null default false,
  source_citation   text,               -- e.g. "[O] O'Neil, CAN SLIM"
  created_at        timestamptz default now() not null
);

create index idx_rule_evals_candidate on public.rule_evaluations(candidate_id);
create index idx_rule_evals_rule      on public.rule_evaluations(rule_id);

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- User-owned tables: full CRUD only for own rows
alter table public.profiles              enable row level security;
alter table public.watchlists            enable row level security;
alter table public.trade_candidates      enable row level security;
alter table public.trades                enable row level security;
alter table public.portfolio             enable row level security;
alter table public.journal_entries       enable row level security;
alter table public.performance_metrics   enable row level security;
alter table public.rule_evaluations      enable row level security;

-- Reference-data tables: read-only for authenticated users, writes via service_role
alter table public.stocks                enable row level security;
alter table public.stock_prices          enable row level security;
alter table public.company_financials    enable row level security;
alter table public.company_news          enable row level security;
alter table public.technical_indicators  enable row level security;

-- ---- Policies for user-owned tables ----------------------------------------

create policy "profiles_own" on public.profiles
  for all using  (auth.uid() = id)
          with check (auth.uid() = id);

create policy "watchlists_own" on public.watchlists
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "candidates_own" on public.trade_candidates
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "trades_own" on public.trades
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "portfolio_own" on public.portfolio
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "journal_own" on public.journal_entries
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "performance_own" on public.performance_metrics
  for all using  (auth.uid() = user_id)
          with check (auth.uid() = user_id);

create policy "rule_evals_own" on public.rule_evaluations
  for all using (
    exists (
      select 1 from public.trade_candidates tc
      where tc.id = candidate_id and tc.user_id = auth.uid()
    )
  );

-- ---- Policies for reference-data tables (read-only to authenticated) -------

create policy "stocks_read_all"                on public.stocks
  for select using (auth.role() = 'authenticated');

create policy "stock_prices_read_all"          on public.stock_prices
  for select using (auth.role() = 'authenticated');

create policy "company_financials_read_all"    on public.company_financials
  for select using (auth.role() = 'authenticated');

create policy "company_news_read_all"          on public.company_news
  for select using (auth.role() = 'authenticated');

create policy "technical_indicators_read_all"  on public.technical_indicators
  for select using (auth.role() = 'authenticated');

-- ============================================================================
-- Triggers
-- ============================================================================

-- updated_at auto-updater
create or replace function public.trigger_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger set_updated_at_profiles     before update on public.profiles
  for each row execute function public.trigger_set_updated_at();

create trigger set_updated_at_stocks       before update on public.stocks
  for each row execute function public.trigger_set_updated_at();

create trigger set_updated_at_watchlists   before update on public.watchlists
  for each row execute function public.trigger_set_updated_at();

create trigger set_updated_at_trades       before update on public.trades
  for each row execute function public.trigger_set_updated_at();

-- Auto-create profile on user signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name', new.email));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================================
-- End of migration 00001
-- ============================================================================
