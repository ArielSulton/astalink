"use client";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";
import { PageHeader } from "@/components/ui/page-header";

function BindingContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code");
  const { workspaceId, workspaces } = useWorkspace();
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const currentWorkspace = workspaces.find((w) => w.id === workspaceId);

  const bind = async () => {
    if (!code || !workspaceId) return;
    setStatus("loading");
    setErrorMsg(null);
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) {
      setStatus("error");
      setErrorMsg("Sesi login tidak ditemukan.");
      return;
    }
    try {
      await api.bindWhatsapp(code, workspaceId, session.access_token);
      setStatus("success");
    } catch (e) {
      setStatus("error");
      setErrorMsg(e instanceof Error ? e.message : "Gagal menghubungkan nomor.");
    }
  };

  if (!code) {
    return (
      <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
        <p className="text-sm text-muted-foreground">
          Belum ada permintaan koneksi nomor WhatsApp. Kirim pesan ke bot AstaLink di
          WhatsApp untuk mendapatkan link koneksi.
        </p>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-4">
        <p className="text-sm p-3.5 rounded-xl border text-emerald-400 bg-emerald-500/5 border-emerald-500/15">
          Nomor WhatsApp berhasil terhubung ke workspace {currentWorkspace?.name ?? ""}.
        </p>
        <Link href="/settings" className="text-sm text-chart-2 underline underline-offset-4">
          Kembali ke Settings
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-6 shadow-xl space-y-5">
      <p className="text-sm text-foreground">
        Nomor WhatsApp Anda akan terhubung ke workspace:{" "}
        <span className="font-semibold text-chart-2">{currentWorkspace?.name ?? "…"}</span>
      </p>
      {errorMsg && (
        <p className="text-xs p-3.5 rounded-xl border text-rose-400 bg-rose-500/5 border-rose-500/15">
          {errorMsg}
        </p>
      )}
      <button
        onClick={bind}
        disabled={status === "loading" || !workspaceId}
        className="w-full py-3 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
      >
        {status === "loading" ? "Menghubungkan…" : "Hubungkan Nomor"}
      </button>
    </div>
  );
}

export default function WhatsAppSettingsPage() {
  return (
    <main className="p-8 max-w-xl w-full mx-auto bg-background min-h-screen text-foreground space-y-6">
      <PageHeader eyebrow="Integrations" title="WhatsApp" />
      <Suspense fallback={<div className="text-sm text-muted-foreground">Memuat…</div>}>
        <BindingContent />
      </Suspense>
    </main>
  );
}
