"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type ApprovalDetail } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { PinModal } from "@/components/pin-modal";
import { AllocationChart } from "@/components/allocation-chart";

export default function ApprovalDetailPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      setDetail(await api.getApproval(auditId, session.access_token));
    };
    load();
  }, [auditId]);

  const submitPin = async (pin: string) => {
    setPinError(null);
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    try {
      await api.approve(auditId, pin, session.access_token);
      router.push(`/audit/${auditId}`);
    } catch (err) {
      setPinError(err instanceof Error ? err.message : "Gagal");
    }
  };

  const reject = async () => {
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    await api.reject(auditId, "User rejected", session.access_token);
    router.push("/approvals");
  };

  if (!detail) return <p className="p-6">Loading…</p>;
  const plan = detail.plan_json;

  return (
    <main className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Approval {auditId.slice(0, 8)}…</h1>

      <section>
        <h2 className="text-lg font-medium mb-2">Alokasi yang diusulkan</h2>
        {plan ? <AllocationChart weights={plan.weights} /> : <p>Tidak ada plan.</p>}
        {plan?.narration && <p className="mt-2 text-sm">{plan.narration}</p>}
      </section>

      <section>
        <h2 className="text-lg font-medium mb-2">Kepatuhan regulasi</h2>
        <p>Status: <span className="font-medium">{detail.legal_status}</span></p>
        <ul className="list-disc pl-5 text-sm">
          {detail.legal_citations.map((c, i) => (
            <li key={i}>
              {c.source} Pasal {c.pasal}{c.ayat ? ` ayat (${c.ayat})` : ""}: <em>{c.span}</em>
            </li>
          ))}
        </ul>
      </section>

      <div className="flex gap-3">
        <button
          onClick={() => setPinOpen(true)}
          className="bg-blue-600 text-white rounded px-4 py-2"
          disabled={detail.legal_status === "rejected" || detail.legal_status === "rejected_after_max_revisions"}
        >
          Approve dengan PIN
        </button>
        <button
          onClick={reject}
          className="border border-gray-400 rounded px-4 py-2"
        >
          Reject
        </button>
      </div>

      <PinModal
        open={pinOpen}
        onSubmit={submitPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />
    </main>
  );
}
