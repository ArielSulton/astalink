"use client";

import { Bot } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  MOBILE_TABS,
  isJourneyRouteActive,
} from "@/lib/journey-navigation";

export function MobileNavigation({
  pendingApprovals,
}: {
  pendingApprovals: number;
}) {
  const pathname = usePathname();

  return (
    <>
      <Link
        aria-label="Tanya Asta"
        href="/chatbot"
        className="fixed right-4 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-40 inline-flex min-h-11 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-lg lg:hidden"
      >
        <Bot className="size-4" />
        Tanya Asta
      </Link>
      <nav
        aria-label="Perjalanan utama"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-border bg-card pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        {MOBILE_TABS.map((tab) => {
          const active = isJourneyRouteActive(pathname, tab.activePrefixes);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className="relative flex min-h-16 flex-col items-center justify-center gap-1 text-[10px] text-muted-foreground aria-[current=page]:text-primary"
            >
              <tab.icon className="size-5" />
              <span>{tab.label}</span>
              {tab.label === "Portofolio" && pendingApprovals > 0 && (
                <span className="absolute right-3 top-2 rounded-full bg-destructive px-1 text-[9px] text-white">
                  {pendingApprovals}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
