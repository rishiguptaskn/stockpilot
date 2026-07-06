/**
 * tradesService — reads/writes to `public.trades`.
 * RLS-scoped to auth.uid() — only the signed-in user's trades are visible.
 */

import type { Trade } from '@stockpilot/types';
import { getSupabase } from './client';

export interface CreateTradeInput {
  ticker: string;
  entryDate: string; // YYYY-MM-DD
  entryPrice: number;
  stopPrice: number;
  targetPrice?: number;
  shares: number;
  candidateId?: string;
}

export interface CloseTradeInput {
  tradeId: string;
  exitDate: string;
  exitPrice: number;
}

export const tradesService = {
  async listOpen(): Promise<Trade[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('trades')
      .select('*')
      .eq('status', 'open')
      .order('entry_date', { ascending: false });
    if (error) throw error;
    return (data ?? []) as unknown as Trade[];
  },

  async listClosed(limit = 20): Promise<Trade[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('trades')
      .select('*')
      .neq('status', 'open')
      .order('exit_date', { ascending: false, nullsFirst: false })
      .limit(limit);
    if (error) throw error;
    return (data ?? []) as unknown as Trade[];
  },

  async listAll(): Promise<Trade[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('trades')
      .select('*')
      .order('entry_date', { ascending: false });
    if (error) throw error;
    return (data ?? []) as unknown as Trade[];
  },

  async create(input: CreateTradeInput): Promise<Trade> {
    const supabase = getSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabase
      .from('trades')
      .insert({
        user_id: user.id,
        ticker: input.ticker,
        entry_date: input.entryDate,
        entry_price: input.entryPrice,
        stop_price: input.stopPrice,
        target_price: input.targetPrice ?? null,
        shares: input.shares,
        candidate_id: input.candidateId ?? null,
        status: 'open',
      })
      .select('*')
      .single();

    if (error) throw error;
    return data as unknown as Trade;
  },

  /**
   * Updates the stop-loss on an open trade.
   * Enforces rule M9.19: stop can only be tightened, never widened (for long positions).
   */
  async updateStop(tradeId: string, newStop: number): Promise<Trade> {
    const supabase = getSupabase();

    // Fetch existing to enforce rule
    const { data: existing, error: fetchErr } = await supabase
      .from('trades')
      .select('stop_price, status')
      .eq('id', tradeId)
      .single();
    if (fetchErr) throw fetchErr;
    if (existing.status !== 'open') {
      throw new Error('Cannot update stop on a closed trade');
    }
    if (newStop < existing.stop_price) {
      throw new Error(
        `Rule M9.19: stop-loss can only be tightened, never widened. ` +
          `Current stop ₹${existing.stop_price}, requested ₹${newStop}.`,
      );
    }

    const { data, error } = await supabase
      .from('trades')
      .update({ stop_price: newStop })
      .eq('id', tradeId)
      .select('*')
      .single();

    if (error) throw error;
    return data as unknown as Trade;
  },

  async close(input: CloseTradeInput): Promise<Trade> {
    const supabase = getSupabase();

    const { data: existing, error: fetchErr } = await supabase
      .from('trades')
      .select('entry_price, stop_price')
      .eq('id', input.tradeId)
      .single();
    if (fetchErr) throw fetchErr;

    let status: Trade['status'];
    if (input.exitPrice > existing.entry_price) status = 'closed_win';
    else if (input.exitPrice < existing.entry_price) status = 'closed_loss';
    else status = 'closed_breakeven';

    const { data, error } = await supabase
      .from('trades')
      .update({
        exit_date: input.exitDate,
        exit_price: input.exitPrice,
        status,
      })
      .eq('id', input.tradeId)
      .select('*')
      .single();

    if (error) throw error;
    return data as unknown as Trade;
  },
};
