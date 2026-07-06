/**
 * journalService — Douglas-style trade journal.
 * RLS-scoped to auth.uid().
 */

import type { JournalEntry } from '@stockpilot/types';
import { getSupabase } from './client';

export interface UpsertJournalInput {
  tradeId: string;
  entryReason?: string;
  exitReason?: string;
  ruleAdherencePct?: number;
  lessons?: string;
}

export const journalService = {
  async listByTrade(tradeId: string): Promise<JournalEntry[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('journal_entries')
      .select('*')
      .eq('trade_id', tradeId)
      .order('created_at', { ascending: false });
    if (error) throw error;
    return (data ?? []) as unknown as JournalEntry[];
  },

  async listMine(limit = 50): Promise<JournalEntry[]> {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from('journal_entries')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);
    if (error) throw error;
    return (data ?? []) as unknown as JournalEntry[];
  },

  async upsert(input: UpsertJournalInput): Promise<JournalEntry> {
    const supabase = getSupabase();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) throw new Error('Not authenticated');

    const { data, error } = await supabase
      .from('journal_entries')
      .insert({
        trade_id: input.tradeId,
        user_id: user.id,
        entry_reason: input.entryReason ?? null,
        exit_reason: input.exitReason ?? null,
        rule_adherence_pct: input.ruleAdherencePct ?? null,
        lessons: input.lessons ?? null,
      })
      .select('*')
      .single();

    if (error) throw error;
    return data as unknown as JournalEntry;
  },
};
