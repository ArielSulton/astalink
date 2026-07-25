"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowRight, Bot, CheckCircle2, LineChart, Loader2, PlusCircle, Send, Sparkles, Trash2, Wallet } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useWorkspace } from "@/components/workspace-context";
import { AllocationChart } from "@/components/allocation-chart";
import { AllocationBar } from "@/components/allocation/allocation-bar";
import { BusinessPanel, VetoPanel } from "@/components/allocation/business-panel";
import dynamic from "next/dynamic";
const PriceChart = dynamic(() => import("@/components/price-chart").then(m => ({ default: m.PriceChart })), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">Memuat chart…</div> });
import { TickerCard } from "@/components/ticker-card";
import { ChatMarkdown } from "@/components/chat-markdown";
import { AllocationBuyModal } from "@/components/allocation-buy-modal";
import {
  allocatedReplyIds,
  appendMessage,
  compositionRespondedIds,
  deleteConversation,
  getMessages,
  getOrCreateDashboardConversation,
} from "@/lib/chat-history";
import { createClient } from "@/lib/supabase/client";
import { api, type AgentRunResponse, type PortfolioResponse, type TickerChartData } from "@/lib/api-client";

const DEFAULT_WATCHLIST = ["BBCA.JK", "TLKM.JK", "ASII.JK", "BBRI.JK"];

const PROMPT_SUGGESTIONS = [
  "Optimalkan portofolio saya, fokus BBCA & TLKM, risiko sedang",
  "Review risiko portofolio dengan ASII dan BBRI",
  "Apa itu RSI dan bagaimana cara membacanya?",
];

function AiIdleState({ loading }: { loading: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-4 py-10 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-card border border-border">
        <Bot className="size-6 text-chart-2" />
      </div>
      <p className="text-sm font-semibold text-foreground">
        {loading ? "Menganalisis…" : "Siap membantu"}
      </p>
      <p className="text-xs leading-relaxed text-muted-foreground max-w-[240px]">
        {loading
          ? "AI sedang memindai pasar, risiko, dan regulasi untuk permintaanmu."
          : "Deskripsikan tujuan investasimu atau tanya apa saja soal pasar IDX dan regulasi OJK."}
      </p>
    </div>
  );
}

function AiSuggestions({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {PROMPT_SUGGESTIONS.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onPick(s)}
          className="px-3 py-1.5 rounded-full border border-border bg-secondary text-left text-xs text-muted-foreground hover:text-foreground hover:border-chart-2/40 hover:bg-chart-2/[0.06] transition-colors duration-150"
        >
          {s}
        </button>
      ))}
    </div>
  );
}

function AiComposer({
  message,
  setMessage,
  loading,
  onRun,
}: {
  message: string;
  setMessage: (v: string) => void;
  loading: boolean;
  onRun: () => void;
}) {
  return (
    <div className="space-y-2">
      <div className="relative">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onRun();
            }
          }}
          placeholder="Tanya apa saja, atau minta analisis alokasi…"
          className="w-full rounded-xl border border-border bg-secondary pl-3.5 pr-12 py-3 text-foreground text-sm resize-none focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200 placeholder:text-muted-foreground/50"
          rows={2}
        />
        <button
          onClick={onRun}
          disabled={loading || !message.trim()}
          aria-label={loading ? "Menganalisis" : "Kirim perintah"}
          className="absolute bottom-2.5 right-2.5 flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
        </button>
      </div>
      <p className="text-[10px] font-mono text-muted-foreground/60">
        Enter kirim · Eksekusi butuh persetujuan &amp; PIN Anda
      </p>
    </div>
  );
}

function fmtIdr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

function fmtSigned(n: number | null | undefined): string {
  if (n == null) return "—";
  const s = Math.abs(n).toLocaleString("id-ID", { maximumFractionDigits: 0 });
  return (n >= 0 ? "+Rp " : "-Rp ") + s;
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone?: number | null }) {
  const toneClass = tone == null ? "text-foreground" : tone >= 0 ? "text-emerald-400" : "text-rose-400";
  return (
    <div className="rounded-xl border border-border bg-card px-3.5 py-2.5">
      <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1">
        {label}
      </p>
      <p className={`font-mono text-sm font-bold tabular-nums leading-none ${toneClass}`}>{value}</p>
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] text-sm leading-relaxed whitespace-pre-wrap bg-primary text-primary-foreground rounded-xl rounded-tr-none px-3.5 py-2.5">
        {content}
      </p>
    </div>
  );
}

function AssistantBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-2.5">
      <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25 mt-0.5">
        <Bot className="size-3.5 text-chart-2" />
      </div>
      <div className="flex-1 min-w-0 text-sm leading-relaxed text-foreground bg-secondary border border-border rounded-xl rounded-tl-none px-3.5 py-2.5">
        <ChatMarkdown content={content} />
      </div>
    </div>
  );
}

type AiMessage = {
  id?: string | null;
  role: "user" | "assistant";
  content: string;
  result?: AgentRunResponse | null;
};

function rowToAiMessage(r: {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown>;
}): AiMessage {
  if (r.role === "assistant") {
    return { id: r.id, role: "assistant", content: r.content, result: (r.metadata?.result as AgentRunResponse | undefined) ?? null };
  }
  return { id: r.id, role: "user", content: r.content };
}

function AiThread({
  messages, loading, compact, workspaceId, allocatedIds, respondedCompositionIds, onAllocated, onComposition,
}: {
  messages: AiMessage[];
  loading: boolean;
  compact?: boolean;
  workspaceId: string | null;
  allocatedIds: Set<string>;
  respondedCompositionIds: Set<string>;
  onAllocated: (messageId: string | null | undefined, ticker: string, amount: number) => void;
  onComposition: (messageId: string | null | undefined, result: AgentRunResponse) => void;
}) {
  return (
    <div className="space-y-5">
      {messages.map((m, i) =>
        m.role === "user" ? (
          <UserBubble key={i} content={m.content} />
        ) : m.result ? (
          <div key={i} className="animate-fade-in">
            <AiResultView
              result={m.result}
              aiAnswer={m.content || null}
              compact={compact}
              workspaceId={workspaceId}
              allocated={!!m.id && allocatedIds.has(m.id)}
              compositionResolved={!!m.id && respondedCompositionIds.has(m.id)}
              onAllocated={(ticker, amount) => onAllocated(m.id, ticker, amount)}
              onComposition={(result) => onComposition(m.id, result)}
            />
          </div>
        ) : (
          <AssistantBubble key={i} content={m.content} />
        ),
      )}
      {loading && (
        <div className="flex justify-start">
          <div className="bg-secondary border border-border rounded-xl rounded-tl-none px-5 py-4">
            <div className="flex gap-1.5 items-center">
              {[0, 1, 2].map((i) => (
                <span key={i} className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AiResultView({
  result,
  aiAnswer,
  compact = false,
  workspaceId,
  allocated,
  compositionResolved,
  onAllocated,
  onComposition,
}: {
  result: AgentRunResponse;
  aiAnswer: string | null;
  compact?: boolean;
  workspaceId: string | null;
  /** True once the user executed the buy for this reply — the CTA is done. */
  allocated: boolean;
  /** True once Setuju/Tidak was already answered for this paused reply. */
  compositionResolved: boolean;
  onAllocated: (ticker: string, amount: number) => void;
  /** Called with the resumed result once Setuju/Tidak is answered on the
     composition gate (allocate_capital only). */
  onComposition: (result: AgentRunResponse) => void;
}) {
  const [buyOpen, setBuyOpen] = useState(false);
  const [resuming, setResuming] = useState(false);
  const isRejected = ["rejected", "rejected_after_max_revisions"].includes(result.legal_status ?? "");

  async function respondToComposition(approval: "approved" | "rejected") {
    if (!workspaceId || resuming) return;
    setResuming(true);
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      const resumed = await api.resumeAgent(
        { thread_id: result.thread_id, workspace_id: workspaceId, approval },
        session.access_token,
      );
      onComposition(resumed);
    } catch {
      toast.error("Gagal melanjutkan analisis. Coba lagi.");
    } finally {
      setResuming(false);
    }
  }

  const rankedWeights = [...(result.allocation_plan?.weights ?? [])]
    .filter((w) => w.weight > 0)
    .sort((a, b) => b.weight - a.weight);
  const suggestedTickers = rankedWeights.length ? rankedWeights.map((w) => w.ticker) : ["BBCA"];
  const suggestedAmount = rankedWeights.length && result.allocation_plan
    ? result.allocation_plan.cash * rankedWeights[0].weight
    : null;

  return (
    <div className="space-y-4">
      {(result.intent || result.legal_status) && (
        <div className="flex items-center gap-2 flex-wrap">
          {result.intent && (
            <Badge variant="outline" className="font-mono text-xs text-muted-foreground bg-secondary border-border">
              {result.intent}
            </Badge>
          )}
          {result.legal_status && <StatusBadge status={result.legal_status} />}
        </div>
      )}

      {aiAnswer && <AssistantBubble content={aiAnswer} />}

      {/* Layer 0 — the cash/stocks/business decision itself. Without this,
         an ALLOCATE_CAPITAL comparison ("saham atau modal ke bisnis saya?")
         silently dropped the business side entirely: the panel below only
         ever shows the optimizer's stock-only weights. */}
      {result.layer0_result?.allocation && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
                Kas vs Saham vs Bisnis
              </p>
              <span className="px-2 py-0.5 rounded border text-[10px] font-bold font-mono text-muted-foreground border-border">
                CONFIDENCE: {result.layer0_result.confidence_label} ({result.layer0_result.confidence}/100)
              </span>
            </div>
            <AllocationBar allocation={result.layer0_result.allocation} />
            {result.layer0_result.business_id && (
              <p className="text-xs text-muted-foreground">
                Bisnis yang dievaluasi: <strong className="text-foreground">{result.layer0_result.business_name}</strong>
                {" · "}skor bisnis{" "}
                <strong className="text-foreground">{result.layer0_result.business_score ?? "UNKNOWN"}</strong>
                {" vs "}skor saham{" "}
                <strong className="text-foreground">{result.layer0_result.stock_score ?? "—"}</strong>
              </p>
            )}
            {result.layer0_result.business_id ? (
              <BusinessPanel layer0={result.layer0_result} />
            ) : (
              <VetoPanel flags={result.layer0_result.veto_flags} />
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-border bg-secondary p-3">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono mb-1">
                  Kenapa tidak 100% saham
                </p>
                <p className="text-xs text-muted-foreground whitespace-pre-line">
                  {result.layer0_result.why_not_all_stocks || "—"}
                </p>
              </div>
              <div className="rounded-xl border border-border bg-secondary p-3">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono mb-1">
                  Kenapa tidak 100% bisnis
                </p>
                <p className="text-xs text-muted-foreground whitespace-pre-line">
                  {result.layer0_result.why_not_all_business || "—"}
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Composition gate (allocate_capital only): stop here until the user
         explicitly approves/rejects the split above — Layer 1 stock
         analysis + optimizer haven't run yet, so allocation_plan is still
         null and the sections below simply don't render until resumed. */}
      {result.awaiting_composition_approval && !compositionResolved && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Setuju dengan komposisi ini? Analisis saham + optimizer baru jalan
              setelah Anda konfirmasi.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={resuming}
                onClick={() => respondToComposition("approved")}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
              >
                {resuming ? "Memproses…" : "Setuju, Lanjutkan Analisis Saham"}
              </button>
              <button
                type="button"
                disabled={resuming}
                onClick={() => respondToComposition("rejected")}
                className="flex-1 py-2.5 rounded-xl border border-border bg-secondary text-foreground text-sm font-semibold hover:bg-secondary/80 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200"
              >
                Tidak, Batalkan
              </button>
            </div>
          </div>
        </>
      )}

      {result.allocation_plan && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-3">
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
              Rincian Saham (Optimizer)
            </p>
            <AllocationChart weights={result.allocation_plan.weights} cash={result.allocation_plan.cash} totalFunds={result.allocation_plan.total_funds} compact={compact} />
            {result.allocation_plan.narration && (
              <p className="text-sm text-muted-foreground leading-relaxed bg-secondary border border-border rounded-xl p-3.5">
                {result.allocation_plan.narration}
              </p>
            )}
          </div>
        </>
      )}

      {result.errors.length > 0 && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-2">
            <p className="text-xs font-bold text-rose-400 uppercase tracking-wider font-mono">Error Log</p>
            <div className="space-y-1 bg-rose-500/5 border border-rose-500/10 rounded-xl p-3.5">
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-rose-400 font-mono break-words">
                  [{e.node}] {e.reason}
                </p>
              ))}
            </div>
          </div>
        </>
      )}

      {allocated && (
        <>
          <Separator className="bg-border" />
          <div className="flex items-start gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.06] px-3.5 py-2.5">
            <CheckCircle2 className="size-4 shrink-0 text-emerald-400 mt-0.5" />
            <p className="text-xs leading-relaxed text-emerald-300">
              Dana dari rekomendasi ini sudah dialokasikan — transaksi tercatat dan
              posisi diperbarui.{" "}
              <Link href="/portfolio" className="underline underline-offset-2 hover:text-emerald-200">
                Lihat portofolio
              </Link>
            </p>
          </div>
        </>
      )}

      {!isRejected && result.allocation_plan && result.user_approval === null && !allocated && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Ini baru rekomendasi — belum ada dana yang berpindah. Alokasikan langsung di
              sini, atau tinjau dulu detail kepatuhan legalnya.
            </p>
            <button
              type="button"
              disabled={!workspaceId}
              onClick={() => setBuyOpen(true)}
              className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200"
            >
              <PlusCircle className="h-4 w-4" />
              Setujui &amp; Alokasikan Dana
            </button>
            <Link
              href={`/approvals/${result.audit_id}`}
              className="block w-full text-center py-2 rounded-xl border border-border bg-secondary text-foreground text-xs font-semibold hover:bg-secondary/80 transition-all duration-200"
            >
              Tinjau Detail Kepatuhan Legal
            </Link>
          </div>
        </>
      )}

      {buyOpen && workspaceId && (
        <AllocationBuyModal
          workspaceId={workspaceId}
          suggestedTickers={suggestedTickers}
          suggestedAmount={suggestedAmount}
          onClose={() => setBuyOpen(false)}
          onSuccess={(ticker, amount) => {
            setBuyOpen(false);
            onAllocated(ticker, amount);
          }}
        />
      )}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();

  const [watchlist, setWatchlist] = useState<TickerChartData[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string>(DEFAULT_WATCHLIST[0]);
  const [marketLoading, setMarketLoading] = useState(true);

  const { workspaceId } = useWorkspace();
  const [cashBalance, setCashBalance] = useState<number | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiMessages, setAiMessages] = useState<AiMessage[]>([]);
  // Ids of replies whose allocation was already executed — their "Setujui &
  // Alokasikan Dana" CTA is spent and must not come back after a reload.
  const [allocatedIds, setAllocatedIds] = useState<Set<string>>(new Set());
  // Ids of paused replies whose composition gate has already been answered —
  // without this, "Setuju/Tidak" would reappear on the same reply forever
  // after a reload, since awaiting_composition_approval is stored as-is.
  const [respondedCompositionIds, setRespondedCompositionIds] = useState<Set<string>>(new Set());
  const [convId, setConvId] = useState<string | null>(null);
  // Without this, every dashboard message started a brand-new, contextless
  // LangGraph thread — a follow-up question in the same session got a
  // generic answer with zero awareness of what was just computed. Also the
  // hard prerequisite for the composition-gate resume: it must reuse the
  // exact thread_id the paused run was invoked under.
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Bumped after a successful "Setujui & Alokasikan Dana" from the AI panel
  // so the cash balance / portfolio strip refetch and reflect the new buy.
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    api
      .getWatchlist(DEFAULT_WATCHLIST)
      .then((data) => setWatchlist(data))
      .catch(() => {})
      .finally(() => setMarketLoading(false));
  }, []);

  // Saldo kas sandbox milik workspace terpilih (RLS-scoped).
  useEffect(() => {
    if (!workspaceId) {
      setCashBalance(null);
      return;
    }
    const sb = createClient();
    sb.from("workspaces")
      .select("cash_balance")
      .eq("id", workspaceId)
      .single()
      .then(({ data }) => {
        setCashBalance(data?.cash_balance != null ? Number(data.cash_balance) : null);
      });
  }, [workspaceId, refreshKey]);

  // Sandbox portfolio summary (holdings + P&L) for the dashboard strip.
  useEffect(() => {
    if (!workspaceId) {
      setPortfolio(null);
      return;
    }
    (async () => {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session) return;
      try {
        setPortfolio(await api.getPortfolio(workspaceId, session.access_token));
      } catch {
        setPortfolio(null);
      }
    })();
  }, [workspaceId, aiMessages.length, refreshKey]);

  // Persisted per-user AI assistant history (surface='dashboard').
  useEffect(() => {
    if (!workspaceId) {
      setAiMessages([]);
      setAllocatedIds(new Set());
      setRespondedCompositionIds(new Set());
      setConvId(null);
      setThreadId(undefined);
      return;
    }
    let cancelled = false;
    (async () => {
      const conv = await getOrCreateDashboardConversation(workspaceId);
      if (cancelled || !conv) return;
      setConvId(conv.id);
      const rows = await getMessages(conv.id);
      if (!cancelled) {
        const mapped = rows.map(rowToAiMessage);
        setAiMessages(mapped);
        setAllocatedIds(allocatedReplyIds(rows));
        setRespondedCompositionIds(compositionRespondedIds(rows));
        const lastResult = [...mapped].reverse().find((m) => m.result)?.result;
        setThreadId(lastResult?.thread_id);
      }
    })();
    return () => { cancelled = true; };
  }, [workspaceId]);

  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  async function handleRun() {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!message.trim()) { toast.error("Masukkan perintah."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { router.push("/login"); return; }

    const query = message.trim();
    setMessage("");
    setLoading(true);
    setAiMessages((prev) => [...prev, { role: "user", content: query }]);

    // Ensure the dashboard conversation exists, then persist the user turn.
    let cid = convId;
    if (!cid) {
      const conv = await getOrCreateDashboardConversation(workspaceId);
      cid = conv?.id ?? null;
      setConvId(cid);
    }
    if (cid) await appendMessage(cid, { role: "user", content: query });

    try {
      const res = await api.runAgent(
        { message: query, workspace_id: workspaceId, thread_id: threadId },
        session.access_token,
      );
      setThreadId(res.thread_id);
      const answer =
        [...res.messages].reverse().find((m) => m.type === "AIMessage")?.content ?? "";
      const ls = res.legal_status ?? "";
      const rejected = ["rejected", "rejected_after_max_revisions"].includes(ls);
      // Persist first so the reply carries its row id: the id is what a later
      // "already allocated" marker points at.
      const msgId = cid
        ? await appendMessage(cid, {
            role: "assistant",
            content: answer,
            auditId: res.audit_id,
            requiresApproval: !!res.allocation_plan && res.user_approval === null && !rejected,
            metadata: { result: res },
          })
        : null;
      setAiMessages((prev) => [...prev, { id: msgId, role: "assistant", content: answer, result: res }]);
      if (res.awaiting_composition_approval) {
        toast.info("Setuju dengan komposisinya? Konfirmasi dulu sebelum lanjut analisis saham.");
      } else if (rejected) {
        toast.error(`Ditolak secara legal: ${ls}`);
      } else if (!res.allocation_plan) {
        toast.success("Jawaban siap.");
      } else if (res.user_approval === null) {
        toast.info("Menunggu approval Anda — gunakan tombol Tinjau & Setujui.");
      } else {
        toast.success("Analisis selesai — silakan tinjau alokasi.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menghubungi agen.");
      const fail = "Maaf, terjadi kesalahan. Coba lagi.";
      setAiMessages((prev) => [...prev, { role: "assistant", content: fail }]);
      if (cid) await appendMessage(cid, { role: "assistant", content: fail });
    } finally {
      setLoading(false);
    }
  }

  // A Setuju/Tidak answer on the composition gate resumes the SAME
  // audit/thread and always produces a brand-new terminal (or re-paused, in
  // theory) result — appended as a new row, same append-only pattern as
  // handleAllocated (chat_messages has no update policy under RLS).
  async function handleComposition(
    messageId: string | null | undefined,
    result: AgentRunResponse,
  ) {
    setThreadId(result.thread_id);
    if (messageId) setRespondedCompositionIds((prev) => new Set(prev).add(messageId));
    const answer =
      [...result.messages].reverse().find((m) => m.type === "AIMessage")?.content ?? "";
    const ls = result.legal_status ?? "";
    const rejected = ["rejected", "rejected_after_max_revisions"].includes(ls);
    const msgId = convId
      ? await appendMessage(convId, {
          role: "assistant",
          content: answer,
          auditId: result.audit_id,
          requiresApproval: !!result.allocation_plan && result.user_approval === null && !rejected,
          metadata: { result, ...(messageId ? { composition_for: messageId } : {}) },
        })
      : null;
    setAiMessages((prev) => [...prev, { id: msgId, role: "assistant", content: answer, result }]);
  }

  // A successful buy retires that reply's CTA and leaves a confirmation in the
  // thread. The marker rides on the confirmation row (metadata.allocated_for)
  // so it survives a reload without needing an update policy on chat_messages.
  async function handleAllocated(
    messageId: string | null | undefined,
    ticker: string,
    amount: number,
  ) {
    setRefreshKey((k) => k + 1);
    if (messageId) setAllocatedIds((prev) => new Set(prev).add(messageId));
    const confirm =
      `✓ **Alokasi berhasil** — ${fmtIdr(amount)} masuk ke **${ticker}**. ` +
      `Transaksi tercatat dan posisi di halaman Portofolio sudah diperbarui.`;
    const id = convId
      ? await appendMessage(convId, {
          role: "assistant",
          content: confirm,
          metadata: messageId ? { allocated_for: messageId } : {},
        })
      : null;
    setAiMessages((prev) => [...prev, { id, role: "assistant", content: confirm }]);
  }

  async function clearDashboard() {
    const id = convId;
    setAiMessages([]);
    setAllocatedIds(new Set());
    setRespondedCompositionIds(new Set());
    setConvId(null);
    setThreadId(undefined);
    if (id) await deleteConversation(id);
  }

  const hasThread = aiMessages.length > 0;

  return (
    <SidebarProvider
      className="min-h-full"
      style={{ "--sidebar-width": "26rem" } as React.CSSProperties}
    >
      {/* ── Main content ── */}
      <SidebarInset className="bg-background">
        {/* Portfolio summary strip */}
        {portfolio && portfolio.holdings.length > 0 && (
          <div className="border-b border-border px-6 py-4 bg-card/20 animate-fade-in">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <LineChart className="size-4 text-chart-2" />
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground font-mono">
                  Portofolio
                </span>
              </div>
              <Link
                href="/portfolio"
                className="inline-flex items-center gap-1 text-xs font-medium text-chart-2 hover:underline"
              >
                Lihat <ArrowRight className="size-3" />
              </Link>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <MiniStat label="Total Ekuitas" value={fmtIdr(portfolio.total_equity)} />
              <MiniStat label="Kas" value={fmtIdr(portfolio.cash_balance)} />
              <MiniStat label="Unrealized P&L" value={fmtSigned(portfolio.total_unrealized_pnl)}
                tone={portfolio.total_unrealized_pnl} />
              <MiniStat label="Realized P&L" value={fmtSigned(portfolio.total_realized_pnl)}
                tone={portfolio.total_realized_pnl} />
            </div>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {portfolio.holdings.slice(0, 6).map((h) => (
                <span key={h.ticker}
                  className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-secondary border border-border text-muted-foreground">
                  {h.ticker}
                </span>
              ))}
              {portfolio.holdings.length > 6 && (
                <span className="text-[10px] font-mono text-muted-foreground/60 px-1 py-0.5">
                  +{portfolio.holdings.length - 6}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Market Watch Header */}
        <div className="border-b border-border px-6 py-5 bg-card/40">
          <PageHeader eyebrow="Market Watch" title="IDX Blue Chips" className="mb-5">
            {cashBalance != null && (
              <div className="flex items-center gap-2.5 rounded-xl border border-border bg-card px-3.5 py-1.5 animate-fade-in">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25">
                  <Wallet className="size-3.5 text-chart-2" />
                </div>
                <div className="leading-tight">
                  <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                    Saldo
                  </p>
                  <p className="font-mono text-sm font-bold text-foreground tabular-nums">
                    Rp {cashBalance.toLocaleString("id-ID", { maximumFractionDigits: 0 })}
                  </p>
                </div>
              </div>
            )}
          </PageHeader>

          <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
            {DEFAULT_WATCHLIST.map((ticker) => {
              const data = watchlist.find((t) => t.ticker === ticker);
              return (
                <TickerCard
                  key={ticker}
                  ticker={ticker}
                  lastClose={marketLoading ? null : (data?.last_close ?? null)}
                  priceChangePct={marketLoading ? null : (data?.price_change_pct ?? null)}
                  rsi14={marketLoading ? null : (data?.rsi14 ?? null)}
                  series={marketLoading ? null : (data?.price_series.map((p) => p.close) ?? null)}
                  selected={selectedTicker === ticker}
                  onClick={() => setSelectedTicker(ticker)}
                />
              );
            })}
          </div>
        </div>

        {/* Chart Area */}
        <div className="px-6 py-5">
          {marketLoading ? (
            <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono tracking-wider">
              <span className="w-2 h-2 rounded-full bg-chart-2 animate-ping mr-2.5" />
              Memuat data pasar…
            </div>
          ) : selectedData && selectedData.price_series.length > 0 ? (
            <PriceChart
              ticker={selectedData.ticker}
              data={selectedData.price_series}
              lastClose={selectedData.last_close}
              priceChangePct={selectedData.price_change_pct}
              bbUpper={selectedData.bb_upper}
              bbLower={selectedData.bb_lower}
            />
          ) : (
            <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">
              Data tidak tersedia untuk {selectedTicker}
            </div>
          )}
        </div>

        {/* Mobile/tablet: floating AI bubble + bottom sheet (right sidebar hidden < lg) */}
        <div className="lg:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Buka Asisten AI"
            className="fixed bottom-5 right-5 z-40 flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-[0_12px_32px_-8px_rgba(0,0,0,0.55)] hover:bg-primary/90 active:scale-95 transition-all duration-200"
          >
            {loading ? <Loader2 className="size-6 animate-spin" /> : <Sparkles className="size-6" />}
            {hasThread && !mobileOpen && (
              <span className="absolute -top-0.5 -right-0.5 size-3.5 rounded-full bg-chart-2 border-2 border-background animate-pulse" />
            )}
          </button>

          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetContent side="bottom" className="h-[85svh] rounded-t-2xl p-0 gap-0 bg-background">
              <SheetHeader className="border-b border-border px-5 py-4 pr-12">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-chart-2/10 border border-chart-2/25">
                      <Sparkles className="size-4 text-chart-2" />
                    </div>
                    <div className="min-w-0">
                      <SheetTitle className="text-sm font-bold tracking-tight">Asisten AI</SheetTitle>
                      <SheetDescription className="text-xs truncate">
                        Analisis alokasi &amp; tanya-jawab IDX
                      </SheetDescription>
                    </div>
                  </div>
                  {hasThread && (
                    <button
                      onClick={clearDashboard}
                      className="shrink-0 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 font-medium py-1 px-2.5 rounded-lg hover:bg-secondary transition-all"
                    >
                      <Trash2 className="size-3.5" /> Clear
                    </button>
                  )}
                </div>
              </SheetHeader>

              <div className="flex-1 overflow-y-auto px-5 py-4">
                {hasThread ? (
                  <AiThread
                    messages={aiMessages}
                    loading={loading}
                    compact
                    workspaceId={workspaceId}
                    allocatedIds={allocatedIds}
                    respondedCompositionIds={respondedCompositionIds}
                    onAllocated={handleAllocated}
                    onComposition={handleComposition}
                  />
                ) : (
                  <AiIdleState loading={loading} />
                )}
              </div>

              <div className="border-t border-border p-4 space-y-3">
                {!hasThread && <AiSuggestions onPick={setMessage} />}
                <AiComposer message={message} setMessage={setMessage} loading={loading} onRun={handleRun} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </SidebarInset>

      {/* ── Right AI sidebar (desktop) ── */}
      <Sidebar
        side="right"
        collapsible="none"
        className="sticky top-0 hidden h-[calc(100svh-3rem)] border-l border-border lg:flex"
      >
        <SidebarHeader className="border-b border-sidebar-border px-4 py-3.5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-chart-2/10 border border-chart-2/25">
                <Sparkles className="size-4 text-chart-2" />
              </div>
              <div className="min-w-0">
                <h2 className="text-sidebar-foreground font-bold text-sm tracking-tight">Asisten AI</h2>
                <p className="text-muted-foreground text-xs truncate">
                  Analisis alokasi &amp; tanya-jawab IDX
                </p>
              </div>
            </div>
            {hasThread && (
              <button
                onClick={clearDashboard}
                title="Bersihkan percakapan"
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 font-medium py-1 px-2.5 rounded-lg hover:bg-secondary transition-all"
              >
                <Trash2 className="size-3.5" /> Clear
              </button>
            )}
          </div>
        </SidebarHeader>

        <SidebarContent className="px-4 py-4">
          {hasThread ? (
            <AiThread
              messages={aiMessages}
              loading={loading}
              compact
              workspaceId={workspaceId}
              allocatedIds={allocatedIds}
              respondedCompositionIds={respondedCompositionIds}
              onAllocated={handleAllocated}
              onComposition={handleComposition}
            />
          ) : (
            <AiIdleState loading={loading} />
          )}
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border p-4 gap-3">
          {!hasThread && <AiSuggestions onPick={setMessage} />}
          <AiComposer message={message} setMessage={setMessage} loading={loading} onRun={handleRun} />
        </SidebarFooter>
      </Sidebar>
    </SidebarProvider>
  );
}
