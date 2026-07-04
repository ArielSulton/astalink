"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Building2 } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { api, LAST_BUSINESS_KEY } from "@/lib/api-client";
import { LAST_WORKSPACE_KEY } from "@/components/workspace-context";
import { createClient } from "@/lib/supabase/client";

export default function BusinessDetailShortcutPage() {
  const router = useRouter();
  const [state, setState] = useState<"loading" | "empty">("loading");

  useEffect(() => {
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) { router.replace("/login"); return; }

      const workspaceId = localStorage.getItem(LAST_WORKSPACE_KEY);
      if (!workspaceId) { setState("empty"); return; }

      try {
        const businesses = await api.listBusinesses(workspaceId, session.access_token);
        if (businesses.length === 0) { setState("empty"); return; }
        const remembered = businesses.find((b) => b.id === localStorage.getItem(LAST_BUSINESS_KEY));
        router.replace(`/business/${(remembered ?? businesses[0]).id}`);
      } catch {
        setState("empty");
      }
    })();
  }, [router]);

  if (state === "loading") {
    return <div className="p-8 text-muted-foreground text-sm">Memuat…</div>;
  }

  return (
    <div className="p-8 max-w-4xl w-full mx-auto">
      <EmptyState icon={Building2} title="Belum ada bisnis">
        <Link href="/business" className="text-chart-2 underline">
          Tambahkan bisnis pertama Anda
        </Link>
      </EmptyState>
    </div>
  );
}
