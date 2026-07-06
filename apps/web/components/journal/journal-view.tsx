'use client';

import { useMemo, useState } from 'react';
import { Loader2, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import {
  useAllTrades,
  useMyJournal,
  useUpsertJournal,
  displayTicker,
  formatINR,
} from '@stockpilot/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

interface TradeRow {
  id: string;
  ticker: string;
  entry_date: string;
  entry_price: number;
  stop_price: number;
  target_price: number | null;
  exit_date: string | null;
  exit_price: number | null;
  shares: number;
  status: string;
}

interface JournalRow {
  id: string;
  trade_id: string;
  entry_reason: string | null;
  exit_reason: string | null;
  rule_adherence_pct: number | null;
  lessons: string | null;
  created_at: string;
}

export function JournalView() {
  const trades = useAllTrades();
  const journal = useMyJournal();

  const merged = useMemo(() => {
    const t = (trades.data ?? []) as unknown as TradeRow[];
    const j = (journal.data ?? []) as unknown as JournalRow[];
    const journalByTrade = new Map<string, JournalRow[]>();
    for (const entry of j) {
      const list = journalByTrade.get(entry.trade_id) ?? [];
      list.push(entry);
      journalByTrade.set(entry.trade_id, list);
    }
    return t.map((trade) => ({
      trade,
      entries: journalByTrade.get(trade.id) ?? [],
    }));
  }, [trades.data, journal.data]);

  if (trades.isLoading || journal.isLoading) {
    return <JournalSkeleton />;
  }

  if (trades.error || journal.error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-rose-400">Could not load journal.</p>
          <p className="mt-2 text-xs text-muted-foreground">
            You may need to sign in — journal data is RLS-scoped to your user.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (merged.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <MessageSquare className="mb-3 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No trades yet.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Add a trade from the Portfolio page. Every trade should have a journal entry.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {merged.map(({ trade, entries }) => (
        <TradeJournalCard key={trade.id} trade={trade} entries={entries} />
      ))}
    </div>
  );
}

// ----------------------------------------------------------------------------

