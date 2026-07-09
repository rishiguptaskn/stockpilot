import { AppShell } from '@/components/layout/app-shell';
import { BacktestView } from '@/components/backtest/backtest-view';

export const metadata = { title: 'Backtest · StockPilot' };

export default function BacktestPage() {
  return (
    <AppShell breadcrumbs={<span>Backtest</span>}>
      <div className="space-y-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Backtest</h1>
          <p className="text-sm text-muted-foreground">
            The trust gate: no live capital until the rules show positive expectancy
            after costs on real history. Runs the actual engine — not a simulation of it.
          </p>
        </div>
        <BacktestView />
      </div>
    </AppShell>
  );
}
