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
    <div className="relative inline-block">
      <select
        className="appearance-none bg-secondary hover:bg-secondary/80 border border-border hover:border-border/60 text-foreground rounded-xl px-4 py-2 pr-9 text-xs font-semibold tracking-wide focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all duration-200 cursor-pointer"
        value={current ?? ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="" disabled className="bg-card text-muted-foreground">Select workspace…</option>
        {workspaces.map((w) => (
          <option key={w.id} value={w.id} className="bg-card text-foreground">
            {w.name} ({w.type === "personal" ? "Personal" : "Business"})
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground">
        <svg className="fill-current h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
          <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
        </svg>
      </div>
    </div>
  );
}
