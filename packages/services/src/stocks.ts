/**
 * stocksService — reads from `public.stocks` (public reference data).
 *
 * Layer 2 of the Hook → Service → RPC → Supabase pattern (see PLAN.md § 13).
 */

import type { Stock } from '@stockpilot/types';
import { getSupabase } from './client';

export const stocksService = {
  /**
   * Total count of active stocks in the tradable universe.
   */
  async count(): Promise<number> {
    const supabase = getSupabase();
    const { count, error } = await supabase
      .from('stocks')
      .select('*', { count: 'exact', head: true })
      .eq('is_active', true);

    if (error) throw error;
    return count ?? 0;
  },

  /**
   * List all active stocks, ordered by ticker.
   */
  async list(): Promise<Stock[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('stocks')
      .select('ticker, name, sector, industry, exchange')
      .eq('is_active', true)
      .order('ticker');

    if (error) throw error;
    return (data ?? []) as unknown as Stock[];
  },

  /**
   * Get one stock by ticker.
   */
  async getByTicker(ticker: string): Promise<Stock | null> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('stocks')
      .select('ticker, name, sector, industry, exchange')
      .eq('ticker', ticker)
      .maybeSingle();

    if (error) throw error;
    return (data as unknown as Stock) ?? null;
  },
};
