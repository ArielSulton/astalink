import {
  Bot,
  Building2,
  ChartCandlestick,
  ClipboardCheck,
  House,
  Lightbulb,
  Newspaper,
  PieChart,
  Receipt,
  Scale,
  Settings,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export type JourneyItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  activePrefixes: string[];
  adminOnly?: boolean;
};

export type JourneySection = {
  label: string;
  items: JourneyItem[];
};

export const ASTA_ACTION: JourneyItem = {
  href: "/chatbot",
  label: "Tanya Asta",
  icon: Bot,
  activePrefixes: ["/chatbot"],
};

export const DESKTOP_SECTIONS: JourneySection[] = [
  {
    label: "",
    items: [
      {
        href: "/dashboard",
        label: "Beranda",
        icon: House,
        activePrefixes: ["/dashboard"],
      },
    ],
  },
  {
    label: "Catat & Kelola",
    items: [
      {
        href: "/transactions",
        label: "Transaksi",
        icon: Receipt,
        activePrefixes: ["/transactions"],
      },
      {
        href: "/business",
        label: "Bisnis Saya",
        icon: Building2,
        activePrefixes: ["/business"],
      },
    ],
  },
  {
    label: "Rencanakan",
    items: [
      {
        href: "/allocation",
        label: "Rencana Dana",
        icon: PieChart,
        activePrefixes: ["/allocation"],
      },
    ],
  },
  {
    label: "Eksplorasi",
    items: [
      {
        href: "/recommendations",
        label: "Ide Investasi",
        icon: Lightbulb,
        activePrefixes: ["/recommendations"],
      },
      {
        href: "/market",
        label: "Pasar & Grafik",
        icon: ChartCandlestick,
        activePrefixes: ["/market"],
      },
      {
        href: "/news",
        label: "Berita Pasar",
        icon: Newspaper,
        activePrefixes: ["/news"],
      },
    ],
  },
  {
    label: "Portofolio",
    items: [
      {
        href: "/portfolio",
        label: "Kepemilikan & Kinerja",
        icon: Wallet,
        activePrefixes: ["/portfolio"],
      },
      {
        href: "/approvals",
        label: "Persetujuan",
        icon: ClipboardCheck,
        activePrefixes: ["/approvals"],
      },
    ],
  },
  {
    label: "",
    items: [
      {
        href: "/settings",
        label: "Pengaturan",
        icon: Settings,
        activePrefixes: ["/settings"],
      },
      {
        href: "/legal-docs",
        label: "Dokumen Regulasi",
        icon: Scale,
        activePrefixes: ["/legal-docs"],
        adminOnly: true,
      },
    ],
  },
];

export const MOBILE_TABS: JourneyItem[] = [
  {
    href: "/dashboard",
    label: "Beranda",
    icon: House,
    activePrefixes: ["/dashboard"],
  },
  {
    href: "/transactions",
    label: "Catat",
    icon: Receipt,
    activePrefixes: ["/transactions", "/business"],
  },
  {
    href: "/allocation",
    label: "Rencana",
    icon: PieChart,
    activePrefixes: ["/allocation"],
  },
  {
    href: "/recommendations",
    label: "Jelajah",
    icon: Lightbulb,
    activePrefixes: ["/recommendations", "/market", "/news"],
  },
  {
    href: "/portfolio",
    label: "Portofolio",
    icon: Wallet,
    activePrefixes: ["/portfolio", "/approvals"],
  },
];

export function isJourneyRouteActive(
  pathname: string,
  prefixes: string[],
): boolean {
  return prefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function visibleDesktopSections(isAdmin: boolean): JourneySection[] {
  return DESKTOP_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => !item.adminOnly || isAdmin),
  })).filter((section) => section.items.length > 0);
}
