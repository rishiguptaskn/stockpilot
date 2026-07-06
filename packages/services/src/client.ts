/**
 * Supabase client — single source of truth for all data access.
 *
 * Apps that consume this service (apps/web) initialize the client once at
 * startup by calling `initSupabase({ url, key })`. All downstream services
 * (candidatesService, etc.) then use `getSupabase()` internally.
 *
 * This avoids reading process.env from a shared package (which couples the
 * package to a specific runtime like Next.js). Instead, the app provides its
 * env-derived values explicitly.
 */

import { createClient, type SupabaseClient } from '@supabase/supabase-js';

let client: SupabaseClient | null = null;

export interface SupabaseInitOptions {
  url: string;
  key: string;
  /**
   * Whether to persist auth sessions (defaults to true — appropriate for browser).
   * Server-side callers should pass false.
   */
  persistSession?: boolean;
}

export function initSupabase(opts: SupabaseInitOptions): SupabaseClient {
  if (!opts.url) throw new Error('initSupabase: url is required');
  if (!opts.key) throw new Error('initSupabase: key is required');

  client = createClient(opts.url, opts.key, {
    auth: {
      persistSession: opts.persistSession ?? true,
      autoRefreshToken: opts.persistSession ?? true,
      detectSessionInUrl: opts.persistSession ?? true,
    },
  });

  return client;
}

export function getSupabase(): SupabaseClient {
  if (!client) {
    throw new Error(
      'Supabase client not initialized. Call initSupabase({ url, key }) at app startup.',
    );
  }
  return client;
}
