import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  tradesService,
  type CreateTradeInput,
  type CloseTradeInput,
} from '@stockpilot/services';

export function useOpenTrades() {
  return useQuery({
    queryKey: ['trades', 'open'] as const,
    queryFn: () => tradesService.listOpen(),
    staleTime: 30 * 1000,
  });
}

export function useClosedTrades(limit = 20) {
  return useQuery({
    queryKey: ['trades', 'closed', limit] as const,
    queryFn: () => tradesService.listClosed(limit),
    staleTime: 60 * 1000,
  });
}

export function useAllTrades() {
  return useQuery({
    queryKey: ['trades', 'all'] as const,
    queryFn: () => tradesService.listAll(),
    staleTime: 30 * 1000,
  });
}

export function useCreateTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTradeInput) => tradesService.create(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trades'] }),
  });
}

export function useUpdateTradeStop() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tradeId, newStop }: { tradeId: string; newStop: number }) =>
      tradesService.updateStop(tradeId, newStop),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trades'] }),
  });
}

export function useCloseTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CloseTradeInput) => tradesService.close(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trades'] }),
  });
}
