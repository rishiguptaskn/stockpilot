import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ExternalLink } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { TradingViewChart } from '@/components/stock/tradingview-chart';
import { AiResearchPanel } from '@/components/stock/ai-research-panel';
import { GraphResearchPanel } from '@/components/stock/graph-research-panel';
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

        {/* Deep research — full LangGraph pass: rule engine + risk gate + AI synthesis.
            Replaces the old placeholder score/pattern/verdict cards with live data. */}
        <GraphResearchPanel ticker={normalizedTicker} />

        <Separator />

        {/* Legacy quick AI analysis (SSE trace of Master + Technical agents) */}
        <AiResearchPanel ticker={normalizedTicker} />
      </div>
    </AppShell>
  );
}
