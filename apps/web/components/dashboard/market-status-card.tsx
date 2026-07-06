import { CheckCircle2, XCircle, MinusCircle, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

export interface MarketCheckItem {
  label: string;
  status: 'pass' | 'fail' | 'neutral';
  detail?: string;
}

export interface MarketStatusCardProps {
  verdict: 'bullish' | 'neutral' | 'bearish';
  score: number;
  checks: MarketCheckItem[];
}

const VERDICT_STYLES = {
  bullish: {
    badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    label: 'Bullish',
  },
  neutral: {
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    label: 'Neutral',
  },
  bearish: {
    badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    label: 'Bearish',
  },
} as const;

export function MarketStatusCard({
  verdict,
  score,
  checks,
}: MarketStatusCardProps) {
  const style = VERDICT_STYLES[verdict];
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-base font-medium text-muted-foreground">
              <TrendingUp className="mr-1.5 inline-block h-3.5 w-3.5" />
              Market Environment
            </CardTitle>
            <p className="font-mono text-3xl font-semibold tabular-nums">
              {score.toFixed(0)}
              <span className="text-lg font-normal text-muted-foreground">/100</span>
            </p>
          </div>
          <Badge variant="outline" className={cn('font-medium', style.badge)}>
            {style.label}
          </Badge>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="pt-4">
        <ul className="space-y-2 text-sm">
          {checks.map((c) => (
            <li key={c.label} className="flex items-start gap-2">
              {c.status === 'pass' && (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
              )}
              {c.status === 'fail' && (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
              )}
              {c.status === 'neutral' && (
                <MinusCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              )}
              <div className="flex-1">
                <span
                  className={cn(
                    c.status === 'pass' && 'text-foreground',
                    c.status === 'fail' && 'text-foreground',
                    c.status === 'neutral' && 'text-muted-foreground',
                  )}
                >
                  {c.label}
                </span>
                {c.detail && (
                  <span className="ml-2 font-mono text-xs text-muted-foreground">
                    {c.detail}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
