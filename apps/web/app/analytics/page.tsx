import { BarChart3 } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Analytics · StockPilot' };

export default function AnalyticsPage() {
  return (
    <PlaceholderPage
      title="Analytics"
      breadcrumb="Analytics"
      icon={BarChart3}
      plannedIn="Month 4"
      description="Aggregate performance metrics — win rate, R:R distribution, drawdown, per-rule performance over time."
      features={[
        'Equity curve chart',
        'Win rate, average win, average loss, profit factor',
        'Maximum drawdown and current drawdown from peak',
        'R:R distribution histogram',
        'Per-rule performance: which rules predict best outcomes',
        'Rule-adherence percentage over time',
        'Comparison of returns vs Nifty 50',
      ]}
    />
  );
}
