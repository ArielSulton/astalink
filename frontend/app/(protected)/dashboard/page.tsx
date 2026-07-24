"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowRight, Bot, LineChart, Loader2, Send, Sparkles, Wallet } from "lucide-react";
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
import dynamic from "next/dynamic";
const PriceChart = dynamic(() => import("@/components/price-chart").then(m => ({ default: m.PriceChart })), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-xs font-mono">Memuat chart…</div> });
import { TickerCard } from "@/components/ticker-card";
import { ChatMarkdown } from "@/components/chat-markdown";
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

function AiResultView({
  result,
  aiAnswer,
  userQuery,
  isRejected,
  onApprove,
  compact = false,
}: {
  result: AgentRunResponse;
  aiAnswer: string | null;
  userQuery: string | null;
  isRejected: boolean;
  onApprove: () => void;
  compact?: boolean;
}) {
  return (
    <div className="space-y-4">
      {userQuery && (
        <div className="flex justify-end">
          <p className="max-w-[85%] text-sm leading-relaxed whitespace-pre-wrap bg-primary text-primary-foreground rounded-xl rounded-tr-none px-3.5 py-2.5">
            {userQuery}
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {result.intent && (
          <Badge variant="outline" className="font-mono text-xs text-muted-foreground bg-secondary border-border">
            {result.intent}
          </Badge>
        )}
        {result.legal_status && <StatusBadge status={result.legal_status} />}
      </div>

      {aiAnswer && (
        <div className="flex gap-2.5">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-chart-2/10 border border-chart-2/25 mt-0.5">
            <Bot className="size-3.5 text-chart-2" />
          </div>
          <div className="flex-1 min-w-0 text-sm leading-relaxed text-foreground bg-secondary border border-border rounded-xl rounded-tl-none px-3.5 py-2.5">
            <ChatMarkdown content={aiAnswer} />
          </div>
        </div>
      )}

      {result.allocation_plan && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-3">
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider font-mono">
              Alokasi Portofolio
            </p>
            <AllocationChart weights={result.allocation_plan.weights} compact={compact} />
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

      {!isRejected && result.allocation_plan && result.user_approval === null && (
        <>
          <Separator className="bg-border" />
          <button
            onClick={onApprove}
            className="w-full py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition-all duration-200"
          >
            Tinjau &amp; Setujui
          </button>
        </>
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
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [lastQuery, setLastQuery] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

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
  }, [workspaceId]);

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
  }, [workspaceId, result]);

  const selectedData = watchlist.find((t) => t.ticker === selectedTicker) ?? null;

  async function handleRun() {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    if (!message.trim()) { toast.error("Masukkan perintah."); return; }
    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) { router.push("/login"); return; }

    const query = message.trim();
    setLoading(true);
    setResult(null);
    setLastQuery(query);
    setMessage("");
    try {
      const res = await api.runAgent(
        { message: query, workspace_id: workspaceId },
        session.access_token,
      );
      setResult(res);
      const ls = res.legal_status ?? "";
      if (["rejected", "rejected_after_max_revisions"].includes(ls)) {
        toast.error(`Ditolak secara legal: ${ls}`);
      } else if (!res.allocation_plan) {
        // Q&A / clarification run — nothing to approve, just an answer.
        toast.success("Jawaban siap.");
      } else if (res.user_approval === null) {
        toast.info("Menunggu approval Anda — periksa halaman Approvals atau gunakan tombol Tinjau & Setujui.");
      } else {
        toast.success("Analisis selesai — silakan tinjau alokasi.");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Gagal menghubungi agen.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!result) return;
    router.push(`/approvals/${result.audit_id}`);
  }

  const isRejected = ["rejected", "rejected_after_max_revisions"].includes(
    result?.legal_status ?? ""
  );

  const aiAnswer = result
    ? [...result.messages].reverse().find((m) => m.type === "AIMessage")?.content ?? null
    : null;

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
            {result && !mobileOpen && (
              <span className="absolute -top-0.5 -right-0.5 size-3.5 rounded-full bg-chart-2 border-2 border-background animate-pulse" />
            )}
          </button>

          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetContent side="bottom" className="h-[85svh] rounded-t-2xl p-0 gap-0 bg-background">
              <SheetHeader className="border-b border-border px-5 py-4 pr-12">
                <div className="flex items-center gap-3">
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
              </SheetHeader>

              <div className="flex-1 overflow-y-auto px-5 py-4">
                {result ? (
                  <div className="animate-fade-in">
                    <AiResultView
                      result={result}
                      aiAnswer={aiAnswer}
                      userQuery={lastQuery}
                      isRejected={isRejected}
                      onApprove={handleApprove}
                      compact
                    />
                  </div>
                ) : (
                  <AiIdleState loading={loading} />
                )}
              </div>

              <div className="border-t border-border p-4 space-y-3">
                {!result && <AiSuggestions onPick={setMessage} />}
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
          <div className="flex items-center gap-3">
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
        </SidebarHeader>

        <SidebarContent className="px-4 py-4">
          {result ? (
            <div className="animate-fade-in">
              <AiResultView
                result={result}
                aiAnswer={aiAnswer}
                userQuery={lastQuery}
                isRejected={isRejected}
                onApprove={handleApprove}
                compact
              />
            </div>
          ) : (
            <AiIdleState loading={loading} />
          )}
        </SidebarContent>

        <SidebarFooter className="border-t border-sidebar-border p-4 gap-3">
          {!result && <AiSuggestions onPick={setMessage} />}
          <AiComposer message={message} setMessage={setMessage} loading={loading} onRun={handleRun} />
        </SidebarFooter>
      </Sidebar>
    </SidebarProvider>
  );
}
