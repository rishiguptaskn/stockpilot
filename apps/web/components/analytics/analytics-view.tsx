'use client';

/**
 * Analytics — REAL performance metrics computed from the user's logged trades
 * (Supabase, RLS-scoped). Elder/Tharp conventions: R = initial risk at entry;
 * expectancy = mean R across closed trades. No trades → honest empty state.
 */

import { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
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
import { tradesService } from '@stockpilot/services';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatCard } from '@/components/stat-card';
import { cn } from '@/lib/utils';

const LINE = '#6d7cff'; // validated vs dark surface (dataviz six checks)

interface TradeRow {
  ticker: string;
  entry_date: string;
  exit_date?: string | null;
  entry_price: number;
  exit_price?: number | null;
  stop_price: number;
  shares: number;
  status: string;
}

const inr = (v: number) => `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export function AnalyticsView() {
  const [trades, setTrades] = useState<TradeRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tradesService
      .listAll()
      .then((t) => setTrades(t as unknown as TradeRow[]))
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Could not load trades — sign in first.'),
      )
      .finally(() => setLoading(false));
  }, []);

  const closed = useMemo(
    () => (trades ?? []).filter((t) => t.status !== 'open' && t.exit_price != null),
    [trades],
  );

  const stats = useMemo(() => {
    if (!closed.length) return null;
    const enriched = closed
      .map((t) => {
        const pnl = ((t.exit_price ?? 0) - t.entry_price) * t.shares;
        const risk = Math.max(0.01, (t.entry_price - t.stop_price) * t.shares);
        return { ...t, pnl, r: pnl / risk };
      })
      .sort((a, b) => (a.exit_date ?? '').localeCompare(b.exit_date ?? ''));
    const wins = enriched.filter((t) => t.pnl > 0);
    const losses = enriched.filter((t) => t.pnl <= 0);
    const grossWin = wins.reduce((s, t) => s + t.pnl, 0);
    const grossLoss = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
    let cum = 0;
    const curve = enriched.map((t) => ({
      date: t.exit_date ?? '',
      pnl: (cum += t.pnl),
    }));
    return {
      enriched,
      curve,
      n: enriched.length,
      winRate: (100 * wins.length) / enriched.length,
      avgWinR: wins.length ? wins.reduce((s, t) => s + t.r, 0) / wins.length : 0,
      avgLossR: losses.length ? losses.reduce((s, t) => s + t.r, 0) / losses.length : 0,
      expectancy: enriched.reduce((s, t) => s + t.r, 0) / enriched.length,
      profitFactor: grossLoss > 0 ? grossWin / grossLoss : wins.length ? Infinity : 0,
      totalPnl: cum,
    };
  }, [closed]);

  if (loading) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading your trades…
      </div>
    );
  }

  if (error || trades === null) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">
        Sign in to see analytics — metrics are computed from your logged trades.
        {error && <span className="mt-1 block text-xs opacity-70">({error})</span>}
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No closed trades yet. Log trades from Today or Portfolio; analytics appear
          after your first exit.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          {(trades ?? []).length} open position{(trades ?? []).length === 1 ? '' : 's'} currently.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Expectancy"
          value={`${stats.expectancy > 0 ? '+' : ''}${stats.expectancy.toFixed(3)}R`}
          hint="Mean R per closed trade"
        />
        <StatCard
          label="Win rate"
          value={`${stats.winRate.toFixed(1)}%`}
          hint={`avg win ${stats.avgWinR.toFixed(2)}R · avg loss ${stats.avgLossR.toFixed(2)}R`}
        />
        <StatCard
          label="Profit factor"
          value={Number.isFinite(stats.profitFactor) ? stats.profitFactor.toFixed(2) : '∞'}
          hint="Gross wins ÷ gross losses"
        />
        <StatCard label="Realized P&L" value={inr(stats.totalPnl)} hint={`${stats.n} closed trades`} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cumulative realized P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats.curve} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid stroke="currentColor" className="text-border" strokeOpacity={0.35} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} tickLine={false} axisLine={false} minTickGap={60} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} tickLine={false} axisLine={false} width={72} tickFormatter={(v: number) => inr(v)} />
                <Tooltip
                  cursor={{ stroke: LINE, strokeOpacity: 0.4 }}
                  contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: 'var(--muted-foreground)' }}
                  formatter={(v) => [inr(Number(v)), 'Cumulative P&L']}
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="4 4" strokeOpacity={0.5} />
                <Line type="monotone" dataKey="pnl" stroke={LINE} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Closed trades ({stats.n})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card text-left text-xs text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="px-4 py-2 font-medium">Stock</th>
                  <th className="px-4 py-2 font-medium">Entry → Exit</th>
                  <th className="px-4 py-2 text-right font-medium">Shares</th>
                  <th className="px-4 py-2 text-right font-medium">R</th>
                  <th className="px-4 py-2 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {stats.enriched.map((t, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="px-4 py-2 font-mono text-xs">{t.ticker.replace('.NS', '')}</td>
                    <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                      {t.entry_date} → {t.exit_date}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-xs">{t.shares}</td>
                    <td className={cn('px-4 py-2 text-right font-mono text-xs tabular-nums', t.r > 0 ? 'text-emerald-400' : 'text-rose-400')}>
                      {t.r > 0 ? '+' : ''}{t.r.toFixed(2)}
                    </td>
                    <td className={cn('px-4 py-2 text-right font-mono text-xs tabular-nums', t.pnl > 0 ? 'text-emerald-400' : 'text-rose-400')}>
                      {inr(t.pnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
