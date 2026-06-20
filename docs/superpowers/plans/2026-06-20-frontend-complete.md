# Frontend Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build all missing frontend pieces so the app is demo-ready: protected layout with sidebar nav, dashboard agent-command form, enriched audit timeline, and a settings index page.

**Architecture:** Add a shared `(protected)/layout.tsx` that renders a sidebar with nav links and a `WorkspaceSwitcher` — all inner pages inherit it. Dashboard is rewritten as a client page with a form that calls `POST /api/v1/agent/run`; results (intent, allocation chart, transactions) render inline. Audit timeline pulls richer events from the `payload` JSON already stored in Supabase. Settings gets an index page linking to `/settings/pin`.

**Tech Stack:** Next.js 16 App Router, Shadcn UI (Button, Card, Badge, Separator), Tailwind CSS v4, lucide-react icons, sonner toasts, react-hook-form + zod, TypeScript 5.

## Global Constraints

- All new files are TypeScript (`.tsx` / `.ts`). No `.js`.
- Use Shadcn primitives (`Button`, `Card`, `Badge`, `Separator`, `Input`, `Label`, `Textarea`) — never raw `<button>` / `<input>` in pages (existing pages that do are out of scope to fix).
- Import aliases: `@/components/...`, `@/lib/...`, `@/app/...` — no relative `../../` imports.
- Supabase client in client components: `createClient` from `@/lib/supabase/client`. Server components: `@/lib/supabase/server`.
- Tailwind v4 — no `bg-gray-100`-style JIT purge issues; stick to classes already used elsewhere.
- No test runner is configured. Verification = `npx tsc --noEmit` (zero errors) + manual browser check described per task.
- Do NOT modify `app/layout.tsx`, auth pages, or any file under `components/ui/`.

---

### Task 1: Protected layout with sidebar navigation

**Files:**
- Create: `frontend/app/(protected)/layout.tsx`
- Create: `frontend/components/app-sidebar.tsx`

**Interfaces:**
- Produces: `<AppSidebar />` — a React component that accepts no props
- Produces: `(protected)/layout.tsx` — Next.js layout that wraps `{children}` with sidebar

- [ ] **Step 1: Create the sidebar component**

Create `frontend/components/app-sidebar.tsx`:

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CheckSquare, ArrowLeftRight, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/transactions", label: "Transaksi", icon: ArrowLeftRight },
  { href: "/settings", label: "Pengaturan", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex flex-col w-56 shrink-0 border-r min-h-screen bg-background">
      <div className="px-4 py-5 border-b">
        <span className="font-semibold text-lg tracking-tight">Astalink</span>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              pathname.startsWith(href)
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: Create the protected layout**

Create `frontend/app/(protected)/layout.tsx`:

```tsx
import { AppSidebar } from "@/components/app-sidebar";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 4: Manual browser check**

Start dev server (`npm run dev`). Navigate to `/dashboard`. Verify:
- Sidebar appears on the left with four nav items.
- Active link (`/dashboard`) has primary background.
- Clicking "Approvals" navigates to `/approvals` and highlights that link.
- No layout shift or scroll issues on `/transactions`.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(protected\)/layout.tsx frontend/components/app-sidebar.tsx
git commit -m "feat(frontend): add protected layout with sidebar navigation"
```

---

### Task 2: Add runAgent to api-client

**Files:**
- Modify: `frontend/lib/api-client.ts`

**Interfaces:**
- Produces: `AgentRunRequest` interface
- Produces: `AgentRunResponse` interface
- Produces: `api.runAgent(body: AgentRunRequest, token: string): Promise<AgentRunResponse>`

- [ ] **Step 1: Add types and method to api-client**

Open `frontend/lib/api-client.ts` and append the following **before** the closing of the file (after the `export const api = { ... }` block, add the new types before it):

Add these interfaces after the existing `ApprovalDetail` interface:

```ts
export interface AgentRunRequest {
  message: string;
  workspace_id: string;
  thread_id?: string;
}

export interface AgentRunResponse {
  audit_id: string;
  thread_id: string;
  intent: string | null;
  legal_status: string | null;
  user_approval: string | null;
  allocation_plan: {
    weights: { ticker: string; weight: number }[];
    cash: number;
    cash_buffer: number;
    narration: string;
    relaxations_applied: string[];
  } | null;
  transactions: Record<string, unknown>[];
  revision_count: number;
  messages: { type: string; content: string }[];
  errors: { node: string; reason: string }[];
}
```

Then add `runAgent` inside the `api` object:

```ts
  runAgent: (body: AgentRunRequest, token: string) =>
    jsonFetch<AgentRunResponse>(
      "/api/v1/agent/run",
      { method: "POST", body: JSON.stringify(body) },
      token,
    ),
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api-client.ts
git commit -m "feat(api-client): add runAgent method and AgentRunRequest/Response types"
```

---

### Task 3: Dashboard — agent command form + result display

**Files:**
- Modify: `frontend/app/(protected)/dashboard/page.tsx`

**Interfaces:**
- Consumes: `api.runAgent` from Task 2
- Consumes: `WorkspaceSwitcher` from `@/components/workspace-switcher`
- Consumes: `AllocationChart` from `@/components/allocation-chart`
- Consumes: `AgentRunResponse` type from Task 2

- [ ] **Step 1: Rewrite dashboard page**

Replace the entire contents of `frontend/app/(protected)/dashboard/page.tsx` with:

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import { AllocationChart } from "@/components/allocation-chart";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse } from "@/lib/api-client";

