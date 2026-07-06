'use client';

/**
 * Client-side providers.
 *
 * - Initializes the Supabase client from NEXT_PUBLIC_ env vars (safe to expose;
 *   RLS protects the data).
 * - Wraps the app in QueryClientProvider (TanStack Query).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect, type ReactNode } from 'react';
import { initSupabase } from '@stockpilot/services';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!;

// Init at module load (Next.js inlines NEXT_PUBLIC_ vars at build time)
if (typeof window !== 'undefined' && SUPABASE_URL && SUPABASE_KEY) {
  try {
    initSupabase({ url: SUPABASE_URL, key: SUPABASE_KEY });
  } catch {
    // already initialized — safe to ignore during Fast Refresh
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 min
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  useEffect(() => {
    // Guard for server → client transition
    if (SUPABASE_URL && SUPABASE_KEY) {
      try {
        initSupabase({ url: SUPABASE_URL, key: SUPABASE_KEY });
      } catch {
        /* already initialized */
      }
    }
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
