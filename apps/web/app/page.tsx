import {
  ActivitySquare,
  AlertTriangle,
  Landmark,
  ShieldCheck,
} from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { StatCard } from '@/components/stat-card';
import { MarketStatusCard } from '@/components/dashboard/market-status-card';
import { CandidatesTable } from '@/components/dashboard/candidates-table';
import { SectorStrip } from '@/components/dashboard/sector-strip';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// ----------------------------------------------------------------------------
// MOCK DATA — will be replaced by real data once Supabase migration is applied
// and the FastAPI rule engine is running. Kept clearly separated for easy removal.
// ----------------------------------------------------------------------------

const MOCK_MARKET = {
  verdict: 'bullish' as const,
  score: 82,
  checks: [
    { label: 'Nifty > 200 SMA', status: 'pass' as const, detail: '+8.4%' },
    { label: 'Nifty > 50 SMA', status: 'pass' as const, detail: '+3.1%' },
    { label: '50 SMA > 200 SMA', status: 'pass' as const },
    { label: 'Distribution days ≤ 5 (20d)', status: 'pass' as const, detail: '2 / 20' },
    { label: 'FII net flow (10d)', status: 'pass' as const, detail: '+₹4,210 cr' },
    { label: 'India VIX < 20', status: 'neutral' as const, detail: '19.8' },
  ],
};

const MOCK_SECTORS = [
  { name: 'Banking', pctChange: 1.42, rank: 1 },
  { name: 'Capital Goods', pctChange: 1.18, rank: 2 },
  { name: 'Pharma', pctChange: 0.94, rank: 3 },
  { name: 'Auto', pctChange: 0.61, rank: 4 },
  { name: 'IT', pctChange: -0.38, rank: 15 },
  { name: 'FMCG', pctChange: -0.72, rank: 17 },
];

const MOCK_CANDIDATES = [
  {
    ticker: 'RELIANCE',
    name: 'Reliance Industries Ltd',
    sector: 'Energy',
    score: 94.2,
    entry: 1287.5,
    stop: 1198.75,
    target: 1465.0,
    rr: 2.0,
    pattern: 'VCP',
  },
  {
    ticker: 'HDFCBANK',
    name: 'HDFC Bank Ltd',
    sector: 'Banking',
    score: 92.6,
    entry: 1723.1,
    stop: 1642.4,
    target: 1888.0,
    rr: 2.0,
    pattern: 'Flat Base',
  },
  {
    ticker: 'INFY',
    name: 'Infosys Ltd',
    sector: 'IT',
    score: 91.4,
    entry: 1856.25,
    stop: 1780.0,
    target: 2010.5,
    rr: 2.0,
    pattern: 'Cup & Handle',
  },
  {
    ticker: 'TATAMOTORS',
    name: 'Tata Motors Ltd',
    sector: 'Auto',
    score: 90.8,
    entry: 812.4,
    stop: 776.9,
    target: 895.0,
    rr: 2.3,
    pattern: 'Bull Flag',
  },
];

// ----------------------------------------------------------------------------

export default function TodayPage() {
  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <AppShell
      breadcrumbs={
        <div className="flex items-center gap-2">
          <span>Today</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground">{today}</span>
        </div>
      }
      actions={
        <>
          <Button variant="outline" size="sm">
            Run workflow
          </Button>
          <Button size="sm">Add trade</Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              Good morning, Rishi
            </h1>
            <Badge variant="outline" className="ml-2 font-mono">
              MOCK DATA
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Overview of today&apos;s market environment and top swing candidates
            from the rule engine.
          </p>
        </div>

        {/* Stat row */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard
            label="Capital"
            value="₹5,00,000"
            hint="Available"
            icon={<Landmark className="h-4 w-4" />}
          />
          <StatCard
            label="Open positions"
            value="0 / 5"
            hint="Max 5 concurrent"
            icon={<ActivitySquare className="h-4 w-4" />}
          />
          <StatCard
            label="Open risk"
            value="0.00%"
            trend="flat"
            trendLabel="of 6% cap"
            icon={<ShieldCheck className="h-4 w-4" />}
          />
          <StatCard
            label="Candidates today"
            value="4"
            trend="up"
            trendLabel="+2 vs yesterday"
            icon={<AlertTriangle className="h-4 w-4" />}
          />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <MarketStatusCard {...MOCK_MARKET} />
          </div>
          <div className="space-y-4 lg:col-span-2">
            <div>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Sector strength (today, top &amp; bottom)
              </h2>
              <SectorStrip sectors={MOCK_SECTORS} />
            </div>
          </div>
        </div>

        {/* Candidates table */}
        <CandidatesTable rows={MOCK_CANDIDATES} />

        {/* Footer disclaimer */}
        <div className="rounded-md border border-border/60 bg-muted/30 p-4 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Reminder:</span> This is
          decision-support, not investment advice. Every referenced author
          (O&apos;Neil, Minervini, Weinstein, Elder, Douglas) explicitly states
          that losing trades are unavoidable — edge comes from probability and
          discipline over many trades, not certainty on any single trade.
        </div>
      </div>
    </AppShell>
  );
}
