"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";

export function LogoutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleLogout() {
    setLoading(true);
    const sb = createClient();
    const { error } = await sb.auth.signOut();
    if (error) {
      toast.error(error.message);
      setLoading(false);
      return;
    }
    router.push("/login");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={loading}
      className="w-full bg-card hover:bg-rose-500/5 border border-border hover:border-rose-500/30 rounded-2xl p-5 flex items-center justify-between transition-all duration-200 hover:-translate-y-0.5 cursor-pointer group disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
    >
      <div className="flex items-center gap-4 min-w-0">
        <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0 group-hover:scale-105 transition-all">
          <LogOut className="h-5 w-5" />
        </div>
        <div className="min-w-0 text-left">
          <h2 className="text-foreground font-bold text-sm tracking-tight">
            {loading ? "Keluar…" : "Logout"}
          </h2>
          <p className="text-muted-foreground text-xs mt-0.5">Keluar dari akun Anda di perangkat ini</p>
        </div>
      </div>
    </button>
  );
}
