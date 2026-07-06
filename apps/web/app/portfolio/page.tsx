import { Target } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Portfolio · StockPilot' };

export default function PortfolioPage() {
  return (
    <PlaceholderPage
      title="Portfolio"
      breadcrumb="Portfolio"
      icon={Target}
      plannedIn="Month 4"
      description="Open positions, risk exposure per position, unrealized P&L, sector allocation, cash balance."
      features={[
        'Table of open positions with entry, current price, stop, target, unrealized P&L',
        'Portfolio-level open risk vs Elder 6% cap',
        'Sector concentration bars',
        'Cash allocation percentage',
        'Per-position status: at breakeven, protected profit, trailing stop level',
        'Quick actions: adjust stop, book partial, close position',
      ]}
    />
  );
}
