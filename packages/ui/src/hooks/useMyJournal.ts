import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { journalService, type UpsertJournalInput } from '@stockpilot/services';

export function useMyJournal(limit = 50) {
  return useQuery({
    queryKey: ['journal', 'mine', limit] as const,
    queryFn: () => journalService.listMine(limit),
    staleTime: 30 * 1000,
  });
}

export function useJournalByTrade(tradeId: string | undefined) {
  return useQuery({
    queryKey: ['journal', 'trade', tradeId] as const,
    queryFn: () => journalService.listByTrade(tradeId!),
    enabled: Boolean(tradeId),
    staleTime: 30 * 1000,
  });
}

export function useUpsertJournal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: UpsertJournalInput) => journalService.upsert(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['journal'] }),
  });
}
