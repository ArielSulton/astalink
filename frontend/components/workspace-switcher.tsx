"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api-client";

interface Workspace { id: string; name: string; type: "personal" | "business"; cash_balance: number; }

const CREATE_VALUE = "__create__";
export const LAST_WORKSPACE_KEY = "astalink_last_workspace_id";

export function WorkspaceSwitcher({
  current,
  onChange,
}: { current: string | null; onChange: (id: string) => void }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<"personal" | "business">("personal");
  const [submitting, setSubmitting] = useState(false);

  function select(id: string) {
    onChange(id);
    localStorage.setItem(LAST_WORKSPACE_KEY, id);
  }

  function refresh(autoSelect: boolean) {
    const sb = createClient();
    sb.from("workspaces").select("id,name,type,cash_balance").then(({ data }) => {
      const list = (data as Workspace[]) || [];
      setWorkspaces(list);
      // Don't make the user pick when there's nothing to choose between (or
      // a remembered choice already answers it) — only surface the dropdown
      // as a real decision when there's more than one workspace and no prior
      // selection cached from a previous visit.
      if (autoSelect && !current && list.length > 0) {
        const remembered = list.find((w) => w.id === localStorage.getItem(LAST_WORKSPACE_KEY));
        select(remembered ? remembered.id : list[0].id);
      }
    });
  }

  useEffect(() => { refresh(true); }, []);

  async function handleCreate() {
    if (!name.trim()) { toast.error("Nama workspace wajib diisi."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { toast.error("Sesi berakhir, silakan login ulang."); return; }

    setSubmitting(true);
    try {
      const workspace = await api.createWorkspace(
        { name: name.trim(), type },
        session.access_token,
      );
      toast.success(`Workspace "${workspace.name}" dibuat.`);
      setName("");
      setType("personal");
      setCreating(false);
      refresh(false);
      select(workspace.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal membuat workspace.");
    } finally {
      setSubmitting(false);
    }
  }

  const currentWorkspace = workspaces.find((w) => w.id === current);

  return (
    <div className="relative inline-block">
      <div className="flex items-center gap-2">
        <div className="relative inline-block">
          <select
            className="appearance-none bg-secondary hover:bg-secondary/80 border border-border hover:border-border/60 text-foreground rounded-xl px-4 py-2 pr-9 text-xs font-semibold tracking-wide focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200 cursor-pointer"
            value={current ?? ""}
            onChange={(e) => {
              if (e.target.value === CREATE_VALUE) { setCreating(true); return; }
              select(e.target.value);
            }}
          >
            <option value="" disabled className="bg-card text-muted-foreground">Select workspace…</option>
            {workspaces.map((w) => (
              <option key={w.id} value={w.id} className="bg-card text-foreground">
                {w.name} ({w.type === "personal" ? "Personal" : "Business"})
              </option>
            ))}
            <option value={CREATE_VALUE} className="bg-card text-chart-2">+ Buat workspace baru</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground">
            <svg className="fill-current h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
            </svg>
          </div>
        </div>
        {currentWorkspace && (
          <span className="text-[10px] font-mono text-muted-foreground whitespace-nowrap">
            Rp {currentWorkspace.cash_balance.toLocaleString("id-ID")}
          </span>
        )}
      </div>

      {creating && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-border bg-card p-4 shadow-xl z-20 space-y-3">
          <p className="text-xs font-bold text-foreground uppercase tracking-wider">Workspace Baru</p>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nama workspace"
            className="w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20"
          />
          <div className="flex gap-2">
            {(["personal", "business"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold border transition-colors ${
                  type === t
                    ? "bg-primary text-primary-foreground border-chart-2"
                    : "bg-secondary text-muted-foreground border-border hover:border-border/60"
                }`}
              >
                {t === "personal" ? "Personal" : "Business"}
              </button>
            ))}
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => { setCreating(false); setName(""); }}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
            >
              Batal
            </button>
            <button
              type="button"
              onClick={handleCreate}
              disabled={submitting || !name.trim()}
              className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Membuat…" : "Buat"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
