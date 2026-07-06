import { cn } from '@/lib/utils';

export interface SectorTile {
  name: string;
  pctChange: number;
  rank: number;
}

export interface SectorStripProps {
  sectors: SectorTile[];
}

export function SectorStrip({ sectors }: SectorStripProps) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      {sectors.map((s) => {
        const positive = s.pctChange >= 0;
        return (
          <div
            key={s.name}
            className={cn(
              'rounded-md border p-2.5 transition-colors',
              positive
                ? 'border-emerald-500/20 bg-emerald-500/5'
                : 'border-rose-500/20 bg-rose-500/5',
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">{s.name}</span>
              <span className="text-[10px] text-muted-foreground">#{s.rank}</span>
            </div>
            <div
              className={cn(
                'mt-1 font-mono text-sm font-semibold tabular-nums',
                positive ? 'text-emerald-400' : 'text-rose-400',
              )}
            >
              {positive ? '+' : ''}
              {s.pctChange.toFixed(2)}%
            </div>
          </div>
        );
      })}
    </div>
  );
}
