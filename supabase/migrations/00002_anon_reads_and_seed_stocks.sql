-- ============================================================================
-- StockPilot — Migration 00002
-- ============================================================================
-- Purpose:
--   (a) Broaden read policies on reference-data tables so anonymous (not-signed-in)
--       clients can read them. Reference data (stocks, prices, indicators, news,
--       financials) is public by nature — nothing user-specific there.
--       User-owned tables (trades, journal, portfolio, ...) remain
--       authenticated-only, RLS-enforced per-user.
--   (b) Seed the `stocks` table with 30 top Nifty 50 constituents so the app
--       has real data to display end-to-end.
-- ============================================================================

-- --- 1. Broaden read access on reference tables to anonymous users ----------
-- Replaces the `authenticated`-only SELECT policies from migration 00001 with
-- policies that allow both `anon` and `authenticated` roles to SELECT.

drop policy if exists "stocks_read_all" on public.stocks;
drop policy if exists "stock_prices_read_all" on public.stock_prices;
drop policy if exists "company_financials_read_all" on public.company_financials;
drop policy if exists "company_news_read_all" on public.company_news;
drop policy if exists "technical_indicators_read_all" on public.technical_indicators;

create policy "stocks_public_read" on public.stocks
  for select to anon, authenticated using (true);

create policy "stock_prices_public_read" on public.stock_prices
  for select to anon, authenticated using (true);

create policy "company_financials_public_read" on public.company_financials
  for select to anon, authenticated using (true);

create policy "company_news_public_read" on public.company_news
  for select to anon, authenticated using (true);

create policy "technical_indicators_public_read" on public.technical_indicators
  for select to anon, authenticated using (true);

-- --- 2. Seed the 30 top Nifty 50 stocks -------------------------------------
-- Sector classification uses NSE's own scheme (industries as of 2025).
-- `ticker` uses the yfinance convention (`<symbol>.NS`) so it lines up with
-- our data ingestion in Month 2.

insert into public.stocks (ticker, name, sector, industry, exchange) values
  ('RELIANCE.NS',   'Reliance Industries Ltd',      'Energy',              'Refineries',           'NSE'),
  ('TCS.NS',        'Tata Consultancy Services',    'Information Technology', 'IT Services',       'NSE'),
  ('HDFCBANK.NS',   'HDFC Bank Ltd',                'Financial Services',  'Banks',                'NSE'),
  ('BHARTIARTL.NS', 'Bharti Airtel Ltd',            'Telecommunications',  'Telecom Services',     'NSE'),
  ('ICICIBANK.NS',  'ICICI Bank Ltd',               'Financial Services',  'Banks',                'NSE'),
  ('INFY.NS',       'Infosys Ltd',                  'Information Technology', 'IT Services',       'NSE'),
  ('SBIN.NS',       'State Bank of India',          'Financial Services',  'Banks',                'NSE'),
  ('LICI.NS',       'Life Insurance Corp of India', 'Financial Services',  'Insurance',            'NSE'),
  ('HINDUNILVR.NS', 'Hindustan Unilever Ltd',       'FMCG',                'Personal Products',    'NSE'),
  ('ITC.NS',        'ITC Ltd',                      'FMCG',                'Cigarettes & Tobacco', 'NSE'),
  ('LT.NS',         'Larsen & Toubro Ltd',          'Capital Goods',       'Construction',         'NSE'),
  ('KOTAKBANK.NS',  'Kotak Mahindra Bank Ltd',      'Financial Services',  'Banks',                'NSE'),
  ('AXISBANK.NS',   'Axis Bank Ltd',                'Financial Services',  'Banks',                'NSE'),
  ('BAJFINANCE.NS', 'Bajaj Finance Ltd',            'Financial Services',  'NBFC',                 'NSE'),
  ('SUNPHARMA.NS',  'Sun Pharmaceutical Industries','Healthcare',          'Pharmaceuticals',      'NSE'),
  ('M&M.NS',        'Mahindra & Mahindra Ltd',      'Automobile',          'Passenger Vehicles',   'NSE'),
  ('ASIANPAINT.NS', 'Asian Paints Ltd',             'Consumer Durables',   'Paints',               'NSE'),
  ('MARUTI.NS',     'Maruti Suzuki India Ltd',      'Automobile',          'Passenger Vehicles',   'NSE'),
  ('NTPC.NS',       'NTPC Ltd',                     'Power',               'Power Generation',     'NSE'),
  ('TATAMOTORS.NS', 'Tata Motors Ltd',              'Automobile',          'Passenger Vehicles',   'NSE'),
  ('TITAN.NS',      'Titan Company Ltd',            'Consumer Durables',   'Jewellery & Watches',  'NSE'),
  ('NESTLEIND.NS',  'Nestle India Ltd',             'FMCG',                'Packaged Foods',       'NSE'),
  ('ULTRACEMCO.NS', 'UltraTech Cement Ltd',         'Construction Materials','Cement',             'NSE'),
  ('ADANIENT.NS',   'Adani Enterprises Ltd',        'Metals & Mining',     'Diversified',          'NSE'),
  ('BAJAJ-AUTO.NS', 'Bajaj Auto Ltd',               'Automobile',          '2/3 Wheelers',         'NSE'),
  ('WIPRO.NS',      'Wipro Ltd',                    'Information Technology', 'IT Services',       'NSE'),
  ('TECHM.NS',      'Tech Mahindra Ltd',            'Information Technology', 'IT Services',       'NSE'),
  ('HCLTECH.NS',    'HCL Technologies Ltd',         'Information Technology', 'IT Services',       'NSE'),
  ('POWERGRID.NS',  'Power Grid Corp of India',     'Power',               'Power Transmission',   'NSE'),
  ('ONGC.NS',       'Oil & Natural Gas Corp',       'Oil, Gas & Consumables','Oil Exploration',    'NSE')
on conflict (ticker) do update
  set name = excluded.name,
      sector = excluded.sector,
      industry = excluded.industry,
      exchange = excluded.exchange,
      updated_at = now();

-- ============================================================================
-- End of migration 00002
-- ============================================================================
