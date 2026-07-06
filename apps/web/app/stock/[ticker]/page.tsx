import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { TradingViewChart } from '@/components/stock/tradingview-chart';
import { getServerSupabase } from '@/lib/supabase/server';

interface Params {
  ticker: string;
}

export async function generateMetadata({ params }: { params: Promise<Params> }) {
  const { ticker } = await params;
  return { title: `${ticker.replace('.NS', '')} · StockPilot` };
}

export default async function StockDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { ticker: rawTicker } = await params;
  const ticker = decodeURIComponent(rawTicker).toUpperCase();
  const normalizedTicker = ticker.includes('.') ? ticker : `${ticker}.NS`;

  const supabase = await getServerSupabase();
  const { data: stock } = await supabase
    .from('stocks')
    .select('*')
    .eq('ticker', normalizedTicker)
    .maybeSingle();

  if (!stock) {
    notFound();
  }

  const tvSymbol = `NSE:${normalizedTicker.replace('.NS', '')}`;

  return (
    <AppShell
      breadcrumbs={
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="text-muted-foreground hover:text-foreground"
          >
            Today
          </Link>
          <span className="text-muted-foreground/50">/</span>
          <span>{normalizedTicker.replace('.NS', '')}</span>
        </div>
      }
      actions={
        <Button
          variant="outline"
          size="sm"
          render={
            <a
              href={`https://groww.in/stocks/${normalizedTicker.replace('.NS', '').toLowerCase()}`}
              target="_blank"
              rel="noopener noreferrer"
            />
          }
        >
          Open in Groww
          <ExternalLink className="ml-1.5 h-3 w-3" />
        </Button>
      }
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <Link
              href="/"
              className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to Today
            </Link>
            <div className="flex items-baseline gap-3">
              <h1 className="font-mono text-3xl font-semibold tracking-tight">
                {normalizedTicker.replace('.NS', '')}
              </h1>
              <span className="text-sm text-muted-foreground">{stock.name}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge variant="outline">{stock.sector ?? '—'}</Badge>
              {stock.industry && (
                <Badge variant="outline" className="text-muted-foreground">
                  {stock.industry}
                </Badge>
              )}
              <Badge variant="outline" className="font-mono">
                {stock.exchange}
              </Badge>
            </div>
          </div>
        </div>

        {/* Chart */}
        <Card className="overflow-hidden p-0">
          <TradingViewChart symbol={tvSymbol} />
        </Card>

        {/* Rule breakdown placeholder */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">
                Aggregate score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="font-mono text-3xl font-semibold tabular-nums">
                — <span className="text-lg text-muted-foreground">/100</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Needs rule engine + price data ingestion. Coming when Modules 2–10 ship.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">
                Detected patterns
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">—</p>
              <p className="mt-1 text-xs text-muted-foreground">
                VCP / Cup&amp;Handle / Stage 2 / Bull Flag detection ships with pattern
                detectors module.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">Verdict</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="outline" className="border-zinc-500/30 bg-zinc-500/10">
                Not scored yet
              </Badge>
              <p className="mt-2 text-xs text-muted-foreground">
                Verdict = candidate (≥ 90) · watch (85-89) · reject (&lt; 75)
              </p>
            </CardContent>
          </Card>
        </div>

        <Separator />

        {/* Rule module breakdown skeleton */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Per-module scores</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="grid grid-cols-1 divide-y divide-border">
              {[
                { id: 'M1', name: 'Market Environment', weight: 15 },
                { id: 'M2', name: 'Sector Strength', weight: 10 },
                { id: 'M3', name: 'Fundamentals (CAN SLIM)', weight: 15 },
                { id: 'M4', name: 'Technical Analysis', weight: 15 },
                { id: 'M5', name: 'Moving Averages', weight: 10 },
                { id: 'M6', name: 'Momentum', weight: 5 },
                { id: 'M7', name: 'Volume Analysis', weight: 10 },
                { id: 'M8', name: 'News & Events', weight: 5 },
                { id: 'M9', name: 'Risk Management', weight: 10 },
                { id: 'M10', name: 'Portfolio Fit', weight: 5 },
              ].map((m) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between px-6 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-muted-foreground">
                      {m.id}
                    </span>
                    <span className="text-sm">{m.name}</span>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      weight {m.weight}
                    </Badge>
                  </div>
                  <span className="font-mono text-sm tabular-nums text-muted-foreground">
                    —/100
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