export default function DashboardPage() {
  const router = useRouter();
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);

  const handleRun = async () => {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!message.trim()) { toast.error("Masukkan perintah."); return; }
    setLoading(true);
    setResult(null);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) { router.push("/login"); return; }
      const res = await api.runAgent(
        { message: message.trim(), workspace_id: workspaceId },
        session.access_token,
      );
      setResult(res);
      if (res.user_approval === null && res.legal_status !== "rejected") {
        toast.info("Menunggu approval Anda di halaman Approvals.");
      } else if (res.transactions.length > 0) {
        toast.success("Eksekusi selesai. Lihat Transaksi untuk detail.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setLoading(false);
    }
  };

  const legalColor: Record<string, string> = {
    approved: "bg-green-100 text-green-800",
    partial: "bg-yellow-100 text-yellow-800",
    rejected: "bg-red-100 text-red-800",
    rejected_after_max_revisions: "bg-red-100 text-red-800",
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <WorkspaceSwitcher current={workspaceId} onChange={setWorkspaceId} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Kirim Perintah ke AI</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            className="w-full border rounded-md px-3 py-2 text-sm min-h-[80px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="Contoh: Alokasikan 50 juta ke saham BBCA.JK, TLKM.JK, dan ASII.JK dengan profil risiko moderat"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={loading}
          />
          <Button onClick={handleRun} disabled={loading || !workspaceId} className="w-full">
            {loading ? "Menganalisis…" : "Jalankan Analisis"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              Hasil Analisis
              <Badge variant="outline" className="font-mono text-xs">
                {result.audit_id.slice(0, 8)}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2 text-sm">
              <span className="text-muted-foreground">Intent:</span>
              <span className="font-medium">{result.intent ?? "—"}</span>
              {result.legal_status && (
                <>
                  <Separator orientation="vertical" className="h-4 self-center" />
                  <span className="text-muted-foreground">Legal:</span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${legalColor[result.legal_status] ?? "bg-muted"}`}
                  >
                    {result.legal_status}
                  </span>
                </>
              )}
            </div>

            {result.allocation_plan && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium mb-2">Alokasi yang Diusulkan</p>
                  <AllocationChart weights={result.allocation_plan.weights} />
                  {result.allocation_plan.narration && (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {result.allocation_plan.narration}
                    </p>
                  )}
                </div>
              </>
            )}

            {result.errors.length > 0 && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium text-destructive mb-1">Errors</p>
                  <ul className="text-xs text-destructive space-y-0.5">
                    {result.errors.map((e, i) => (
                      <li key={i}>{e.node}: {e.reason}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}

            {(result.user_approval === null && result.legal_status !== "rejected") && (
              <>
                <Separator />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/approvals/${result.audit_id}`)}
                >
                  Review & Approve →
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add Sonner Toaster to root layout**

Open `frontend/app/layout.tsx`. Add the import and `<Toaster />` inside `<body>`:

```tsx
import type { Metadata } from "next";
import { Inter, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Astalink",
  description: "Next.js + FastAPI + Supabase Template",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body className={inter.className}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 4: Manual browser check**

With dev server running, go to `/dashboard`:
- Workspace switcher renders top-right.
- Without workspace selected → clicking "Jalankan Analisis" shows error toast.
- With workspace but no `GOOGLE_API_KEY` set: backend returns 500 → toast shows the error message.
- If API keys are set: result card appears with intent badge and allocation chart.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(protected\)/dashboard/page.tsx frontend/app/layout.tsx
git commit -m "feat(dashboard): add agent command form and result display"
```

---

### Task 4: Enrich audit timeline

**Files:**
- Modify: `frontend/app/(protected)/audit/[auditId]/page.tsx`
- Modify: `frontend/components/audit-timeline.tsx`

**Interfaces:**
- Consumes: `AuditTimeline` — existing component, interface extended to accept optional `variant`
- Produces: `AuditTimeline` props: `events: { ts: string; node: string; status: string; variant?: "default" | "success" | "error" }[]`

- [ ] **Step 1: Update AuditTimeline component**

Replace entire `frontend/components/audit-timeline.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface TimelineEvent {
  ts: string;
  node: string;
  status: string;
  variant?: "default" | "success" | "error";
}

export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  const dotColor: Record<string, string> = {
    default: "bg-blue-500",
    success: "bg-green-500",
    error: "bg-red-500",
  };

  return (
    <ol className="border-l-2 border-gray-200 pl-4 space-y-4">
      {events.map((e, i) => (
        <li key={i} className="relative">
          <span
            className={cn(
              "absolute -left-[9px] top-1 w-3 h-3 rounded-full",
              dotColor[e.variant ?? "default"],
            )}
          />
          <div className="text-xs text-muted-foreground">
            {new Date(e.ts).toLocaleString("id-ID")}
          </div>
          <div className="font-medium text-sm">{e.node}</div>
          <div className="text-sm text-muted-foreground">{e.status}</div>
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 2: Enrich audit page to pull more events from payload**

Replace entire `frontend/app/(protected)/audit/[auditId]/page.tsx`:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuditTimeline } from "@/components/audit-timeline";
import { Badge } from "@/components/ui/badge";

interface AuditRow {
  audit_id: string;
  status: string;
  intent: string | null;
  created_at: string;
  completed_at: string | null;
  payload: Record<string, unknown>;
}

type TimelineEvent = {
  ts: string;
  node: string;
  status: string;
  variant?: "default" | "success" | "error";
};

function buildEvents(row: AuditRow): TimelineEvent[] {
  const events: TimelineEvent[] = [
    { ts: row.created_at, node: "n1_intent", status: `Intent: ${row.intent ?? "unknown"}` },
  ];

  const p = row.payload as Record<string, unknown>;

  if (p.market) events.push({ ts: row.created_at, node: "n2a_market", status: "Analisis pasar selesai" });
  if (p.business) events.push({ ts: row.created_at, node: "n2b_business", status: "Analisis bisnis selesai" });
  if (p.risk) events.push({ ts: row.created_at, node: "n2c_risk", status: "Analisis risiko selesai" });
  if (p.optimizer) events.push({ ts: row.created_at, node: "n5_optimizer", status: "Alokasi dioptimasi" });

  if (p.legal) {
    const legal = p.legal as Record<string, unknown>;
    const legalStatus = (legal.status as string) ?? "unknown";
    events.push({
      ts: row.created_at,
      node: "n3_legal",
      status: `Legal: ${legalStatus}`,
      variant: legalStatus === "approved" ? "success" : legalStatus === "rejected" ? "error" : "default",
    });
  }

  if (row.status === "awaiting_approval") {
    events.push({ ts: row.created_at, node: "n6_hitl", status: "Menunggu approval pengguna" });
  }

  if (row.completed_at) {
    const isSuccess = row.status === "completed";
    events.push({
      ts: row.completed_at,
      node: "Selesai",
      status: row.status,
      variant: isSuccess ? "success" : row.status.includes("rejected") ? "error" : "default",
    });
  }

  return events;
}

const STATUS_COLOR: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  awaiting_approval: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-800",
  rejected: "bg-red-100 text-red-800",
  rejected_after_max_revisions: "bg-red-100 text-red-800",
};

export default function AuditPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [row, setRow] = useState<AuditRow | null>(null);

  useEffect(() => {
    const sb = createClient();
    sb.from("audit_log").select("*").eq("audit_id", auditId).single()
      .then(({ data }) => setRow(data as AuditRow | null));
  }, [auditId]);

  if (!row) return <p className="p-6 text-muted-foreground">Memuat…</p>;

  return (
    <main className="p-6 max-w-2xl mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[row.status] ?? "bg-muted"}`}
        >
          {row.status}
        </span>
      </div>
      <p className="text-xs text-muted-foreground font-mono">{auditId}</p>
      <AuditTimeline events={buildEvents(row)} />
    </main>
  );
}
```

- [ ] **Step 3: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 4: Manual browser check**

Navigate to any `/audit/<auditId>`. Verify:
- Status badge appears next to title.
- Timeline shows at least the intent event with formatted Indonesian timestamp.
- Completed audits show green dot on final event.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/audit-timeline.tsx frontend/app/\(protected\)/audit/\[auditId\]/page.tsx
git commit -m "feat(audit): enrich timeline with payload events and status colors"
```

---

### Task 5: Settings index page

**Files:**
- Create: `frontend/app/(protected)/settings/page.tsx`

**Interfaces:**
- Produces: `/settings` route that links to `/settings/pin`

- [ ] **Step 1: Create settings index page**

Create `frontend/app/(protected)/settings/page.tsx`:

```tsx
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyRound } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-lg mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Pengaturan</h1>
      <Link href="/settings/pin">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <CardHeader className="flex flex-row items-center gap-3 space-y-0">
            <KeyRound className="h-5 w-5 text-muted-foreground" />
            <div>
              <CardTitle className="text-base">PIN Persetujuan</CardTitle>
              <CardDescription>Atur PIN untuk mengkonfirmasi transaksi</CardDescription>
            </div>
          </CardHeader>
        </Card>
      </Link>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Manual browser check**

Navigate to `/settings`. Verify:
- Settings card renders with key icon.
- Clicking card navigates to `/settings/pin`.
- "Pengaturan" nav item in sidebar is highlighted.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(protected\)/settings/page.tsx
git commit -m "feat(settings): add settings index page with PIN card link"
```
