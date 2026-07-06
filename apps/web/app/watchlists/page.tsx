import { ClipboardList } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Watchlists · StockPilot' };

export default function WatchlistsPage() {
  return (
    <PlaceholderPage
      title="Watchlists"
      breadcrumb="Watchlists"
      icon={ClipboardList}
      plannedIn="Month 3"
      description="User-curated lists of stocks to monitor. Rule engine runs against watchlist first each morning."
      features={[
        'Create named watchlists (e.g., "Banking Leaders", "IT Bounce Candidates")',
        'Add/remove stocks from any watchlist',
        'Score every watchlist stock against the ~200-rule engine on demand',
        'Auto-notify when a watchlist stock crosses score threshold',
        'Share watchlist snapshot with a link (v2+)',
      ]}
    />
  );
}
