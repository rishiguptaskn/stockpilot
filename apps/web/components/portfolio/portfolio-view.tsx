'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { Loader2, Target, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import {
  useOpenTrades,
  useUpdateTradeStop,
  useCloseTrade,
  formatINR,
  formatPercent,
  displayTicker,
} from '@stockpilot/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { StatCard } from '@/components/stat-card';

const CAPITAL_INR = 500_000;
const MAX_OPEN_RISK_PCT = 6.0;

interface TradeRow {
  id: string;
  ticker: string;
  entry_date: string;
  entry_price: number;
  stop_price: number;
  target_price: number | null;
  shares: number;
  status: string;
}

export function PortfolioView() {
  const openTrades = useOpenTrades();

  const summary = useMemo(() => {
    const trades = (openTrades.data ?? []) as unknown as TradeRow[];
    const capitalDeployed = trades.reduce((s, t) => s + t.entry_price * t.shares, 0);
    const totalRisk = trades.reduce(
      (s, t) => s + Math.max(0, t.entry_price - t.stop_price) * t.shares,
      0,
    );
    const cash = Math.max(0, CAPITAL_INR - capitalDeployed);
    const riskPct = (totalRisk / CAPITAL_INR) * 100;
    return {
      trades,
      capitalDeployed,
      totalRisk,
      cash,
      riskPct,
      deployedPct: (capitalDeployed / CAPITAL_INR) * 100,
      cashPct: (cash / CAPITAL_INR) * 100,
    };
  }, [openTrades.data]);

  if (openTrades.isLoading) {
    return <PortfolioSkeleton />;
  }

  if (openTrades.error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-rose-400">
            Could not load portfolio: {(openTrades.error as Error).message}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            You may need to sign in — portfolio data is RLS-scoped to your user.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stat row */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          label="Capital"
          value={formatINR(CAPITAL_INR)}
          hint="Total account"
        />
        <StatCard
          label="Deployed"
          value={formatINR(summary.capitalDeployed)}
          trend="flat"
          trendLabel={formatPercent(summary.deployedPct)}
        />
        <StatCard
          label="Cash"
          value={formatINR(summary.cash)}
          trend="flat"
          trendLabel={formatPercent(summary.cashPct)}
        />
        <StatCard
          label="Open risk"
          value={formatPercent(summary.riskPct)}
          hint={`of ${MAX_OPEN_RISK_PCT}% cap`}
          trend={summary.riskPct > MAX_OPEN_RISK_PCT ? 'up' : 'flat'}
          icon={<Target className="h-4 w-4" />}
        />
      </div>

      {/* Elder 6% rule gauge */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            Portfolio open risk
            <Badge
              variant="outline"
              className={
                summary.riskPct > MAX_OPEN_RISK_PCT
                  ? 'border-rose-500/30 bg-rose-500/10 text-rose-400'
                  : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              }
            >
              Elder 6% rule (M9.4)
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-2xl font-semibold tabular-nums">
                {formatPercent(summary.riskPct)}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatINR(summary.totalRisk)} at risk / {formatINR(CAPITAL_INR)} capital
              </span>
            </div>
            <div className="relative h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full transition-all ${
                  summary.riskPct > MAX_OPEN_RISK_PCT ? 'bg-rose-500' : 'bg-emerald-500'
                }`}
                style={{
                  width: `${Math.min(100, (summary.riskPct / MAX_OPEN_RISK_PCT) * 100)}%`,
                }}
              />
              <div
                className="absolute inset-y-0 border-r border-dashed border-foreground/40"
                style={{ left: '100%' }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Sum of (entry − stop) × shares across all open positions must stay ≤ 6% of
              capital.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Open positions table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Open positions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {summary.trades.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-muted-foreground">No open positions.</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Use &ldquo;Add trade&rdquo; after executing an order in Groww.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border">
                    <TableHead>Stock</TableHead>
                    <TableHead>Entry date</TableHead>
                    <TableHead className="text-right">Entry</TableHead>
                    <TableHead className="text-right">Stop</TableHead>
                    <TableHead className="text-right">Target</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">Risk</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.trades.map((t) => (
                    <TradeRowView key={t.id} trade={t} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ----------------------------------------------------------------------------

function TradeRowView({ trade }: { trade: TradeRow }) {
  const risk = Math.max(0, trade.entry_price - trade.stop_price) * trade.shares;
  const riskPct = (risk / CAPITAL_INR) * 100;

  return (
    <TableRow className="border-border">
      <TableCell>
        <Link
          href={`/stock/${trade.ticker}`}
          className="group inline-flex items-center gap-1.5 font-mono text-sm font-medium hover:underline"
        >
          {displayTicker(trade.ticker)}
          <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100" />
        </Link>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">{trade.entry_date}</TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        ₹{trade.entry_price.toFixed(2)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-rose-400">
        ₹{trade.stop_price.toFixed(2)}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-emerald-400">
        {trade.target_price ? `₹${trade.target_price.toFixed(2)}` : '—'}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {trade.shares}
      </TableCell>
      <TableCell className="text-right">
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          {formatINR(risk)} ({riskPct.toFixed(2)}%)
        </span>
      </TableCell>
      <TableCell className="text-right">
        <div className="flex justify-end gap-2">
          <UpdateStopSheet trade={trade} />
          <CloseTradeSheet trade={trade} />
        </div>
      </TableCell>
    </TableRow>
  );
}

// ----------------------------------------------------------------------------

function UpdateStopSheet({ trade }: { trade: TradeRow }) {
  const [open, setOpen] = useState(false);
  const [newStop, setNewStop] = useState(trade.stop_price.toString());
  const updateStop = useUpdateTradeStop();

  async function handleSubmit() {
    try {
      await updateStop.mutateAsync({
        tradeId: trade.id,
        newStop: parseFloat(newStop),
      });
      toast.success('Stop updated', { description: `${displayTicker(trade.ticker)} stop now ₹${newStop}` });
      setOpen(false);
    } catch (err) {
      toast.error('Cannot update stop', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="ghost" size="sm">
            Stop
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Update stop-loss</SheetTitle>
          <SheetDescription>
            Stop can only be tightened (moved higher for a long position). Rule
            M9.19 enforced server-side.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div className="rounded-md border bg-muted/30 p-3 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Ticker</span>
              <span className="font-mono">{displayTicker(trade.ticker)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Entry</span>
              <span className="font-mono">₹{trade.entry_price.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Current stop</span>
              <span className="font-mono text-rose-400">₹{trade.stop_price.toFixed(2)}</span>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">New stop (₹)</label>
            <Input
              type="number"
              step="0.01"
              value={newStop}
              onChange={(e) => setNewStop(e.target.value)}
              min={trade.stop_price}
            />
            <p className="text-[10px] text-muted-foreground">
              Must be ≥ current stop of ₹{trade.stop_price.toFixed(2)}.
            </p>
          </div>
        </div>
        <SheetFooter className="mt-6">
          <Button onClick={handleSubmit} disabled={updateStop.isPending} className="w-full">
            {updateStop.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Update stop
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ----------------------------------------------------------------------------

function CloseTradeSheet({ trade }: { trade: TradeRow }) {
  const [open, setOpen] = useState(false);
  const [exitPrice, setExitPrice] = useState('');
  const closeTrade = useCloseTrade();

  const parsed = useMemo(() => {
    const exit = parseFloat(exitPrice) || 0;
    if (exit <= 0) return null;
    const pnl = (exit - trade.entry_price) * trade.shares;
    const pnlPct = ((exit - trade.entry_price) / trade.entry_price) * 100;
    const initialRisk = trade.entry_price - trade.stop_price;
    const rMultiple = initialRisk > 0 ? (exit - trade.entry_price) / initialRisk : 0;
    return { pnl, pnlPct, rMultiple };
  }, [exitPrice, trade]);

  async function handleSubmit() {
    if (!exitPrice) return;
    try {
      await closeTrade.mutateAsync({
        tradeId: trade.id,
        exitDate: new Date().toISOString().slice(0, 10),
        exitPrice: parseFloat(exitPrice),
      });
      toast.success('Trade closed', {
        description: `${displayTicker(trade.ticker)} P&L: ${parsed ? formatINR(parsed.pnl) : ''}`,
      });
      setOpen(false);
    } catch (err) {
      toast.error('Could not close trade', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="ghost" size="sm">
            Close
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Close position</SheetTitle>
          <SheetDescription>
            Record the exit. R multiple and P&L are computed automatically.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div className="rounded-md border bg-muted/30 p-3 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Ticker</span>
              <span className="font-mono">{displayTicker(trade.ticker)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Entry</span>
              <span className="font-mono">₹{trade.entry_price.toFixed(2)} × {trade.shares}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Stop</span>
              <span className="font-mono text-rose-400">₹{trade.stop_price.toFixed(2)}</span>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Exit price (₹)</label>
            <Input
              type="number"
              step="0.01"
              value={exitPrice}
              onChange={(e) => setExitPrice(e.target.value)}
              required
            />
          </div>
          {parsed && (
            <div className="rounded-md border bg-muted/30 p-3 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">P&L</span>
                <span
                  className={`font-mono font-semibold tabular-nums ${
                    parsed.pnl > 0 ? 'text-emerald-400' : parsed.pnl < 0 ? 'text-rose-400' : ''
                  }`}
                >
                  {formatINR(parsed.pnl)} ({parsed.pnlPct >= 0 ? '+' : ''}
                  {parsed.pnlPct.toFixed(2)}%)
                </span>
              </div>
              <Separator className="my-2" />
              <div className="flex justify-between">
                <span className="text-muted-foreground">R multiple</span>
                <span
                  className={`font-mono tabular-nums ${
                    parsed.rMultiple >= 1
                      ? 'text-emerald-400'
                      : parsed.rMultiple < 0
                        ? 'text-rose-400'
                        : ''
                  }`}
                >
                  {parsed.rMultiple >= 0 ? '+' : ''}
                  {parsed.rMultiple.toFixed(2)}R
                </span>
              </div>
            </div>
          )}
        </div>
        <SheetFooter className="mt-6">
          <Button
            onClick={handleSubmit}
            disabled={!exitPrice || closeTrade.isPending}
            className="w-full"
          >
            {closeTrade.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Close position
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ----------------------------------------------------------------------------

function PortfolioSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border bg-card p-4">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="mt-2 h-7 w-24" />
          </div>
        ))}
      </div>
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
