import { Newspaper } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'News · StockPilot' };

export default function NewsPage() {
  return (
    <PlaceholderPage
      title="News feed"
      breadcrumb="News feed"
      icon={Newspaper}
      plannedIn="Month 4"
      description="Filtered news feed for portfolio holdings and watchlist. Claude API interprets sentiment and significance."
      features={[
        'Aggregated news for portfolio + watchlist tickers',
        'Claude-scored sentiment (-1 to +1) with rationale',
        'Category tags: earnings, regulatory, mgmt, corp action, macro',
        'F&O ban list, GSM/ASM watchlist per NSE',
        'RBI policy meetings, budget calendar, key macro events',
        'Configurable notifications on significant news',
      ]}
    />
  );
}
