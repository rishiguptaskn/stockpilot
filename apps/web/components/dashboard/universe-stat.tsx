'use client';

import { Globe2 } from 'lucide-react';
import { useStockCount } from '@stockpilot/ui';
import { StatCard } from '@/components/stat-card';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * Live count of stocks in the tradable universe.
 * Reads from Supabase via stocksService → useStockCount → TanStack Query.
 * Demonstrates the Hook → Service → RPC → Supabase pattern end-to-end.
 */
export function UniverseStat() {
  const { data, isLoading, error } = useStockCount();

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="mt-2 h-7 w-16" />
        <Skeleton className="mt-1 h-3 w-24" />
      </div>
    );
  }

  if (error) {
    return (
      <StatCard
        label="Universe"
        value="—"
        hint="Could not load"
        icon={<Globe2 className="h-4 w-4" />}
      />
    );
  }

  const count = data ?? 0;
  return (
    <StatCard
      label="Universe"
      value={count.toString()}
      hint={count > 0 ? 'NSE stocks (live from Supabase)' : 'No stocks seeded'}
      icon={<Globe2 className="h-4 w-4" />}
    />
  );
}
