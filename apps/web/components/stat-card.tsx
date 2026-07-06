import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';

/**
 * A compact metric card. Label on top, monospace value below, optional trend.
 */
export interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  trend?: 'up' | 'down' | 'flat';
  trendLabel?: string;
  icon?: ReactNode;
  className?: string;
}

export function StatCard({
  label,
  value,
  hint,
  trend,
  trendLabel,
  icon,
  className,
}: StatCardProps) {
  return (
    <Card className={cn('gap-2 py-4', className)}>
      <CardContent className="px-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          {icon && (
            <span className="text-muted-foreground" aria-hidden="true">
              {icon}
            </span>
          )}
        </div>
        <div className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums text-foreground">
          {value}
        </div>
        {(trendLabel || hint) && (
          <div className="mt-1 flex items-center gap-1 text-xs">
            {trend && (
              <span
                className={cn(
                  'font-mono font-medium',
                  trend === 'up' && 'text-emerald-400',
                  trend === 'down' && 'text-rose-400',
                  trend === 'flat' && 'text-muted-foreground',
                )}
              >
                {trend === 'up' ? '▲' : trend === 'down' ? '▼' : '■'}
              </span>
            )}
            {trendLabel && (
              <span
                className={cn(
                  trend === 'up' && 'text-emerald-400',
                  trend === 'down' && 'text-rose-400',
                  !trend && 'text-muted-foreground',
                )}
              >
                {trendLabel}
              </span>
            )}
            {hint && <span className="text-muted-foreground">{hint}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
