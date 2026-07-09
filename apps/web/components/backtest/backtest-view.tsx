'use client';

/**
 * Backtest page — drives the REAL deterministic backtester via the async job API.
 *
 *   POST /backtest/run           start a run (thread on the API)
 *   GET  /backtest/runs/{id}     poll status + progress; report when done
 *
 * Results render as: verdict banner (status color + icon, never color-alone),
 * stat tiles, single-series equity curve (validated #6d7cff on dark surface),
 * trades table, and the report's honest caveats.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, Loader2, Play, ShieldAlert, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { stocksService } from '@stockpilot/services';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StatCard } from '@/components/stat-card';
import { cn } from '@/lib/utils';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const LINE = '#6d7cff'; // validated vs dark surface (dataviz six checks)

interface RunStatus {
  run_id: string;
  status: 'running' | 'done' | 'failed';
  progress: { phase: string; done: number; total: number };
  error?: string;
  report?: BacktestReport;
}

interface BacktestReport {
  period: string;
  universe: string[];
  config: Record<string, number | boolean | string>;
  equity_curve: Array<{ date: string; equity: number }>;
  metrics: {
    n_trades: number;
    win_rate_pct: number;
    avg_win_r: number;
    avg_loss_r: number;
    expectancy_r: number;
    total_pnl_inr: number;
    total_costs_inr: number;
    final_equity_inr: number;
    cagr_pct: number;
    max_drawdown_pct: number;
    exposure_pct: number;
    avg_holding_days: number;
    exit_reason_counts: Record<string, number>;
  };
  trades: Array<{
    ticker: string;
    entry_date: string;
    exit_date: string;
    entry: number;
    exit: number;
    shares: number;
    pnl_inr: number;
    r: number;
    reason: string;
    score: number;
    days: number;
  }>;
  skipped_signals: Record<string, number>;
  caveats: string[];
  verdict: string;
}

const inr = (v: number) => `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export function BacktestView() {
  const [universe, setUniverse] = useState<string[]>([]);
  const [period, setPeriod] = useState<'2y' | '5y'>('2y');
  const [minScore, setMinScore] = useState<80 | 85 | 90>(85);
  const [requirePattern, setRequirePattern] = useState(true);
  const [run, setRun] = useState<RunStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollRun = useCallback((runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API_URL}/backtest/runs/${runId}`);
        if (!r.ok) return;
        const status = (await r.json()) as RunStatus;
        setRun(status);
        if (status.status !== 'running' && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          if (status.status === 'failed') toast.error('Backtest failed', { description: status.error });
        }
      } catch {
        /* transient poll errors are fine */
      }
    }, 3000);
  }, []);

  useEffect(() => {
    stocksService
      .list()
      .then((s) => setUniverse(s.map((x) => x.ticker)))
      .catch(() => setUniverse([]));

    // Rehydrate the most recent run (results survive a page reload)
    fetch(`${API_URL}/backtest/runs`)
      .then((r) => (r.ok ? r.json() : []))
      .then(async (runs: Array<{ run_id: string; status: string }>) => {
        if (!runs.length) return;
        const latest = runs[0];
        const full = await fetch(`${API_URL}/backtest/runs/${latest.run_id}`);
        if (!full.ok) return;
        const status = (await full.json()) as RunStatus;
        setRun(status);
        if (status.status === 'running') pollRun(status.run_id);
      })
      .catch(() => {});

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pollRun]);

  const start = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tickers: universe.slice(0, 50),
          period,
          min_score: minScore,
          require_pattern: requirePattern,
          capital_inr: 500_000,
        }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`);
      const { run_id } = (await res.json()) as { run_id: string };
      setRun({ run_id, status: 'running', progress: { phase: 'queued', done: 0, total: 1 } });
      pollRun(run_id);
    } catch (err) {
      toast.error('Could not start backtest', {
        description: err instanceof Error ? err.message : `Is the API running at ${API_URL}?`,
      });
    }
  }, [universe, period, minScore, requirePattern, pollRun]);

  const running = run?.status === 'running';
  const report = run?.status === 'done' ? run.report : undefined;
  const positive = report ? report.metrics.expectancy_r > 0 && report.metrics.n_trades > 0 : false;
  const pct = run?.progress?.total
    ? Math.round((run.progress.done / run.progress.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Config + launch */}
      <div className="panel-hero rounded-xl border border-border bg-card p-6">
        <span className="eyebrow-chip">Deterministic backtester</span>
        <h2 className="mt-3 text-xl font-semibold tracking-tight">
          Validate the rule engine on history before trusting it
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Point-in-time walk-forward: signals fill at next-day open, Indian delivery costs
          + slippage included, Elder 2%/6% sizing enforced. The exact production rule engine
          scores every scan date — nothing is simulated from summaries.
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-lg border border-border p-1">
            {(['2y', '5y'] as const).map((p) => (
              <Button
                key={p}
                size="sm"
                variant={period === p ? 'secondary' : 'ghost'}
                onClick={() => setPeriod(p)}
                disabled={running}
              >
                {p}
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-border p-1">
            {([80, 85, 90] as const).map((s) => (
              <Button
                key={s}
                size="sm"
                variant={minScore === s ? 'secondary' : 'ghost'}
                onClick={() => setMinScore(s)}
                disabled={running}
              >
                score ≥ {s}
              </Button>
            ))}
          </div>
          <Button
            size="sm"
            variant={requirePattern ? 'secondary' : 'ghost'}
            className="border border-border"
            onClick={() => setRequirePattern((v) => !v)}
            disabled={running}
          >
            {requirePattern ? '✓ ' : ''}pattern required
          </Button>
          <Button onClick={start} disabled={running || universe.length === 0} className="glow-primary-sm">
            {running ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Play className="mr-1.5 h-4 w-4" />}
            {running ? 'Running…' : `Run on ${Math.min(universe.length, 50)} stocks`}
          </Button>
        </div>

        {running && (
          <div className="mt-4 max-w-xl">
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span className="capitalize">{run?.progress.phase}…</span>
              <span className="font-mono">{pct}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Scoring every stock on every scan date — a few minutes for 2y, longer for 5y.
            </p>
          </div>
        )}
      </div>

      {run?.status === 'failed' && (
        <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{run.error}</span>
        </div>
      )}

      {report && (
        <>
          {/* Verdict — status color + icon + words, never color alone */}
          <div
            className={cn(
              'flex items-center gap-3 rounded-xl border p-4',
              positive
                ? 'border-emerald-500/30 bg-emerald-500/5'
                : 'border-amber-500/30 bg-amber-500/5',
            )}
          >
            {positive ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            ) : (
              <XCircle className="h-5 w-5 text-amber-400" />
            )}
            <div>
              <p className={cn('text-sm font-semibold', positive ? 'text-emerald-400' : 'text-amber-400')}>
                {report.verdict}
              </p>
              <p className="text-xs text-muted-foreground">
                {report.metrics.n_trades} trades · {report.period} · score ≥ {String(report.config.min_score)} ·
                pattern {report.config.require_pattern ? 'required' : 'not required'} · after all costs
              </p>
            </div>
          </div>

          {/* Stat tiles */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Expectancy" value={`${report.metrics.expectancy_r > 0 ? '+' : ''}${report.metrics.expectancy_r.toFixed(3)}R`} hint="Mean R-multiple, net of costs" />
            <StatCard label="Win rate" value={`${report.metrics.win_rate_pct.toFixed(1)}%`} hint={`avg win ${report.metrics.avg_win_r.toFixed(2)}R · avg loss ${report.metrics.avg_loss_r.toFixed(2)}R`} />
            <StatCard label="CAGR" value={`${report.metrics.cagr_pct.toFixed(2)}%`} hint={`exposure ${report.metrics.exposure_pct.toFixed(0)}% of days`} />
            <StatCard label="Max drawdown" value={`${report.metrics.max_drawdown_pct.toFixed(2)}%`} hint="Peak-to-trough equity" />
            <StatCard label="Net P&L" value={inr(report.metrics.total_pnl_inr)} hint={`costs paid ${inr(report.metrics.total_costs_inr)}`} />
            <StatCard label="Final equity" value={inr(report.metrics.final_equity_inr)} hint={`from ${inr(Number(report.config.capital_inr))}`} />
            <StatCard label="Trades" value={String(report.metrics.n_trades)} hint={`avg hold ${report.metrics.avg_holding_days.toFixed(1)} days`} />
            <StatCard
              label="Exits"
              value={Object.entries(report.metrics.exit_reason_counts)
                .map(([k, v]) => `${k} ${v}`)
                .join(' · ') || '—'}
              hint="stop / target / time / trail"
            />
          </div>

          {/* Equity curve — single series, validated line color */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Equity curve (mark-to-market, daily)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={report.equity_curve} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                    <CartesianGrid stroke="currentColor" className="text-border" strokeOpacity={0.35} vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={60}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
                      tickLine={false}
                      axisLine={false}
                      width={78}
                      domain={['auto', 'auto']}
                      tickFormatter={(v: number) => inr(v)}
                    />
                    <Tooltip
                      cursor={{ stroke: LINE, strokeOpacity: 0.4 }}
                      contentStyle={{
                        background: 'var(--card)',
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      labelStyle={{ color: 'var(--muted-foreground)' }}
                      formatter={(v) => [inr(Number(v)), 'Equity']}
                    />
                    <ReferenceLine
                      y={Number(report.config.capital_inr)}
                      stroke="var(--muted-foreground)"
                      strokeDasharray="4 4"
                      strokeOpacity={0.5}
                    />
                    <Line type="monotone" dataKey="equity" stroke={LINE} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Trades table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Trades ({report.trades.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-card text-left text-xs text-muted-foreground">
                    <tr className="border-b border-border">
                      <th className="px-4 py-2 font-medium">Stock</th>
                      <th className="px-4 py-2 font-medium">Entry → Exit</th>
                      <th className="px-4 py-2 text-right font-medium">Days</th>
                      <th className="px-4 py-2 font-medium">Exit via</th>
                      <th className="px-4 py-2 text-right font-medium">R</th>
                      <th className="px-4 py-2 text-right font-medium">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.trades.map((t, i) => (
                      <tr key={i} className="border-b border-border/50">
                        <td className="px-4 py-2 font-mono text-xs">{t.ticker.replace('.NS', '')}</td>
                        <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                          {t.entry_date} → {t.exit_date}
                        </td>
                        <td className="px-4 py-2 text-right font-mono text-xs">{t.days}</td>
                        <td className="px-4 py-2 text-xs">{t.reason}</td>
                        <td
                          className={cn(
                            'px-4 py-2 text-right font-mono text-xs tabular-nums',
                            t.r > 0 ? 'text-emerald-400' : t.r < 0 ? 'text-rose-400' : 'text-muted-foreground',
                          )}
                        >
                          {t.r > 0 ? '+' : ''}
                          {t.r.toFixed(2)}
                        </td>
                        <td
                          className={cn(
                            'px-4 py-2 text-right font-mono text-xs tabular-nums',
                            t.pnl_inr > 0 ? 'text-emerald-400' : t.pnl_inr < 0 ? 'text-rose-400' : 'text-muted-foreground',
                          )}
                        >
                          {inr(t.pnl_inr)}
                        </td>
                      </tr>
                    ))}
                    {report.trades.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                          No trades — no signal cleared the threshold + hard gates in this window.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Honest caveats — part of the report contract */}
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-4">
            <p className="mb-1.5 text-xs font-medium text-amber-400">
              Read before believing the numbers
            </p>
            <ul className="list-inside list-disc space-y-1 text-xs text-muted-foreground">
              {report.caveats.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
              {Object.keys(report.skipped_signals).length > 0 && (
                <li>
                  Skipped signals:{' '}
                  {Object.entries(report.skipped_signals)
                    .map(([k, v]) => `${k} ×${v}`)
                    .join(', ')}
                  {' '}(honest accounting — nothing silently dropped).
                </li>
              )}
            </ul>
          </div>
        </>
      )}

      {!run && (
        <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
          Configure and run a backtest. Results include equity curve, expectancy after costs,
          every trade, and the caveats that qualify them.{' '}
          <Badge variant="outline" className="ml-1 font-mono text-[10px]">
            No live capital until expectancy &gt; 0
          </Badge>
        </div>
      )}
    </div>
  );
}
