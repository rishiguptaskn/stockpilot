import { NextResponse } from 'next/server';
import { getServerSupabase } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const supabase = await getServerSupabase();
  await supabase.auth.signOut();

  return NextResponse.redirect(new URL('/signin', request.url), {
    status: 303,
  });
}
