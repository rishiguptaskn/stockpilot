import { AppShell } from '@/components/layout/app-shell';
import { WatchlistsView } from '@/components/watchlists/watchlists-view';

export const metadata = { title: 'Watchlists · StockPilot' };

export default function WatchlistsPage() {
  return (
    <AppShell breadcrumbs={<span>Watchlists</span>}>
      <div className="mb-6 space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Watchlists</h1>
        <p className="text-sm text-muted-foreground">
          Curated stock lists to focus your attention. The rule engine runs against your
          watchlists first each morning.
        </p>
      </div>
      <WatchlistsView />
    </AppShell>
  );
}
