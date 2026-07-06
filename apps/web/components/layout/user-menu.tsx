'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LogIn, LogOut, User as UserIcon } from 'lucide-react';
import { getBrowserSupabase } from '@/lib/supabase/browser';
import {
  SidebarMenuButton,
} from '@/components/ui/sidebar';
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface UserMenuProps {
  initialEmail: string | null;
  initialName: string | null;
}

export function UserMenu({ initialEmail, initialName }: UserMenuProps) {
  const router = useRouter();
  const [email, setEmail] = useState(initialEmail);
  const [name, setName] = useState(initialName);

  useEffect(() => {
    const supabase = getBrowserSupabase();
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setEmail(session?.user?.email ?? null);
      setName((session?.user?.user_metadata?.full_name as string) ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  async function handleSignOut() {
    const supabase = getBrowserSupabase();
    await supabase.auth.signOut();
    router.push('/signin');
    router.refresh();
  }

  const initials = (name ?? email ?? 'US')
    .split(/[@\s.]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
    .slice(0, 2) || 'US';

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <SidebarMenuButton
            size="lg"
            className="data-[state=open]:bg-sidebar-accent"
          />
        }
      >
        <Avatar className="h-8 w-8 rounded-md">
          <AvatarImage src="" alt="" />
          <AvatarFallback className="rounded-md bg-zinc-800 text-xs font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex flex-col text-left leading-tight group-data-[collapsible=icon]:hidden">
          <span className="truncate text-sm font-medium">
            {name ?? (email ? email.split('@')[0] : 'Signed out')}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {email ?? 'Sign in to sync trades'}
          </span>
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="right" align="end" className="w-56">
        <DropdownMenuLabel>
          {email ? 'Account' : 'Not signed in'}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {email ? (
          <>
            <DropdownMenuItem
              render={
                <Link href="/settings">
                  <UserIcon className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              }
            />
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </>
        ) : (
          <>
            <DropdownMenuItem
              render={
                <Link href="/signin">
                  <LogIn className="mr-2 h-4 w-4" />
                  Sign in
                </Link>
              }
            />
            <DropdownMenuItem
              render={
                <Link href="/signup">
                  <UserIcon className="mr-2 h-4 w-4" />
                  Create account
                </Link>
              }
            />
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
