import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { watchlistsService } from '@stockpilot/services';

export function useMyWatchlists() {
  return useQuery({
    queryKey: ['watchlists', 'mine'] as const,
    queryFn: () => watchlistsService.listMine(),
    staleTime: 60 * 1000,
  });
}

export function useCreateWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, tickers = [] }: { name: string; tickers?: string[] }) =>
      watchlistsService.create(name, tickers),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useAddTickerToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ watchlistId, ticker }: { watchlistId: string; ticker: string }) =>
      watchlistsService.addTicker(watchlistId, ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useRemoveTickerFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ watchlistId, ticker }: { watchlistId: string; ticker: string }) =>
      watchlistsService.removeTicker(watchlistId, ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useDeleteWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (watchlistId: string) => watchlistsService.delete(watchlistId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}
