/**
 * candidatesService — reads/writes to `public.trade_candidates`.
 *
 * Layer 2 of the Hook → Service → RPC → Supabase pattern (see PLAN.md § 13).
 * Called by hooks in @stockpilot/ui/hooks. Never called directly from components.
 */

import type { TradeCandidate } from '@stockpilot/types';
import { getSupabase } from './client.js';

export const candidatesService = {
  /**
   * Returns top-scoring candidates for a given date, above `minScore`.
   */
  async getTopByDate(date: Date, minScore = 90): Promise<TradeCandidate[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('trade_candidates')
      .select('*')
      .eq('candidate_date', date.toISOString().slice(0, 10))
      .gte('aggregate_score', minScore)
      .order('aggregate_score', { ascending: false })
      .limit(20);

    if (error) throw error;
    return (data ?? []) as unknown as TradeCandidate[];
  },

  /**
   * Fetch a single candidate by id, including its full rule-evaluation trail.
   */
  async getById(id: string): Promise<TradeCandidate | null> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('trade_candidates')
      .select('*')
      .eq('id', id)
      .maybeSingle();

    if (error) throw error;
    return (data as unknown as TradeCandidate) ?? null;
  },
};
