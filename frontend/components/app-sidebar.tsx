"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { NavUser } from "@/components/nav-user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import {
  ASTA_ACTION,
  isJourneyRouteActive,
  visibleDesktopSections,
} from "@/lib/journey-navigation";

export function AppSidebar({
  pendingApprovals = 0,
  isAdmin = false,
  ...props
}: React.ComponentProps<typeof Sidebar> & {
  pendingApprovals?: number;
  isAdmin?: boolean;
}) {
  const pathname = usePathname();
  const sections = visibleDesktopSections(isAdmin);

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center">
                <Image
                  src="/logo_astalink.png"
                  alt="Astalink"
                  width={32}
                  height={32}
                  className="size-8 object-contain"
                />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-bold tracking-tight">Astalink</span>
                <span className="truncate font-mono text-[10px] font-black uppercase tracking-widest text-chart-2">
                  AI
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <WorkspaceSwitcher variant="sidebar" />
      </SidebarHeader>

      <SidebarMenu className="px-2">
        <SidebarMenuItem>
          <SidebarMenuButton
            tooltip={ASTA_ACTION.label}
            isActive={isJourneyRouteActive(
              pathname,
              ASTA_ACTION.activePrefixes,
            )}
            render={<Link href={ASTA_ACTION.href} />}
          >
            <ASTA_ACTION.icon />
            <span>{ASTA_ACTION.label}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>

      <SidebarContent>
        {sections.map((section, sectionIndex) => (
          <SidebarGroup key={`${section.label}-${sectionIndex}`}>
            {section.label && (
              <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
            )}
            <SidebarMenu>
              {section.items.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    tooltip={item.label}
                    isActive={isJourneyRouteActive(
                      pathname,
                      item.activePrefixes,
                    )}
                    render={<Link href={item.href} />}
                  >
                    <item.icon />
                    <span>{item.label}</span>
                  </SidebarMenuButton>
                  {item.href === "/approvals" && pendingApprovals > 0 && (
                    <SidebarMenuBadge>{pendingApprovals}</SidebarMenuBadge>
                  )}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <NavUser isAdmin={isAdmin} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
