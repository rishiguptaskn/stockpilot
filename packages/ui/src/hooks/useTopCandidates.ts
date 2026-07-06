/**
 * useTopCandidates — React Query hook wrapping candidatesService.
 *
 * Layer 3 of the Hook → Service → RPC → Supabase pattern (see PLAN.md § 13).
 * Called from UI components. Handles caching, loading, error, refetch.
 */

import { useQuery } from '@tanstack/react-query';
import { candidatesService } from '@stockpilot/services';

const FIVE_MINUTES = 5 * 60 * 1000;

export function useTopCandidates(date: Date, minScore = 90) {
  return useQuery({
    queryKey: ['candidates', 'top', date.toISOString().slice(0, 10), minScore] as const,
    queryFn: () => candidatesService.getTopByDate(date, minScore),
    staleTime: FIVE_MINUTES,
  });
}
