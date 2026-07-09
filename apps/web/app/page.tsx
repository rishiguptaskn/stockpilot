import { AppShell } from '@/components/layout/app-shell';
import { TodayDashboard } from '@/components/dashboard/today-dashboard';
import { AddTradeDialog } from '@/components/trades/add-trade-dialog';

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
      actions={<AddTradeDialog />}
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Today</h1>
          <p className="text-sm text-muted-foreground">
            Live market environment and rule-engine candidates. Every number is
            computed from real data or explicitly labelled as a v1 default.
          </p>
        </div>

        <TodayDashboard />

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
