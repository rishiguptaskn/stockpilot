import { AppShell } from '@/components/layout/app-shell';
import { PortfolioView } from '@/components/portfolio/portfolio-view';
import { AddTradeDialog } from '@/components/trades/add-trade-dialog';

export const metadata = { title: 'Portfolio · StockPilot' };

export default function PortfolioPage() {
  return (
    <AppShell
      breadcrumbs={<span>Portfolio</span>}
      actions={<AddTradeDialog />}
    >
      <div className="space-y-2 mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Portfolio</h1>
        <p className="text-sm text-muted-foreground">
          Open positions, portfolio-level risk (Elder 6% rule), and quick actions.
        </p>
      </div>
      <PortfolioView />
    </AppShell>
  );
}
