import { AppShell } from '@/components/layout/app-shell';
import { AnalyticsView } from '@/components/analytics/analytics-view';

export const metadata = { title: 'Analytics · StockPilot' };

export default function AnalyticsPage() {
  return (
    <AppShell breadcrumbs={<span>Analytics</span>}>
      <div className="space-y-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Performance computed from your logged trades — expectancy, win rate,
            profit factor, realized P&amp;L. Outcomes are consequences; decision
            quality is the metric that matters.
          </p>
        </div>
        <AnalyticsView />
      </div>
    </AppShell>
  );
}
