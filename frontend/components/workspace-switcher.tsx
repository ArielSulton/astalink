"use client";

import { ChevronDown, ChevronRight, Layers, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useWorkspace } from "@/components/workspace-context";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

type WorkspaceSwitcherProps = {
  variant?: "sidebar" | "header";
};

export function WorkspaceSwitcher({
  variant = "sidebar",
}: WorkspaceSwitcherProps) {
  const { workspaceId, setWorkspaceId, workspaces, refreshWorkspaces } =
    useWorkspace();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<"personal" | "business">("personal");
  const [submitting, setSubmitting] = useState(false);

  const current = workspaces.find((workspace) => workspace.id === workspaceId);

  function selectWorkspace(id: string) {
    setWorkspaceId(id);
    setOpen(false);
  }

  function cancelCreate() {
    setCreating(false);
    setName("");
  }

  async function handleCreate() {
    if (!name.trim()) {
      toast.error("Nama workspace wajib diisi.");
      return;
    }
    const sb = createClient();
    const {
      data: { session },
    } = await sb.auth.getSession();
    if (!session) {
      toast.error("Sesi berakhir, silakan login ulang.");
      return;
    }

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
      setOpen(false);
      refreshWorkspaces(false);
      setWorkspaceId(workspace.id);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Gagal membuat workspace.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const createForm = (
    <div className="space-y-3 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
      <p className="text-xs font-bold uppercase tracking-wider text-foreground">
        Workspace Baru
      </p>
      <input
        autoFocus
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Nama workspace"
        className="w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-chart-2 focus:outline-none focus:ring-1 focus:ring-chart-2/20"
      />
      <div className="flex gap-2">
        {(["personal", "business"] as const).map((workspaceType) => (
          <button
            key={workspaceType}
            type="button"
            onClick={() => setType(workspaceType)}
            className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
              type === workspaceType
                ? "border-chart-2 bg-primary text-primary-foreground"
                : "border-border bg-secondary text-muted-foreground hover:border-border/60"
            }`}
          >
            {workspaceType === "personal" ? "Personal" : "Bisnis"}
          </button>
        ))}
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={cancelCreate}
          className="rounded-lg px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground"
        >
          Batal
        </button>
        <button
          type="button"
          onClick={handleCreate}
          disabled={submitting || !name.trim()}
          className="rounded-lg bg-primary px-4 py-1.5 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"
        >
          {submitting ? "Membuat…" : "Buat"}
        </button>
      </div>
    </div>
  );

  if (variant === "header") {
    return (
      <>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex min-h-11 max-w-[60vw] items-center gap-2 rounded-lg px-3 text-sm font-medium text-foreground hover:bg-secondary"
        >
          <Layers className="size-4 shrink-0" />
          <span className="truncate">
            {current ? current.name : "Pilih Workspace"}
          </span>
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        </button>
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetContent side="bottom" className="max-h-[85svh] overflow-auto">
            <SheetHeader>
              <SheetTitle>Workspace</SheetTitle>
              <SheetDescription>
                Pilih ruang kerja untuk melanjutkan perjalanan Anda.
              </SheetDescription>
            </SheetHeader>
            <div className="space-y-2 px-4 pb-6">
              {!creating && (
                <>
                  {workspaces.map((workspace) => (
                    <button
                      key={workspace.id}
                      type="button"
                      onClick={() => selectWorkspace(workspace.id)}
                      className={`flex min-h-11 w-full items-center justify-between rounded-lg border px-3 text-left text-sm ${
                        workspace.id === workspaceId
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-border bg-card text-foreground"
                      }`}
                    >
                      <span>{workspace.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {workspace.type === "personal" ? "Personal" : "Bisnis"}
                      </span>
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => setCreating(true)}
                    className="flex min-h-11 w-full items-center gap-2 rounded-lg border border-dashed border-border px-3 text-sm font-medium text-foreground"
                  >
                    <Plus className="size-4" />
                    Buat workspace baru
                  </button>
                </>
              )}
              {creating && createForm}
            </div>
          </SheetContent>
        </Sheet>
      </>
    );
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          tooltip="Workspace"
          onClick={() => setOpen((value) => !value)}
        >
          <Layers />
          <span>{current ? current.name : "Pilih Workspace"}</span>
          <ChevronRight
            className={`ml-auto size-4 shrink-0 transition-transform ${
              open ? "rotate-90" : ""
            }`}
          />
        </SidebarMenuButton>
        {open && (
          <SidebarMenuSub>
            {workspaces.map((workspace) => (
              <SidebarMenuSubItem key={workspace.id}>
                <SidebarMenuSubButton
                  isActive={workspace.id === workspaceId}
                  render={<button type="button" />}
                  onClick={() => selectWorkspace(workspace.id)}
                >
                  <span>
                    {workspace.name} (
                    {workspace.type === "personal" ? "Personal" : "Bisnis"})
                  </span>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
            <SidebarMenuSubItem>
              <SidebarMenuSubButton
                render={<button type="button" />}
                onClick={() => {
                  setCreating(true);
                  setOpen(false);
                }}
              >
                <Plus />
                <span>Buat workspace baru</span>
              </SidebarMenuSubButton>
            </SidebarMenuSubItem>
          </SidebarMenuSub>
        )}
      </SidebarMenuItem>

      {creating && <div className="mx-2 mt-2">{createForm}</div>}
    </SidebarMenu>
  );
}
