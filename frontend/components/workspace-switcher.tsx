"use client";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Workspace { id: string; name: string; type: "personal" | "business"; }

export function WorkspaceSwitcher({
  current,
  onChange,
}: { current: string | null; onChange: (id: string) => void }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  useEffect(() => {
    const sb = createClient();
    sb.from("workspaces").select("id,name,type").then(({ data }) => {
      setWorkspaces((data as Workspace[]) || []);
    });
  }, []);
  return (
    <select
      className="border rounded px-2 py-1"
      value={current ?? ""}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="" disabled>Select workspace…</option>
      {workspaces.map((w) => (
        <option key={w.id} value={w.id}>{w.name} ({w.type})</option>
      ))}
    </select>
  );
}
