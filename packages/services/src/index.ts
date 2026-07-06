/**
 * @stockpilot/services — public exports.
 *
 * All data access flows through this package. UI components should never
 * import from @supabase/supabase-js directly.
 *
 * Usage:
 *   1. At app startup, call `initSupabase({ url, key })` with env-derived values.
 *   2. Then use the service objects anywhere.
 */

export { initSupabase, getSupabase, type SupabaseInitOptions } from './client';
export { candidatesService } from './candidates';
export { stocksService } from './stocks';
export { tradesService, type CreateTradeInput, type CloseTradeInput } from './trades';
export { journalService, type UpsertJournalInput } from './journal';
export { watchlistsService, type Watchlist } from './watchlists';
