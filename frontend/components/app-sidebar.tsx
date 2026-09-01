"use client";

import * as React from "react";
import Image from "next/image";
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
  PieChart,
  Receipt,
  Scale,
  Settings,
  Sparkles,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import { NavUser } from "@/components/nav-user";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
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

// Legal Docs is admin-only (server-enforced on GET/POST /api/v1/legal/documents*)
// — this hides the link for everyone else; it's UX polish, not the security boundary.
function isVisible(item: NavItem, isAdmin: boolean): boolean {
  if (!isNavGroup(item) && item.href === "/legal-docs") return isAdmin;
  return true;
}

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Utama",
    items: [{ href: "/dashboard", label: "Dasbor", icon: LayoutDashboard }],
  },
  {
    label: "Portofolio",
    items: [
      // Restored per /impeccable critique (2026-08-27): the Layer 0 allocation
      // gate is the product's own headline differentiator and was previously
      // reachable only via deep link or chat — undiscoverable from nav.
      { href: "/allocation", label: "Alokasi Modal", icon: PieChart },
      { href: "/recommendations", label: "Rekomendasi", icon: Sparkles },
      { href: "/chatbot", label: "Chatbot AI", icon: Bot },
      { href: "/portfolio", label: "Portofolio", icon: Wallet },
      { href: "/transactions", label: "Transaksi", icon: Receipt },
    ],
  },
  {
    label: "Kepatuhan",
    items: [
      { href: "/legal-docs", label: "Dokumen Legal", icon: Scale },
      { href: "/approvals", label: "Persetujuan", icon: ClipboardCheck },
      { href: "/audit", label: "Jejak Audit", icon: History },
      { href: "/news", label: "Berita Pasar", icon: Newspaper },
    ],
  },
  {
    label: "Bisnis",
    items: [
      {
        label: "Bisnis Saya",
        icon: Building2,
        children: [
          { href: "/business", label: "Daftar Bisnis" },
          { href: "/business/detail", label: "Detail Bisnis" },
        ],
      },
    ],
  },
  {
    label: "Sistem",
    items: [{ href: "/settings", label: "Pengaturan", icon: Settings }],
  },
];

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const [openGroups, setOpenGroups] = React.useState<Record<string, boolean>>({});
  const [isAdmin, setIsAdmin] = React.useState(false);

  React.useEffect(() => {
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        const me = await api.getMe(session.access_token);
        setIsAdmin(me.is_admin);
      } catch {
        // Fail closed — stays non-admin, Legal Docs link stays hidden.
      }
    })();
  }, []);

  function isGroupOpen(group: NavGroup): boolean {
    if (group.label in openGroups) return openGroups[group.label];
    return group.children.some((c) => pathname.startsWith(c.href));
  }

  const navSections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => isVisible(item, isAdmin)),
  }));

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center">
                <Image src="/astalink.png" alt="Astalink" width={32} height={32} className="size-8 object-contain" />
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
        <WorkspaceSwitcher />
      </SidebarHeader>

      <SidebarContent>
        {navSections.map(({ label, items }) => (
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
                        {item.children.map((child) => {
                          // For "/business": active when on the list page itself OR any
                          // /business/{uuid} sub-route — but NOT /business/detail (that
                          // belongs to the "Detail Bisnis" item).
                          // For all other sub-items: exact match or strict prefix (child.href + "/").
                          const isActive = child.href === "/business"
                            ? pathname === "/business" || (pathname.startsWith("/business/") && !pathname.startsWith("/business/detail"))
                            : pathname === child.href || pathname.startsWith(child.href + "/");
                          return (
                          <SidebarMenuSubItem key={child.href}>
                            <SidebarMenuSubButton
                              isActive={isActive}
                              render={<Link href={child.href} />}
                            >
                              <span>{child.label}</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                          );
                        })}
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
