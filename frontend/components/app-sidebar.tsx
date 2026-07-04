"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Briefcase,
  Building2,
  ChevronRight,
  ClipboardCheck,
  History,
  LayoutDashboard,
  Newspaper,
  Receipt,
  Scale,
  Settings,
  type LucideIcon,
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
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
} from "@/components/ui/sidebar";

type NavLeaf = { href: string; label: string; icon: LucideIcon };
type NavGroup = { label: string; icon: LucideIcon; children: { href: string; label: string }[] };
type NavItem = NavLeaf | NavGroup;

function isNavGroup(item: NavItem): item is NavGroup {
  return "children" in item;
}

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
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
    label: "Business",
    items: [
      {
        label: "Bisnis Saya",
        icon: Building2,
        children: [
          { href: "/business", label: "List Bisnis" },
          { href: "/business/detail", label: "Detail Bisnis" },
        ],
      },
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
  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>({});

  function isGroupOpen(group: NavGroup): boolean {
    if (group.label in openGroups) return openGroups[group.label];
    return group.children.some((c) => pathname.startsWith(c.href));
  }

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
              {items.map((item) =>
                isNavGroup(item) ? (
                  <SidebarMenuItem key={item.label}>
                    <SidebarMenuButton
                      tooltip={item.label}
                      onClick={() =>
                        setOpenGroups((prev) => ({ ...prev, [item.label]: !isGroupOpen(item) }))
                      }
                    >
                      <item.icon />
                      <span>{item.label}</span>
                      <ChevronRight
                        className={`ml-auto size-4 shrink-0 transition-transform ${
                          isGroupOpen(item) ? "rotate-90" : ""
                        }`}
                      />
                    </SidebarMenuButton>
                    {isGroupOpen(item) && (
                      <SidebarMenuSub>
                        {item.children.map((child) => (
                          <SidebarMenuSubItem key={child.href}>
                            <SidebarMenuSubButton
                              isActive={pathname.startsWith(child.href)}
                              render={<Link href={child.href} />}
                            >
                              <span>{child.label}</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        ))}
                      </SidebarMenuSub>
                    )}
                  </SidebarMenuItem>
                ) : (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      tooltip={item.label}
                      isActive={pathname.startsWith(item.href)}
                      render={<Link href={item.href} />}
                    >
                      <item.icon />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              )}
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
