'use client';

import { createBrowserClient } from '@supabase/ssr';

/**
 * Browser-side Supabase client. Uses cookies to persist auth session so that
 * server-side rendering can also see the auth state.
 *
 * Only for client components (auth forms, sign-in triggers, etc.).
 * Application data reads still go through @stockpilot/services.
 */
export function getBrowserSupabase() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}
