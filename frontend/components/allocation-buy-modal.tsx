"use client";
import { useEffect, useState } from "react";
import { PlusCircle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { PinModal } from "@/components/pin-modal";

function idr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

// The only UI that actually places an order: writes to `transactions` and
// updates holdings via POST /portfolio/{workspaceId}/buy. Shared by the
// chatbot page and the dashboard AI panel — both surfaces let the user act
// on an AI recommendation, so both need the same real execution step.
export function AllocationBuyModal({
  workspaceId, suggestedTickers, suggestedAmount, onClose, onSuccess,
}: {
  workspaceId: string;
  suggestedTickers: string[];
  suggestedAmount?: number | null;
  onClose: () => void;
  onSuccess: (ticker: string, amount: number, cashRemaining: number) => void;
}) {
  const [selectedTicker, setSelectedTicker] = useState(suggestedTickers[0] || "BBCA");
  const [amountStr, setAmountStr] = useState(
    suggestedAmount && suggestedAmount > 0 ? String(Math.round(suggestedAmount)) : "10000000",
  ); // defaults to what the user asked for / what the AI recommended; falls back to 10 Juta
  const [availableCash, setAvailableCash] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [fetchingCash, setFetchingCash] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // A buy moves real (sandbox) money exactly like a sell already does — it
  // must not be weaker-gated than sell's mandatory PIN confirmation.
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const sb = createClient();
        const { data: { session } } = await sb.auth.getSession();
        if (!session) return;
        const port = await api.getPortfolio(workspaceId, session.access_token);
        setAvailableCash(port.cash_balance);
      } catch {
        setError("Gagal mengambil saldo kas.");
      } finally {
        setFetchingCash(false);
      }
    })();
  }, [workspaceId]);

  const amountNum = Number(amountStr);
  const valid = selectedTicker.trim().length >= 3 && amountNum > 0 && amountNum <= availableCash;

  const presetAmounts = [
    { label: "5 Juta", val: 5000000 },
    { label: "10 Juta", val: 10000000 },
    { label: "25 Juta", val: 25000000 },
    { label: "50 Juta", val: 50000000 },
  ];

  async function submitWithPin(pin: string) {
    setPinError(null);
    setLoading(true);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;

      const res = await api.buyHolding(
        workspaceId,
        { ticker: selectedTicker.toUpperCase().trim(), amount: amountNum, pin },
        session.access_token,
      );

      toast.success(
        `Alokasi ${idr(res.allocated_amount)} ke ${res.ticker} berhasil! Saldo kas berkurang.`,
      );
      setPinOpen(false);
      onSuccess(res.ticker, res.allocated_amount, res.cash_balance);
    } catch (e) {
      setPinError(e instanceof Error ? e.message : "Gagal mengalokasikan dana.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-background/80 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-glass border border-border shadow-[0_20px_60px_rgba(0,0,0,0.5)] rounded-2xl p-6 w-full max-w-md backdrop-blur-xl relative z-10 space-y-4 text-foreground"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <h2 className="font-bold text-lg tracking-tight text-foreground flex items-center gap-2">
            <PlusCircle className="h-5 w-5 text-chart-2" />
            Alokasikan Dana Ke Portofolio
          </h2>
          <p className="text-muted-foreground text-xs mt-0.5">
            Saldo Kas Tersedia: {fetchingCash ? (
              <span className="animate-pulse font-mono">Memuat…</span>
            ) : (
              <strong className="text-foreground font-mono">{idr(availableCash)}</strong>
            )}
          </p>
        </div>

        <div>
          <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
            Pilih Saham Rekomendasi / Ticker
          </label>
          <div className="flex gap-2 mb-2 flex-wrap">
            {suggestedTickers.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setSelectedTicker(t)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border transition-all ${
                  selectedTicker === t
                    ? "bg-chart-2/20 border-chart-2 text-chart-2"
                    : "bg-secondary border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value.toUpperCase())}
            placeholder="Ketik ticker custom, misal: BBCA"
            className="w-full font-mono uppercase font-bold bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all text-xs"
          />
        </div>

        <div>
          <label className="block text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
            Nominal Alokasi (Rupiah)
          </label>
          <input
            type="number"
            value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)}
            placeholder="Nominal alokasi dalam Rp"
            className="w-full font-mono font-bold bg-secondary border border-border rounded-xl px-4 py-2.5 text-foreground focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all text-xs mb-2"
          />
          <div className="flex items-center gap-2 flex-wrap">
            {presetAmounts.map((p) => (
              <button
                key={p.val}
                type="button"
                onClick={() => setAmountStr(String(p.val))}
                className="text-[11px] font-mono px-2.5 py-1 rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-muted-foreground hover:text-foreground transition-all"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {amountNum > availableCash && !fetchingCash && (
          <p className="text-xs text-destructive font-medium">
            ⚠ Nominal alokasi melebihi saldo kas yang tersedia.
          </p>
        )}

        {error && <p className="text-xs text-destructive font-medium">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 transition-all"
          >
            Batal
          </button>
          <button
            type="button"
            disabled={!valid || loading || fetchingCash}
            onClick={() => { setPinError(null); setPinOpen(true); }}
            className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all"
          >
            {loading ? "Mengalokasikan…" : "Alokasikan Dana"}
          </button>
        </div>
      </div>

      <PinModal
        open={pinOpen}
        onSubmit={submitWithPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />
    </div>
  );
}
