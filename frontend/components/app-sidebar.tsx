"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Briefcase,
  ClipboardCheck,
  LayoutDashboard,
  Newspaper,
  Scale,
  Settings,
} from "lucide-react";

const NAV_SECTIONS = [
  {
    label: "Portfolio",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/chatbot", label: "AI Chatbot", icon: Bot },
      { href: "/assets", label: "Asset View", icon: Briefcase },
    ],
  },
  {
    label: "Compliance",
    items: [
      { href: "/legal-docs", label: "Legal Docs", icon: Scale },
      { href: "/approvals", label: "Approvals", icon: ClipboardCheck },
      { href: "/news", label: "Market News", icon: Newspaper },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 bg-sidebar min-h-screen border-r border-sidebar-border flex flex-col z-20">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center shrink-0">
            <span className="text-primary text-[10px] font-black font-mono">A</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-foreground font-bold text-sm tracking-tight">Astalink</span>
            <span className="text-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
          </div>
        </div>
      </div>

      {/* Nav sections */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
        {NAV_SECTIONS.map(({ label, items }) => (
          <div key={label}>
            <p className="px-3 mb-1.5 text-[9px] font-black uppercase tracking-[0.18em] text-muted-foreground/60 font-mono">
              {label}
            </p>
            <div className="space-y-0.5">
              {items.map(({ href, label: itemLabel, icon: Icon }) => {
                const active = pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 relative ${
                      active
                        ? "bg-primary/[0.12] text-foreground"
                        : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-[20%] h-[60%] w-[2px] rounded-r-full bg-primary shadow-[0_0_8px_rgba(37,99,235,0.6)]" />
                    )}
                    <Icon
                      className={`h-4 w-4 shrink-0 transition-colors duration-150 ${
                        active ? "text-primary" : "text-muted-foreground/70"
                      }`}
                    />
                    {itemLabel}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom: Settings */}
      <div className="px-3 py-3 border-t border-sidebar-border">
        <Link
          href="/settings"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 relative ${
            pathname.startsWith("/settings")
              ? "bg-primary/[0.12] text-foreground"
              : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
          }`}
        >
          {pathname.startsWith("/settings") && (
            <span className="absolute left-0 top-[20%] h-[60%] w-[2px] rounded-r-full bg-primary shadow-[0_0_8px_rgba(37,99,235,0.6)]" />
          )}
          <Settings
            className={`h-4 w-4 shrink-0 ${
              pathname.startsWith("/settings") ? "text-primary" : "text-muted-foreground/70"
            }`}
          />
          Settings
        </Link>
      </div>
    </aside>
  );
}
