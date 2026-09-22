"use client";

import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
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
    <DialogPrimitive.Root
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop className="fixed inset-0 z-[60] bg-background/80 backdrop-blur-md animate-fade-in" />
        <DialogPrimitive.Popup className="fixed inset-x-0 bottom-0 z-[60] max-h-[90svh] overflow-y-auto rounded-t-2xl border border-border bg-glass p-6 shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur-xl lg:bottom-auto lg:left-1/2 lg:top-1/2 lg:max-w-sm lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-2xl">
          <DialogPrimitive.Title className="mb-1 text-lg font-bold tracking-tight text-foreground">
            Konfirmasi PIN
          </DialogPrimitive.Title>
          <DialogPrimitive.Description className="mb-4 text-xs text-muted-foreground">
            Masukkan PIN keamanan Anda untuk menyetujui alokasi ini.
          </DialogPrimitive.Description>
          <input
            type="password"
            aria-label="PIN keamanan"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            className="w-full text-center tracking-[0.8em] font-mono font-bold text-lg bg-secondary border border-border rounded-xl px-4 py-3 text-foreground placeholder:text-muted-foreground/50 placeholder:tracking-normal focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
            placeholder="••••••••"
            autoFocus
          />
          {error && <p className="mt-2 text-xs font-medium text-destructive">{error}</p>}
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 transition-all duration-200"
            >
              Batal
            </button>
            <button
              type="button"
              disabled={loading || pin.length < 6}
              onClick={handle}
              className="flex-1 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
            >
              {loading ? "Memverifikasi…" : "Setujui"}
            </button>
          </div>
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
