/**
 * watchlistsService — user-curated stock lists.
 * RLS-scoped to auth.uid().
 */

import { getSupabase } from './client';

export interface Watchlist {
  id: string;
  user_id: string;
  name: string;
  tickers: string[];
  created_at: string;
  updated_at: string;
}

export const watchlistsService = {
  async listMine(): Promise<Watchlist[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('watchlists')
      .select('*')
      .order('created_at', { ascending: true });
    if (error) throw error;
    return (data ?? []) as unknown as Watchlist[];
  },

  async create(name: string, tickers: string[] = []): Promise<Watchlist> {
    const supabase = getSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabase
      .from('watchlists')
      .insert({
        user_id: user.id,
        name,
        tickers,
      })
      .select('*')
      .single();

    if (error) throw error;
    return data as unknown as Watchlist;
  },

  async addTicker(watchlistId: string, ticker: string): Promise<Watchlist> {
    const supabase = getSupabase();
    const { data: existing, error: fetchErr } = await supabase
      .from('watchlists')
      .select('tickers')
      .eq('id', watchlistId)
      .single();
    if (fetchErr) throw fetchErr;

    const current = (existing.tickers as string[]) ?? [];
    if (current.includes(ticker)) return existing as unknown as Watchlist;

    const { data, error } = await supabase
      .from('watchlists')
      .update({ tickers: [...current, ticker] })
      .eq('id', watchlistId)
      .select('*')
      .single();
    if (error) throw error;
    return data as unknown as Watchlist;
  },

  async removeTicker(watchlistId: string, ticker: string): Promise<Watchlist> {
    const supabase = getSupabase();
    const { data: existing, error: fetchErr } = await supabase
      .from('watchlists')
      .select('tickers')
      .eq('id', watchlistId)
      .single();
    if (fetchErr) throw fetchErr;

    const current = (existing.tickers as string[]) ?? [];
    const { data, error } = await supabase
      .from('watchlists')
      .update({ tickers: current.filter((t) => t !== ticker) })
      .eq('id', watchlistId)
      .select('*')
      .single();
    if (error) throw error;
    return data as unknown as Watchlist;
  },

  async delete(watchlistId: string): Promise<void> {
    const supabase = getSupabase();
    const { error } = await supabase.from('watchlists').delete().eq('id', watchlistId);
    if (error) throw error;
  },
};
