"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { AllocationChart } from "@/components/allocation-chart";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse } from "@/lib/api-client";

const legalColor: Record<string, string> = {
  approved: "bg-green-100 text-green-800",
  partial: "bg-yellow-100 text-yellow-800",
  rejected: "bg-red-100 text-red-800",
  rejected_after_max_revisions: "bg-red-100 text-red-800",
};

export default function DashboardPage() {
  const router = useRouter();
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);

  const handleRun = async () => {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!message.trim()) { toast.error("Masukkan perintah."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { router.push("/login"); return; }
    setLoading(true);
    setResult(null);
    try {
      const res = await api.runAgent(
        { message: message.trim(), workspace_id: workspaceId },
        session.access_token,
      );
      setResult(res);
      if (res.user_approval === null && res.legal_status !== "rejected") {
        toast.info("Menunggu approval Anda di halaman Approvals.");
      } else if (res.transactions.length > 0) {
        toast.success("Eksekusi selesai. Lihat Transaksi untuk detail.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Kirim Perintah ke AI</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="w-full border rounded-md px-3 py-2 text-sm min-h-[80px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Contoh: Alokasikan 50 juta ke saham BBCA.JK, TLKM.JK, dan ASII.JK dengan profil risiko moderat"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={loading}
          />
          <Button onClick={handleRun} disabled={loading || !workspaceId} className="w-full">
            {loading ? "Menganalisis…" : "Jalankan Analisis"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              Hasil Analisis
              <Badge variant="outline" className="font-mono text-xs">
                {result.audit_id.slice(0, 8)}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="text-muted-foreground">Intent:</span>
              <span className="font-medium">{result.intent ?? "—"}</span>
              {result.legal_status && (
                <>
                  <Separator orientation="vertical" className="h-4 self-center" />
                  <span className="text-muted-foreground">Legal:</span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${legalColor[result.legal_status] ?? "bg-muted"}`}
                  >
                    {result.legal_status}
                  </span>
                </>
              )}
            </div>

            {result.allocation_plan && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium mb-2">Alokasi yang Diusulkan</p>
                  <AllocationChart weights={result.allocation_plan.weights} />
                  {result.allocation_plan.narration && (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {result.allocation_plan.narration}
                    </p>
                  )}
                </div>
              </>
            )}

            {result.errors.length > 0 && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium text-destructive mb-1">Errors</p>
                  <ul className="text-xs text-destructive space-y-0.5">
                    {result.errors.map((e, i) => (
                      <li key={i}>{e.node}: {e.reason}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            {(result.user_approval === null && result.legal_status !== "rejected") && (
              <>
                <Separator />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/approvals/${result.audit_id}`)}
                >
                  Review & Approve →
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
