'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { useCreateTrade } from '@stockpilot/ui';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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

const CAPITAL_INR = 500_000;
const MAX_RISK_PCT = 2.0;

/**
 * Add-trade form. Implements Elder 2% rule position sizing inline:
 * shares = floor((CAPITAL × 2%) / (entry - stop))
 * User can override shares but the risk warning shows if outside 2% cap.
 */
export function AddTradeDialog() {
  const [open, setOpen] = useState(false);
  const [ticker, setTicker] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [shares, setShares] = useState('');
  const [manualShares, setManualShares] = useState(false);

  const createTrade = useCreateTrade();

  const parsed = useMemo(() => {
    const entry = parseFloat(entryPrice) || 0;
    const stop = parseFloat(stopPrice) || 0;
    const target = parseFloat(targetPrice) || 0;
    const stopDistance = entry - stop;
    const targetDistance = target > 0 ? target - entry : 0;
    const rr = stopDistance > 0 && targetDistance > 0 ? targetDistance / stopDistance : 0;
    const riskAmount = (CAPITAL_INR * MAX_RISK_PCT) / 100;
    const suggestedShares = stopDistance > 0 ? Math.floor(riskAmount / stopDistance) : 0;
    const actualShares = manualShares ? parseInt(shares || '0', 10) : suggestedShares;
    const actualRisk = actualShares * stopDistance;
    const actualRiskPct = (actualRisk / CAPITAL_INR) * 100;
    return {
      entry,
      stop,
      target,
      stopDistance,
      rr,
      suggestedShares,
      actualShares,
      actualRisk,
      actualRiskPct,
      valid: entry > 0 && stop > 0 && stop < entry,
      stopPct: entry > 0 ? (stopDistance / entry) * 100 : 0,
    };
  }, [entryPrice, stopPrice, targetPrice, shares, manualShares]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!parsed.valid) {
      toast.error('Invalid trade', {
        description: 'Entry price must be > stop-loss.',
      });
      return;
    }
    if (parsed.actualShares <= 0) {
      toast.error('Zero shares', { description: 'Position size is 0.' });
      return;
    }
    if (parsed.stopPct > 8) {
      toast.warning('Stop wider than 8% (rule M9.7)', {
        description: `Stop is ${parsed.stopPct.toFixed(1)}% below entry. O'Neil recommends max 7–8%.`,
      });
    }

    try {
      await createTrade.mutateAsync({
        ticker: ticker.trim().toUpperCase(),
        entryDate: new Date().toISOString().slice(0, 10),
        entryPrice: parsed.entry,
        stopPrice: parsed.stop,
        targetPrice: parsed.target > 0 ? parsed.target : undefined,
        shares: parsed.actualShares,
      });
      toast.success('Trade added', {
        description: `${ticker.toUpperCase()} · ${parsed.actualShares} shares @ ₹${parsed.entry}`,
      });
      setOpen(false);
      // Reset form
      setTicker('');
      setEntryPrice('');
      setStopPrice('');
      setTargetPrice('');
      setShares('');
      setManualShares(false);
    } catch (err) {
      toast.error('Could not add trade', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button size="sm">
            <Plus className="mr-1.5 h-4 w-4" />
            Add trade
          </Button>
        }
      />
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Add trade</SheetTitle>
          <SheetDescription>
            Record a trade you&apos;ve just executed in Groww. Position size uses
            Elder&apos;s 2% rule automatically.
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Ticker
            </label>
            <Input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="RELIANCE.NS"
              required
              className="uppercase"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Entry price (₹)
              </label>
              <Input
                type="number"
                step="0.01"
                value={entryPrice}
                onChange={(e) => setEntryPrice(e.target.value)}
                required
                placeholder="1287.50"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Stop-loss (₹)
              </label>
              <Input
                type="number"
                step="0.01"
                value={stopPrice}
                onChange={(e) => setStopPrice(e.target.value)}
                required
                placeholder="1198.75"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Target (₹) <span className="opacity-60">— optional</span>
            </label>
            <Input
              type="number"
              step="0.01"
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              placeholder="1465.00"
            />
          </div>

          <Separator />

          {/* Position size preview */}
          <div className="rounded-md border bg-muted/30 p-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Capital</span>
              <span className="font-mono tabular-nums">₹5,00,000</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Risk per trade (Elder 2%)</span>
              <span className="font-mono tabular-nums">₹10,000</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Stop distance</span>
              <span className="font-mono tabular-nums">
                {parsed.stopDistance > 0 ? `₹${parsed.stopDistance.toFixed(2)} (${parsed.stopPct.toFixed(1)}%)` : '—'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">R:R ratio</span>
              <span className={`font-mono tabular-nums ${parsed.rr >= 2 ? 'text-emerald-400' : parsed.rr > 0 ? 'text-rose-400' : ''}`}>
                {parsed.rr > 0 ? `1:${parsed.rr.toFixed(1)}` : '—'}
              </span>
            </div>
            <Separator className="my-2" />
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Suggested shares (Elder)</span>
              <span className="font-mono tabular-nums font-semibold">
                {parsed.suggestedShares || '—'}
              </span>
            </div>
            {manualShares && (
              <div className="mt-2 flex items-center justify-between">
                <span className="text-muted-foreground">Actual risk</span>
                <span
                  className={`font-mono tabular-nums ${parsed.actualRiskPct > 2 ? 'text-rose-400' : 'text-emerald-400'}`}
                >
                  {parsed.actualRisk.toFixed(0)} ({parsed.actualRiskPct.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-muted-foreground">
                Shares
              </label>
              <button
                type="button"
                onClick={() => {
                  setManualShares(!manualShares);
                  if (!manualShares) setShares(String(parsed.suggestedShares));
                }}
                className="text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
              >
                {manualShares ? 'Use suggested' : 'Override'}
              </button>
            </div>
            <Input
              type="number"
              value={manualShares ? shares : String(parsed.suggestedShares || '')}
              onChange={(e) => setShares(e.target.value)}
              disabled={!manualShares}
              placeholder="Auto-calculated"
              required
            />
          </div>

          <SheetFooter>
            <Button type="submit" disabled={createTrade.isPending || !parsed.valid} className="w-full">
              {createTrade.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Add trade
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}
