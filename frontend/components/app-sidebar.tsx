"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Briefcase,
  ClipboardCheck,
  History,
  LayoutDashboard,
  Newspaper,
  Receipt,
  Scale,
  Settings,
} from "lucide-react";

import { NavUser } from "@/components/nav-user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";

const NAV_SECTIONS = [
  {
    label: "Portfolio",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/chatbot", label: "AI Chatbot", icon: Bot },
      { href: "/assets", label: "Asset View", icon: Briefcase },
      { href: "/transactions", label: "Transactions", icon: Receipt },
    ],
  },
  {
    label: "Compliance",
    items: [
      { href: "/legal-docs", label: "Legal Docs", icon: Scale },
      { href: "/approvals", label: "Approvals", icon: ClipboardCheck },
      { href: "/audit", label: "Audit Trail", icon: History },
      { href: "/news", label: "Market News", icon: Newspaper },
    ],
  },
  {
    label: "Sistem",
    items: [{ href: "/settings", label: "Settings", icon: Settings }],
  },
];

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-chart-2/15 border border-chart-2/30">
                <span className="text-chart-2 text-[10px] font-black font-mono">A</span>
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-bold tracking-tight">Astalink</span>
                <span className="truncate text-[10px] text-chart-2 font-mono font-black uppercase tracking-widest">
                  AI
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {NAV_SECTIONS.map(({ label, items }) => (
          <SidebarGroup key={label}>
            <SidebarGroupLabel>{label}</SidebarGroupLabel>
            <SidebarMenu>
              {items.map(({ href, label: itemLabel, icon: Icon }) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton
                    tooltip={itemLabel}
                    isActive={pathname.startsWith(href)}
                    render={<Link href={href} />}
                  >
                    <Icon />
                    <span>{itemLabel}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
