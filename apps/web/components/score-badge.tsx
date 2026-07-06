import { cn } from '@/lib/utils';

/**
 * Score badge for the ~200-rule aggregate score (0-100).
 * Color-mapped per PLAN.md § 11 component polish standards:
 *   >= 90  → bullish (emerald)  — candidate
 *   >= 75  → warning (amber)    — watch
 *   <  75  → bearish (rose)     — reject
 */
export interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export function ScoreBadge({
  score,
  size = 'md',
  label,
  className,
}: ScoreBadgeProps) {
  const tone = score >= 90 ? 'bullish' : score >= 75 ? 'warning' : 'bearish';
  const rounded = score.toFixed(1);

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-md border font-mono font-medium tabular-nums',
        size === 'sm' && 'px-1.5 py-0.5 text-xs',
        size === 'md' && 'px-2 py-1 text-sm',
        size === 'lg' && 'px-3 py-1.5 text-base',
        tone === 'bullish' &&
          'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
        tone === 'warning' &&
          'border-amber-500/30 bg-amber-500/10 text-amber-400',
        tone === 'bearish' &&
          'border-rose-500/30 bg-rose-500/10 text-rose-400',
        className,
      )}
      aria-label={label ? `${label}: ${rounded}` : `Score ${rounded}`}
    >
      {label && (
        <span className="font-sans text-[10px] uppercase tracking-wider opacity-70">
          {label}
        </span>
      )}
      <span>{rounded}</span>
    </div>
  );
}
