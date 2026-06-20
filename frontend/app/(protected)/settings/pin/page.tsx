"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function PinSettings() {
  const [pin, setPin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setMsg(null);
    if (pin.length < 6) { setMsg("PIN minimal 6 digit."); return; }
    if (pin !== confirm) { setMsg("PIN dan konfirmasi tidak cocok."); return; }

    setLoading(true);
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { setLoading(false); return; }
    try {
      await api.setPin(pin, session.access_token);
      setMsg("PIN berhasil disimpan.");
      setPin(""); setConfirm("");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-8 max-w-xl w-full mx-auto bg-background min-h-screen text-foreground space-y-6">
      <div>
        <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
          Security Settings
        </p>
        <h1 className="text-foreground text-2xl font-bold tracking-tight">PIN Persetujuan</h1>
      </div>

      <div className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-5">
        <div>
          <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">PIN Baru (6-8 digit)</label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={8}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            placeholder="••••••••"
            className="w-full text-center tracking-[0.8em] font-mono font-bold text-lg bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground placeholder:text-muted-foreground/40 placeholder:tracking-normal focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200"
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground mb-1.5 block">Konfirmasi PIN</label>
          <input
            type="password"
            inputMode="numeric"
            maxLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ""))}
            placeholder="••••••••"
            className="w-full text-center tracking-[0.8em] font-mono font-bold text-lg bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground placeholder:text-muted-foreground/40 placeholder:tracking-normal focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200"
          />
        </div>

        {msg && (
          <p className={`text-xs p-3.5 rounded-xl border ${
            msg === "PIN berhasil disimpan."
              ? "text-emerald-400 bg-emerald-500/5 border-emerald-500/10"
              : "text-rose-400 bg-rose-500/5 border-rose-500/10"
          }`}>
            {msg}
          </p>
        )}

        <button
          onClick={submit}
          disabled={loading || pin.length < 6 || !confirm}
          className="w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 hover:shadow-[0_0_16px_rgba(37,99,235,0.3)] disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
        >
          {loading ? "Menyimpan…" : "Simpan PIN"}
        </button>
      </div>
    </main>
  );
}
