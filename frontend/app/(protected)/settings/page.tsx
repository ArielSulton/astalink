import Link from "next/link";
import { KeyRound, MessageCircle, ArrowRight } from "lucide-react";
import { LogoutButton } from "@/components/logout-button";
import { PageHeader } from "@/components/ui/page-header";

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-4xl w-full mx-auto bg-background min-h-screen text-foreground space-y-6">
      <PageHeader eyebrow="Preferences" title="Settings" />

      <Link href="/settings/pin">
        <div className="bg-card hover:bg-secondary border border-border hover:border-border/60 rounded-2xl p-5 flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5 cursor-pointer group">
          <div className="flex items-center gap-4 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-chart-2/10 border border-chart-2/20 flex items-center justify-center text-chart-2 shrink-0 group-hover:scale-105 transition-all">
              <KeyRound className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-foreground font-bold text-sm tracking-tight">PIN Persetujuan</h2>
              <p className="text-muted-foreground text-xs mt-0.5">Atur PIN untuk mengkonfirmasi otorisasi transaksi portofolio</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
        </div>
      </Link>

      <Link href="/settings/whatsapp">
        <div className="bg-card hover:bg-secondary border border-border hover:border-border/60 rounded-2xl p-5 flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5 cursor-pointer group">
          <div className="flex items-center gap-4 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-chart-2/10 border border-chart-2/20 flex items-center justify-center text-chart-2 shrink-0 group-hover:scale-105 transition-all">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-foreground font-bold text-sm tracking-tight">WhatsApp</h2>
              <p className="text-muted-foreground text-xs mt-0.5">Hubungkan nomor WhatsApp untuk chat dengan AstaLink bot</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
        </div>
      </Link>

      <LogoutButton />
    </div>
  );
}
