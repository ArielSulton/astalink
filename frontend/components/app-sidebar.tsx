"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Briefcase,
  LayoutDashboard,
  Newspaper,
  Scale,
  Settings,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chatbot", label: "Chatbot", icon: Bot },
  { href: "/assets", label: "Asset View", icon: Briefcase },
  { href: "/legal-docs", label: "Legal Document", icon: Scale },
  { href: "/news", label: "External News", icon: Newspaper },
  { href: "/settings", label: "Pengaturan", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 bg-[#0a0b0d] min-h-screen border-r border-[#1e2028] flex flex-col">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-[#1e2028]">
        <span className="text-white font-semibold text-base tracking-tight">
          Astalink
        </span>
        <span className="ml-1.5 text-[#0052ff] text-xs font-mono font-bold">
          AI
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-[#16181c] text-white border-l-2 border-[#0052ff] pl-[10px]"
                  : "text-[#a8acb3] hover:bg-[#16181c] hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
