import { Cog } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Settings · StockPilot' };

export default function SettingsPage() {
  return (
    <PlaceholderPage
      title="Settings"
      breadcrumb="Settings"
      icon={Cog}
      plannedIn="Month 4"
      description="Trading parameters, capital, theme preferences, notification channels."
      features={[
        'Trading capital (₹)',
        'Risk per trade (% — Elder default 2%)',
        'Max portfolio open risk (% — Elder default 6%)',
        'Max open positions (default 5)',
        'Aggregate score threshold (default 90)',
        'Data source: yfinance (v1) / Kite Connect / Upstox / Fyers',
        'Theme: dark / light / system',
        'Notification channels',
      ]}
    />
  );
}
