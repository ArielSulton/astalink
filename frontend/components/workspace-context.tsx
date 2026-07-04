"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { createClient } from "@/lib/supabase/client";

export interface WorkspaceRecord {
  id: string;
  name: string;
  type: "personal" | "business";
}

export const LAST_WORKSPACE_KEY = "astalink_last_workspace_id";

interface WorkspaceContextValue {
  workspaceId: string | null;
  setWorkspaceId: (id: string) => void;
  workspaces: WorkspaceRecord[];
  refreshWorkspaces: (autoSelect: boolean) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaceId, setWorkspaceIdState] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceRecord[]>([]);

  function setWorkspaceId(id: string) {
    setWorkspaceIdState(id);
    localStorage.setItem(LAST_WORKSPACE_KEY, id);
  }

  function refreshWorkspaces(autoSelect: boolean) {
    const sb = createClient();
    sb.from("workspaces").select("id,name,type").then(({ data }) => {
      const list = (data as WorkspaceRecord[]) || [];
      setWorkspaces(list);
      // Don't make the user pick when there's nothing to choose between (or
      // a remembered choice already answers it) — only surface the dropdown
      // as a real decision when there's more than one workspace and no prior
      // selection cached from a previous visit.
      if (autoSelect && !workspaceId && list.length > 0) {
        const remembered = list.find((w) => w.id === localStorage.getItem(LAST_WORKSPACE_KEY));
        setWorkspaceId(remembered ? remembered.id : list[0].id);
      }
    });
  }

  useEffect(() => { refreshWorkspaces(true); }, []);

  return (
    <WorkspaceContext.Provider value={{ workspaceId, setWorkspaceId, workspaces, refreshWorkspaces }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within a WorkspaceProvider");
  return ctx;
}