function TradeJournalCard({
  trade,
  entries,
}: {
  trade: TradeRow;
  entries: JournalRow[];
}) {
  const isOpen = trade.status === 'open';
  const isWin = trade.status === 'closed_win';
  const isLoss = trade.status === 'closed_loss';

  const pnl = useMemo(() => {
    if (!trade.exit_price) return null;
    const total = (trade.exit_price - trade.entry_price) * trade.shares;
    const initialRisk = trade.entry_price - trade.stop_price;
    const rMultiple = initialRisk > 0 ? (trade.exit_price - trade.entry_price) / initialRisk : 0;
    return { total, rMultiple };
  }, [trade]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-mono text-base font-semibold">
                {displayTicker(trade.ticker)}
              </h3>
              <Badge
                variant="outline"
                className={
                  isOpen
                    ? 'border-blue-500/30 bg-blue-500/10 text-blue-400'
                    : isWin
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                      : isLoss
                        ? 'border-rose-500/30 bg-rose-500/10 text-rose-400'
                        : 'border-zinc-500/30 bg-zinc-500/10 text-zinc-400'
                }
              >
                {isOpen ? 'Open' : isWin ? 'Won' : isLoss ? 'Lost' : 'Breakeven'}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Entered {trade.entry_date} · {trade.shares} shares @ ₹{trade.entry_price.toFixed(2)}
              {trade.exit_date && ` · Exited ${trade.exit_date} @ ₹${trade.exit_price?.toFixed(2)}`}
            </p>
          </div>
        </div>
        {pnl && (
          <div className="text-right">
            <div
              className={`font-mono text-sm font-semibold tabular-nums ${
                pnl.total > 0
                  ? 'text-emerald-400'
                  : pnl.total < 0
                    ? 'text-rose-400'
                    : 'text-muted-foreground'
              }`}
            >
              {formatINR(pnl.total)}
            </div>
            <div className="text-xs text-muted-foreground">
              {pnl.rMultiple >= 0 ? '+' : ''}
              {pnl.rMultiple.toFixed(2)}R
            </div>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No journal entries yet.</p>
        ) : (
          <div className="space-y-3">
            {entries.map((e) => (
              <div key={e.id} className="rounded-md border bg-muted/30 p-3">
                {e.entry_reason && (
                  <div className="mb-2">
                    <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Entry reason
                    </div>
                    <p className="mt-0.5 text-sm">{e.entry_reason}</p>
                  </div>
                )}
                {e.exit_reason && (
                  <div className="mb-2">
                    <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Exit reason
                    </div>
                    <p className="mt-0.5 text-sm">{e.exit_reason}</p>
                  </div>
                )}
                {e.lessons && (
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Lessons
                    </div>
                    <p className="mt-0.5 text-sm">{e.lessons}</p>
                  </div>
                )}
                {e.rule_adherence_pct !== null && (
                  <div className="mt-2 inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs">
                    <span className="text-muted-foreground">Rule adherence</span>
                    <span className="font-mono font-medium">{e.rule_adherence_pct}%</span>
                  </div>
                )}
                <div className="mt-2 text-[10px] text-muted-foreground">
                  {new Date(e.created_at).toLocaleDateString('en-IN')}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4">
          <AddJournalEntrySheet tradeId={trade.id} ticker={trade.ticker} />
        </div>
      </CardContent>
    </Card>
  );
}

// ----------------------------------------------------------------------------

function AddJournalEntrySheet({ tradeId, ticker }: { tradeId: string; ticker: string }) {
  const [open, setOpen] = useState(false);
  const [entryReason, setEntryReason] = useState('');
  const [exitReason, setExitReason] = useState('');
  const [ruleAdherence, setRuleAdherence] = useState('');
  const [lessons, setLessons] = useState('');

  const upsert = useUpsertJournal();

  async function handleSubmit() {
    if (!entryReason && !exitReason && !lessons) {
      toast.error('Empty entry', { description: 'Fill at least one field.' });
      return;
    }
    try {
      await upsert.mutateAsync({
        tradeId,
        entryReason: entryReason || undefined,
        exitReason: exitReason || undefined,
        ruleAdherencePct: ruleAdherence ? parseFloat(ruleAdherence) : undefined,
        lessons: lessons || undefined,
      });
      toast.success('Journal saved');
      setOpen(false);
      setEntryReason('');
      setExitReason('');
      setRuleAdherence('');
      setLessons('');
    } catch (err) {
      toast.error('Could not save', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button variant="outline" size="sm">
            <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
            Add journal entry
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Journal · {displayTicker(ticker)}</SheetTitle>
          <SheetDescription>
            Douglas-style reflection. Everything is optional, but consistency matters.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Entry reason
            </label>
            <textarea
              value={entryReason}
              onChange={(e) => setEntryReason(e.target.value)}
              rows={3}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="e.g. Stage 2 breakout on volume; sector strong; earnings 30d away"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Exit reason <span className="opacity-60">— on close</span>
            </label>
            <textarea
              value={exitReason}
              onChange={(e) => setExitReason(e.target.value)}
              rows={2}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="e.g. Hit trailing stop / target reached / thesis broken"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Rule adherence (0-100)
            </label>
            <Input
              type="number"
              min="0"
              max="100"
              value={ruleAdherence}
              onChange={(e) => setRuleAdherence(e.target.value)}
              placeholder="90"
            />
            <p className="text-[10px] text-muted-foreground">
              What % of your rules did you follow on this trade?
            </p>
          </div>

          <Separator />

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Lessons</label>
            <textarea
              value={lessons}
              onChange={(e) => setLessons(e.target.value)}
              rows={4}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Douglas: focus on what the market taught you, not the outcome"
            />
          </div>
        </div>

        <SheetFooter className="mt-6">
          <Button onClick={handleSubmit} disabled={upsert.isPending} className="w-full">
            {upsert.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save entry
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// ----------------------------------------------------------------------------

function JournalSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="rounded-lg border bg-card p-6">
          <div className="flex justify-between">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-6 w-24" />
          </div>
          <Skeleton className="mt-4 h-16 w-full" />
        </div>
      ))}
    </div>
  );
}
