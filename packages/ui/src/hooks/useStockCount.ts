/**
 * useStockCount — number of active stocks in the tradable universe.
 * Reads from Supabase `public.stocks` via stocksService.
 */

import { useQuery } from '@tanstack/react-query';
import { stocksService } from '@stockpilot/services';

const ONE_HOUR = 60 * 60 * 1000;

export function useStockCount() {
  return useQuery({
    queryKey: ['stocks', 'count'] as const,
    queryFn: () => stocksService.count(),
    staleTime: ONE_HOUR,
  });
}
