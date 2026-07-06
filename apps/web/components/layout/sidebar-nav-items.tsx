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
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';

const NAV_GROUPS = [
  {
    label: 'Overview',
    items: [
      { title: 'Today',     href: '/',          Icon: LayoutDashboard },
      { title: 'Portfolio', href: '/portfolio', Icon: Target },
      { title: 'Journal',   href: '/journal',   Icon: BookOpen },
      { title: 'Analytics', href: '/analytics', Icon: BarChart3 },
    ],
  },
  {
    label: 'Research',
    items: [
      { title: 'Watchlists', href: '/watchlists', Icon: ClipboardList },
      { title: 'News feed',  href: '/news',       Icon: Newspaper },
      { title: 'Backtest',   href: '/backtest',   Icon: Sparkles },
    ],
  },
  {
    label: 'System',
    items: [
      { title: 'Rulebook', href: '/rulebook', Icon: ScrollText },
      { title: 'Settings', href: '/settings', Icon: Cog },
    ],
  },
] as const;

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <>
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
                      <item.Icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      ))}
    </>
  );
}
