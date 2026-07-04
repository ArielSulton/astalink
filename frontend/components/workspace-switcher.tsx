"use client";
import { useState } from "react";
import { toast } from "sonner";
import { ChevronRight, Layers, Plus } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api-client";
import { useWorkspace } from "@/components/workspace-context";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";

export function WorkspaceSwitcher() {
  const { workspaceId, setWorkspaceId, workspaces, refreshWorkspaces } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<"personal" | "business">("personal");
  const [submitting, setSubmitting] = useState(false);

  const current = workspaces.find((w) => w.id === workspaceId);

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
      refreshWorkspaces(false);
      setWorkspaceId(workspace.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal membuat workspace.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton tooltip="Workspace" onClick={() => setOpen((v) => !v)}>
          <Layers />
          <span>{current ? current.name : "Pilih Workspace"}</span>
          <ChevronRight
            className={`ml-auto size-4 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
          />
        </SidebarMenuButton>
        {open && (
          <SidebarMenuSub>
            {workspaces.map((w) => (
              <SidebarMenuSubItem key={w.id}>
                <SidebarMenuSubButton
                  isActive={w.id === workspaceId}
                  render={<button type="button" />}
                  onClick={() => { setWorkspaceId(w.id); setOpen(false); }}
                >
                  <span>{w.name} ({w.type === "personal" ? "Personal" : "Business"})</span>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
            <SidebarMenuSubItem>
              <SidebarMenuSubButton
                render={<button type="button" />}
                onClick={() => { setCreating(true); setOpen(false); }}
              >
                <Plus />
                <span>Buat workspace baru</span>
              </SidebarMenuSubButton>
            </SidebarMenuSubItem>
          </SidebarMenuSub>
        )}
      </SidebarMenuItem>

      {creating && (
        <div className="mx-2 mt-2 rounded-xl border border-border bg-card p-4 shadow-xl space-y-3">
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
    </SidebarMenu>
  );
}
