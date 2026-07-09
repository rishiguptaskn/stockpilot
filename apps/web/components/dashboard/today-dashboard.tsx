'use client';

/**
 * Today dashboard — REAL data only. No mocks.
 *
 *   Market Environment  → GET /market/environment (fresh Nifty, Module 1)
 *   Candidates          → POST /engine/run-workflow (full rule engine)
 *   Open positions/risk → Supabase trades (RLS: signed-in user)
 *   Universe            → Supabase stocks (is_active)
 *
 * Static v1 inputs (VIX/FII/breadth) are labelled — a default never
 * masquerades as a live reading.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivitySquare,
  AlertTriangle,
  Landmark,
  Loader2,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import { stocksService, tradesService } from '@stockpilot/services';
import { StatCard } from '@/components/stat-card';
import {
  MarketStatusCard,
  type MarketCheckItem,
} from '@/components/dashboard/market-status-card';
import {
  CandidatesTable,
  type CandidateRow,
} from '@/components/dashboard/candidates-table';
import { Button } from '@/components/ui/button';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const CAPITAL_INR = 500_000; // v1: single configured account size (Settings later)
const MAX_POSITIONS = 5;
const OPEN_RISK_CAP = 0.06; // Elder 6%

// --- API wire types ----------------------------------------------------------

interface MarketEnvWire {
  as_of: string;
  nifty_close: number;
  score: number;
  verdict: 'bullish' | 'neutral' | 'bearish';
  hard_gates_passed: boolean;
  checks: Array<{
    rule_id: string;
    label: string;
    passed: boolean;
    detail: string;
    hard_gate: boolean;
    input_quality: 'live' | 'proxy' | 'static_default';
  }>;
}

interface WorkflowCandidateWire {
  ticker: string;
  aggregate_score: number;
  verdict: string;
  detected_patterns: string[];
  entry: number;
  stop: number;
  target: number;
  shares: number;
}

interface WorkflowResponseWire {
  as_of: string;
  universe_size: number;
  candidates: WorkflowCandidateWire[];
  all_results: WorkflowCandidateWire[];
}

// Supabase rows come back snake_case regardless of the TS type's casing.
interface OpenTradeRow {
  entry_price?: number;
  stop_price?: number;
  shares?: number;
}

// ------------------------------------------------------------------------------

export function TodayDashboard() {
  const [market, setMarket] = useState<MarketEnvWire | null>(null);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [universeCount, setUniverseCount] = useState<number | null>(null);
  const [universe, setUniverse] = useState<
    Array<{ ticker: string; name: string; sector: string | null }>
  >([]);
  const [openTrades, setOpenTrades] = useState<OpenTradeRow[] | null>(null);
  const [scan, setScan] = useState<WorkflowResponseWire | null>(null);
  const [scanning, setScanning] = useState(false);

  // Market environment — fresh Nifty via the API
  useEffect(() => {
    fetch(`${API_URL}/market/environment`)
      .then((r) => {
        if (!r.ok) throw new Error(`API responded ${r.status}`);
        return r.json();
      })
      .then((d: MarketEnvWire) => setMarket(d))
      .catch((e) =>
        setMarketError(
          `${e instanceof Error ? e.message : 'failed'} — is the API running at ${API_URL}?`,
        ),
      );
  }, []);

  // Universe + open positions (positions need auth; fail soft to null)
  useEffect(() => {
    stocksService
      .list()
      .then((stocks) => {
        setUniverse(
          stocks.map((s) => ({
            ticker: s.ticker,
            name: s.name,
            sector: s.sector ?? null,
          })),
        );
        setUniverseCount(stocks.length);
      })
      .catch(() => setUniverseCount(null));
    tradesService
      .listOpen()
      .then((t) => setOpenTrades(t as unknown as OpenTradeRow[]))
      .catch(() => setOpenTrades(null));
  }, []);

  const openRiskPct = useMemo(() => {
    if (!openTrades) return null;
    const risk = openTrades.reduce(
      (sum, t) =>
        sum + Math.max(0, (t.entry_price ?? 0) - (t.stop_price ?? 0)) * (t.shares ?? 0),
      0,
    );
    return (risk / CAPITAL_INR) * 100;
  }, [openTrades]);

  const runScan = useCallback(async () => {
    const tickers = universe.map((s) => s.ticker);
    if (tickers.length === 0) {
      toast.error('Universe is empty', {
        description: 'No active stocks in Supabase — seed the stocks table first.',
      });
      return;
    }
    setScanning(true);
    const toastId = toast.loading(`Scanning ${tickers.length} stocks…`, {
      description: 'Fetching prices + scoring against all 206 rules. Takes a few minutes.',
    });
    try {
      const res = await fetch(`${API_URL}/engine/run-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: tickers.slice(0, 50), capital_inr: CAPITAL_INR }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = (await res.json()) as WorkflowResponseWire;
      setScan(data);
      toast.dismiss(toastId);
      const n = data.candidates?.length ?? 0;
      const top = data.all_results?.[0]?.aggregate_score ?? 0;
      (n > 0 ? toast.success : toast.info)(
        n > 0 ? `${n} candidate${n > 1 ? 's' : ''} surfaced` : 'No candidates today',
        {
          description: `Scanned ${data.universe_size} stocks · top score ${top.toFixed(1)} · as of ${data.as_of}`,
        },
      );
    } catch (err) {
      toast.dismiss(toastId);
      toast.error('Scan failed', {
        description: err instanceof Error ? err.message : `Could not reach ${API_URL}`,
      });
    } finally {
      setScanning(false);
    }
  }, [universe]);

  // --- view mapping -----------------------------------------------------------

  const checks: MarketCheckItem[] = useMemo(() => {
    if (!market) return [];
    return market.checks.map((c) => ({
      label: c.label,
      // static defaults render as neutral so a hardcoded input can't show green
      status: c.input_quality === 'static_default' ? 'neutral' : c.passed ? 'pass' : 'fail',
      detail:
        c.input_quality === 'static_default'
          ? `${c.detail} · v1 default`
          : c.input_quality === 'proxy'
            ? `${c.detail} · proxy`
            : c.detail,
    }));
  }, [market]);

  const byTicker = useMemo(
    () => new Map(universe.map((s) => [s.ticker, s])),
    [universe],
  );

  const candidateRows: CandidateRow[] = useMemo(() => {
    if (!scan) return [];
    const surfaced = scan.candidates?.length ? scan.candidates : [];
    return surfaced.map((c) => {
      const meta = byTicker.get(c.ticker);
      const riskPerShare = c.entry - c.stop;
      return {
        ticker: c.ticker.replace('.NS', ''),
        name: meta?.name ?? c.ticker,
        sector: meta?.sector ?? '—',
        score: c.aggregate_score,
        entry: c.entry,
        stop: c.stop,
        target: c.target,
        rr: riskPerShare > 0 ? (c.target - c.entry) / riskPerShare : 0,
        pattern: c.detected_patterns?.[0],
      };
    });
  }, [scan, byTicker]);

  const topRejects: CandidateRow[] = useMemo(() => {
    if (!scan || scan.candidates?.length) return [];
    return (scan.all_results ?? []).slice(0, 5).map((c) => {
      const meta = byTicker.get(c.ticker);
      const riskPerShare = c.entry - c.stop;
      return {
        ticker: c.ticker.replace('.NS', ''),
        name: meta?.name ?? c.ticker,
        sector: meta?.sector ?? '—',
        score: c.aggregate_score,
        entry: c.entry,
        stop: c.stop,
        target: c.target,
        rr: riskPerShare > 0 ? (c.target - c.entry) / riskPerShare : 0,
        pattern: c.detected_patterns?.[0],
      };
    });
  }, [scan, byTicker]);

  return (
    <div className="space-y-6">
      {/* Stat row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <StatCard
          label="Capital"
          value={`₹${CAPITAL_INR.toLocaleString('en-IN')}`}
          hint="Configured account size"
          icon={<Landmark className="h-4 w-4" />}
        />
        <StatCard
          label="Universe"
          value={universeCount === null ? '—' : String(universeCount)}
          hint="Active NSE stocks (Supabase)"
          icon={<ActivitySquare className="h-4 w-4" />}
        />
        <StatCard
          label="Open positions"
          value={openTrades === null ? '—' : `${openTrades.length} / ${MAX_POSITIONS}`}
          hint={openTrades === null ? 'Sign in to sync trades' : `Max ${MAX_POSITIONS} concurrent`}
          icon={<ActivitySquare className="h-4 w-4" />}
        />
        <StatCard
          label="Open risk"
          value={openRiskPct === null ? '—' : `${openRiskPct.toFixed(2)}%`}
          hint={`Elder cap ${(OPEN_RISK_CAP * 100).toFixed(0)}%`}
          icon={<ShieldCheck className="h-4 w-4" />}
        />
        <StatCard
          label="Candidates"
          value={scan ? String(scan.candidates?.length ?? 0) : '—'}
          hint={scan ? `as of ${scan.as_of}` : 'Run a scan'}
          icon={<AlertTriangle className="h-4 w-4" />}
        />
      </div>

      {/* Market environment + scan action */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          {market ? (
            <MarketStatusCard verdict={market.verdict} score={market.score} checks={checks} />
          ) : (
            <div className="flex h-full min-h-48 items-center justify-center rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
              {marketError ?? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Evaluating market environment (Module 1, live Nifty)…
                </span>
              )}
            </div>
          )}
        </div>

        <div className="space-y-4 lg:col-span-2">
          <div className="panel-hero flex h-full flex-col items-start justify-center gap-3 rounded-xl border border-border bg-card p-6">
            <span className="eyebrow-chip">Rule engine scan</span>
            <h2 className="text-xl font-semibold tracking-tight">
              Scan the universe against all 206 rules
            </h2>
            <p className="text-sm text-muted-foreground">
              Fetches fresh prices for every active stock, runs Modules 1–10 + 8 pattern
              detectors, and surfaces only candidates passing hard gates with score ≥ 90
              (watch ≥ 85). Nothing is auto-traded — you review every plan.
            </p>
            <Button onClick={runScan} disabled={scanning || universe.length === 0} className="glow-primary-sm">
              {scanning ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-1.5 h-4 w-4" />
              )}
              {scanning ? 'Scanning… (a few minutes)' : 'Run full scan'}
            </Button>
          </div>
        </div>
      </div>

      {/* Candidates */}
      <CandidatesTable rows={candidateRows} empty={scan !== null && candidateRows.length === 0} />

      {/* Nearest misses when nothing surfaced */}
      {scan && candidateRows.length === 0 && topRejects.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Closest to threshold (rejected — shown for context, not trade ideas)
          </h3>
          <CandidatesTable rows={topRejects} />
        </div>
      )}
    </div>
  );
}
