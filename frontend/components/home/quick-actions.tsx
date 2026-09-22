import { Bot, PieChart, Receipt } from "lucide-react";
import Link from "next/link";

const ACTIONS = [
  { href: "/transactions", label: "Catat transaksi", icon: Receipt },
  { href: "/allocation", label: "Rencana dana", icon: PieChart },
  { href: "/chatbot", label: "Tanya Asta", icon: Bot },
];

export function QuickActions() {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-base font-bold text-foreground">Akses cepat</h2>
      <div className="mt-3 grid gap-2 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
        {ACTIONS.map((action) => (
          <Link
            key={action.href}
            href={action.href}
            className="flex min-h-11 items-center gap-2 rounded-lg border border-border px-3 text-sm font-semibold text-foreground hover:bg-secondary"
          >
            <action.icon className="size-4 text-muted-foreground" />
            <span>{action.label}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
