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
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg p-6 w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold mb-3">Konfirmasi PIN</h2>
        <input
          type="password"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={8}
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className="border rounded px-2 py-1 w-full"
          placeholder="6-8 digit PIN"
          autoFocus
        />
        {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
        <div className="flex gap-2 mt-3">
          <button
            disabled={loading || pin.length < 6}
            onClick={handle}
            className="bg-blue-600 text-white rounded px-4 py-1 disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Approve"}
          </button>
          <button
            onClick={onClose}
            className="border border-gray-400 rounded px-4 py-1"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
