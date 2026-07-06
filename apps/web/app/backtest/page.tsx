import { Sparkles } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Backtest · StockPilot' };

export default function BacktestPage() {
  return (
    <PlaceholderPage
      title="Backtest"
      breadcrumb="Backtest"
      icon={Sparkles}
      plannedIn="Month 5"
      description="Run any rule set against 5 years of NSE historical data. Validate rule thresholds before live capital."
      features={[
        'Configure: universe, date range, aggregate-score threshold, position sizing rules',
        'Run backtest — Python FastAPI backtester consumes daily OHLCV',
        'Results: equity curve, win rate, R:R distribution, drawdown',
        'Per-rule contribution: which rules added or removed edge',
        'Threshold sensitivity: try minScore 85, 90, 92, 95 and compare',
        'Export trades to CSV for external analysis',
      ]}
    />
  );
}
