import { AppShell } from '@/components/layout/app-shell';
import { JournalView } from '@/components/journal/journal-view';

export const metadata = { title: 'Journal · StockPilot' };

export default function JournalPage() {
  return (
    <AppShell breadcrumbs={<span>Journal</span>}>
      <div className="mb-6 space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Journal</h1>
        <p className="text-sm text-muted-foreground">
          Every trade documented. Douglas-style reflection. Track your process, not just the P&L.
        </p>
      </div>
      <JournalView />
    </AppShell>
  );
}
