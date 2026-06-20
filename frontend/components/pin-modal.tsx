"use client";
import { useState } from "react";

export function PinModal({
  open, onSubmit, onClose, error,
}: {
  open: boolean;
  onSubmit: (pin: string) => Promise<void>;
  onClose: () => void;
  error?: string | null;
}) {
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handle = async () => {
    setLoading(true);
    try { await onSubmit(pin); } finally { setLoading(false); }
  };

  return (
    <div
      className="fixed inset-0 bg-background/80 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-glass border border-border shadow-[0_20px_60px_rgba(0,0,0,0.6)] rounded-2xl p-6 w-full max-w-sm backdrop-blur-xl relative z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-foreground font-bold text-lg mb-1 tracking-tight">Konfirmasi PIN</h2>
        <p className="text-muted-foreground text-xs mb-4">
          Masukkan PIN keamanan Anda untuk menyetujui alokasi ini.
        </p>
        <input
          type="password"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={8}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className="w-full text-center tracking-[0.8em] font-mono font-bold text-lg bg-secondary border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted-foreground/50 placeholder:tracking-normal focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200"
          placeholder="••••••••"
          autoFocus
        />
        {error && <p className="text-xs text-rose-400 mt-2 font-medium">{error}</p>}
        <div className="flex gap-3 mt-5">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 transition-all duration-200"
          >
            Cancel
          </button>
          <button
            disabled={loading || pin.length < 6}
            onClick={handle}
            className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 hover:shadow-[0_0_16px_rgba(37,99,235,0.35)] disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
          >
            {loading ? "Verifying..." : "Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}
