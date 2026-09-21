"use client";

import { PlusCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PinModal } from "@/components/pin-modal";
import { ResponsiveDialog } from "@/components/ui/responsive-dialog";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

function idr(value: number | null | undefined): string {
  if (value == null) return "—";
  return `Rp ${value.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
}

export function AllocationBuyModal({
  workspaceId,
  suggestedTickers,
  suggestedAmount,
  auditId,
  onClose,
  onSuccess,
}: {
  workspaceId: string;
  suggestedTickers: string[];
  suggestedAmount?: number | null;
  auditId?: string | null;
  onClose: () => void;
  onSuccess: (ticker: string, amount: number, cashRemaining: number) => void;
}) {
  const [selectedTicker, setSelectedTicker] = useState(
    suggestedTickers[0] || "BBCA",
  );
  const [amountString, setAmountString] = useState(
    suggestedAmount && suggestedAmount > 0
      ? String(Math.round(suggestedAmount))
      : "10000000",
  );
  const [availableCash, setAvailableCash] = useState(0);
  const [loading, setLoading] = useState(false);
  const [fetchingCash, setFetchingCash] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const sb = createClient();
        const {
          data: { session },
        } = await sb.auth.getSession();
        if (!session) return;
        const portfolio = await api.getPortfolio(
          workspaceId,
          session.access_token,
        );
        setAvailableCash(portfolio.cash_balance);
      } catch {
        setError("Gagal mengambil saldo kas.");
      } finally {
        setFetchingCash(false);
      }
    })();
  }, [workspaceId]);

  const amount = Number(amountString);
  const valid =
    selectedTicker.trim().length >= 3 &&
    amount > 0 &&
    amount <= availableCash;

  const presetAmounts = [
    { label: "5 Juta", value: 5_000_000 },
    { label: "10 Juta", value: 10_000_000 },
    { label: "25 Juta", value: 25_000_000 },
    { label: "50 Juta", value: 50_000_000 },
  ];

  async function submitWithPin(pin: string) {
    setPinError(null);
    setLoading(true);
    try {
      const sb = createClient();
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (!session) return;

      const response = await api.buyHolding(
        workspaceId,
        {
          ticker: selectedTicker.toUpperCase().trim(),
          amount,
          pin,
          ...(auditId ? { audit_id: auditId } : {}),
        },
        session.access_token,
      );

      toast.success(
        `Alokasi ${idr(response.allocated_amount)} ke ${response.ticker} berhasil! Saldo kas berkurang.`,
      );
      setPinOpen(false);
      onSuccess(
        response.ticker,
        response.allocated_amount,
        response.cash_balance,
      );
    } catch (caughtError) {
      setPinError(
        caughtError instanceof Error
          ? caughtError.message
          : "Gagal mengalokasikan dana.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <ResponsiveDialog
        open
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
        title="Alokasikan Dana ke Portofolio"
        description="Pilih saham dan nominal yang akan dialokasikan dari saldo kas."
      >
        <div className="mt-4 space-y-4 text-foreground">
          <p className="text-xs text-muted-foreground">
            Saldo Kas Tersedia:{" "}
            {fetchingCash ? (
              <span className="animate-pulse font-mono">Memuat…</span>
            ) : (
              <strong className="font-mono text-foreground">
                {idr(availableCash)}
              </strong>
            )}
          </p>

          <div>
            <label className="mb-1.5 block font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Pilih saham / ticker
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {suggestedTickers.map((ticker) => (
                <button
                  key={ticker}
                  type="button"
                  onClick={() => setSelectedTicker(ticker)}
                  className={`min-h-11 rounded-lg border px-3 font-mono text-xs font-bold transition-all ${
                    selectedTicker === ticker
                      ? "border-chart-2 bg-chart-2/20 text-chart-2"
                      : "border-border bg-secondary text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {ticker}
                </button>
              ))}
            </div>
            <input
              type="text"
              value={selectedTicker}
              onChange={(event) =>
                setSelectedTicker(event.target.value.toUpperCase())
              }
              placeholder="Ketik ticker, misal: BBCA"
              className="w-full rounded-xl border border-border bg-secondary px-4 py-2.5 font-mono text-xs font-bold uppercase text-foreground transition-all focus:border-chart-2 focus:outline-none focus:ring-1 focus:ring-chart-2/20"
            />
          </div>

          <div>
            <label className="mb-1.5 block font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Nominal alokasi (Rupiah)
            </label>
            <input
              type="number"
              value={amountString}
              onChange={(event) => setAmountString(event.target.value)}
              placeholder="Nominal alokasi dalam Rp"
              className="mb-2 w-full rounded-xl border border-border bg-secondary px-4 py-2.5 font-mono text-xs font-bold text-foreground transition-all focus:border-chart-2 focus:outline-none focus:ring-1 focus:ring-chart-2/20"
            />
            <div className="flex flex-wrap items-center gap-2">
              {presetAmounts.map((preset) => (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => setAmountString(String(preset.value))}
                  className="min-h-11 rounded-lg border border-border bg-secondary px-2.5 font-mono text-[11px] text-muted-foreground transition-all hover:bg-secondary/80 hover:text-foreground"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {amount > availableCash && !fetchingCash && (
            <p className="text-xs font-medium text-destructive">
              Nominal alokasi melebihi saldo kas yang tersedia.
            </p>
          )}

          {error && (
            <p className="text-xs font-medium text-destructive">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="min-h-11 flex-1 rounded-xl border border-border bg-secondary text-sm font-semibold text-foreground transition-all hover:bg-secondary/80"
            >
              Batal
            </button>
            <button
              type="button"
              disabled={!valid || loading || fetchingCash}
              onClick={() => {
                setPinError(null);
                setPinOpen(true);
              }}
              className="min-h-11 flex-1 rounded-xl bg-primary text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
            >
              <PlusCircle className="mr-1 inline size-4" />
              {loading ? "Mengalokasikan…" : "Alokasikan Dana"}
            </button>
          </div>
        </div>
      </ResponsiveDialog>

      <PinModal
        open={pinOpen}
        onSubmit={submitWithPin}
        onClose={() => setPinOpen(false)}
        error={pinError}
      />
    </>
  );
}
