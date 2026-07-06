'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  ClipboardList,
  Cog,
  LayoutDashboard,
  Newspaper,
  ScrollText,
  Sparkles,
  Target,
} from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
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

const NAV_GROUPS = [
  {
    label: 'Overview',
    items: [
      { title: 'Today', href: '/', icon: LayoutDashboard },
      { title: 'Portfolio', href: '/portfolio', icon: Target },
      { title: 'Journal', href: '/journal', icon: BookOpen },
      { title: 'Analytics', href: '/analytics', icon: BarChart3 },
    ],
  },
  {
    label: 'Research',
    items: [
      { title: 'Watchlists', href: '/watchlists', icon: ClipboardList },
      { title: 'News feed', href: '/news', icon: Newspaper },
      { title: 'Backtest', href: '/backtest', icon: Sparkles },
    ],
  },
  {
    label: 'System',
    items: [
      { title: 'Rulebook', href: '/rulebook', icon: ScrollText },
      { title: 'Settings', href: '/settings', icon: Cog },
    ],
  },
] as const;

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-sm">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
              aria-hidden="true"
            >
              <path d="M3 17l6-6 4 4 8-8" />
              <path d="M14 7h7v7" />
            </svg>
          </div>
          <div className="flex flex-col leading-none group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold tracking-tight">StockPilot</span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              v0.1.0 · NSE
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const active =
                    item.href === '/'
                      ? pathname === '/'
                      : pathname.startsWith(item.href);
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        render={<Link href={item.href} />}
                        tooltip={item.title}
                        isActive={active}
                      >
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
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
              <AvatarImage src="" alt="user" />
              <AvatarFallback className="rounded-md bg-zinc-800 text-xs">
                RG
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col text-left leading-tight group-data-[collapsible=icon]:hidden">
              <span className="text-sm font-medium">Signed out</span>
              <span className="text-xs text-muted-foreground">
                Sign in to sync
              </span>
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="end" className="w-56">
            <DropdownMenuLabel>Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>Sign in (v1)</DropdownMenuItem>
            <DropdownMenuItem disabled>Preferences</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
