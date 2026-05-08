"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

export default function PinSettings() {
  const [pin, setPin] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const submit = async () => {
    setMsg(null);
    if (pin !== confirm) { setMsg("PIN dan konfirmasi tidak cocok."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    try {
      await api.setPin(pin, session.access_token);
      setMsg("PIN berhasil disimpan.");
      setPin(""); setConfirm("");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Gagal");
    }
  };

  return (
    <main className="p-6 max-w-md mx-auto">
      <h1 className="text-2xl font-semibold mb-4">PIN Persetujuan</h1>
      <input
        type="password"
        inputMode="numeric"
        maxLength={8}
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
        placeholder="6-8 digit PIN"
        className="border rounded px-2 py-1 w-full mb-2"
      />
      <input
        type="password"
        inputMode="numeric"
        maxLength={8}
        value={confirm}
        onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ""))}
        placeholder="Konfirmasi PIN"
        className="border rounded px-2 py-1 w-full mb-2"
      />
      <button onClick={submit} className="bg-blue-600 text-white rounded px-4 py-2">
        Simpan
      </button>
      {msg && <p className="mt-2 text-sm">{msg}</p>}
    </main>
  );
}
