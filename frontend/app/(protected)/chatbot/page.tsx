"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bot, CheckCircle2, MessageSquare, MessageSquarePlus, Send, Trash2, PlusCircle, Wallet } from "lucide-react";
import { toast } from "sonner";
import { api, type Layer0Result } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { ChatMarkdown } from "@/components/chat-markdown";
import { AllocationBar } from "@/components/allocation/allocation-bar";
import { BusinessPanel, VetoPanel } from "@/components/allocation/business-panel";
import { AllocationBuyModal } from "@/components/allocation-buy-modal";
import { useWorkspace } from "@/components/workspace-context";
import {
  allocatedReplyIds,
  appendMessage,
  compositionRespondedIds,
  createConversation,
  deleteConversation,
  getMessages,
  listConversations,
  titleFrom,
  updateConversation,
  type ChatConversation,
} from "@/lib/chat-history";

function idr(n: number | null | undefined): string {
  if (n == null) return "—";
  return "Rp " + n.toLocaleString("id-ID", { maximumFractionDigits: 0 });
}

function extractTickers(text: string): string[] {
  const matches = text.match(/\b[A-Z]{4}\b/g) || [];
  const validCommon = new Set([
    "BBCA", "TLKM", "ASII", "BMRI", "BBNI", "UNVR", "ICBP", "INDF", "GOTO", "AMRT",
    "CPIN", "KLBF", "MDKA", "PGAS", "PTBA", "SMGR", "TPIA", "BREN", "CUAN", "ADRO"
  ]);
  const found = Array.from(new Set(matches)).filter(t => validCommon.has(t));
  return found.length > 0 ? found : ["BBCA"];
}

// Whether THIS reply itself carries a real optimizer recommendation —
// checked on the assistant's own message, not the preceding user request's
// wording. A regex on the request text ("alokasikan dana") broke as soon as
// the request came via the composition-gate "Setuju, lanjutkan analisis
// saham" reply instead of a literal alokasikan-dana phrasing, silently
// hiding the CTA on every allocate_capital flow.
function hasAllocationPlan(text: string): boolean {
  return /Rekomendasi Bobot Saham/i.test(text);
}

function extractAmount(text: string): number | null {
  const jutaMatch = text.match(/(\d+(?:[.,]\d+)?)\s*(?:juta|jt)\b/i);
  if (jutaMatch) return Math.round(parseFloat(jutaMatch[1].replace(",", ".")) * 1_000_000);
  const milyarMatch = text.match(/(\d+(?:[.,]\d+)?)\s*(?:miliar|milyar)\b/i);
  if (milyarMatch) return Math.round(parseFloat(milyarMatch[1].replace(",", ".")) * 1_000_000_000);
  const rawMatch = text.match(/\b(\d{1,3}(?:\.\d{3})+|\d{6,})\b/);
  if (rawMatch) return parseInt(rawMatch[1].replace(/\./g, ""), 10);
  return null;
}

// Fallback for when the preceding user message has no extractable amount
// (e.g. it's just "Setuju, lanjutkan analisis saham") — the report itself
// always states the analyzed amount when a plan exists.
function extractAnalyzedAmount(text: string): number | null {
  const m = text.match(/Dana yang dianalisis:\s*\**Rp\s*([\d.,]+)/i);
  if (!m) return null;
  return parseInt(m[1].replace(/[.,]/g, ""), 10);
}

interface Message {
  id?: string | null;
  role: "user" | "assistant";
  content: string;
  auditId?: string | null;
  requiresApproval?: boolean;
  // Paused at the composition gate (allocate_capital only) — awaiting a
  // Setuju/Tidak reply before Layer 1 stock analysis + optimizer run.
  awaitingCompositionApproval?: boolean;
  // Layer 0's cash/stocks/business split — renders the same visual
  // AllocationBar the dashboard shows, instead of leaving it as plain text.
  layer0Result?: Layer0Result | null;
}

export default function ChatbotPage() {
  const { workspaceId } = useWorkspace();
  const [rooms, setRooms] = useState<ChatConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [buyModalOpen, setBuyModalOpen] = useState(false);
  const [buyTickers, setBuyTickers] = useState<string[]>(["BBCA"]);
  const [buyAmount, setBuyAmount] = useState<number | null>(null);
  // Which reply the open modal belongs to, and the replies already executed —
  // an executed recommendation must not keep offering its allocate button.
  const [buyForMessageId, setBuyForMessageId] = useState<string | null>(null);
  const [allocatedIds, setAllocatedIds] = useState<Set<string>>(new Set());
  // Ids of paused replies whose composition gate has already been answered —
  // without this, Setuju/Tidak would reappear forever after a reload.
  const [respondedCompositionIds, setRespondedCompositionIds] = useState<Set<string>>(new Set());
  const [respondingComposition, setRespondingComposition] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadRoom = useCallback(async (conv: ChatConversation) => {
    setActiveId(conv.id);
    setThreadId(conv.thread_id ?? undefined);
    const rows = await getMessages(conv.id);
    setMessages(
      rows.map((r) => ({
        id: r.id,
        role: r.role,
        content: r.content,
        auditId: r.audit_id,
        requiresApproval: r.requires_approval,
        awaitingCompositionApproval: !!r.metadata?.awaiting_composition_approval,
        layer0Result: (r.metadata?.layer0_result as Layer0Result | undefined) ?? null,
      })),
    );
    setAllocatedIds(allocatedReplyIds(rows));
    setRespondedCompositionIds(compositionRespondedIds(rows));
  }, []);

  // Load this user's chatbot rooms for the workspace; open the most recent.
  useEffect(() => {
    if (!workspaceId) {
      setRooms([]);
      setActiveId(null);
      setMessages([]);
      setAllocatedIds(new Set());
      setRespondedCompositionIds(new Set());
      setThreadId(undefined);
      return;
    }
    let cancelled = false;
    (async () => {
      const list = await listConversations(workspaceId, "chatbot");
      if (cancelled) return;
      setRooms(list);
      if (list.length) await loadRoom(list[0]);
      else {
        setActiveId(null);
        setMessages([]);
        setAllocatedIds(new Set());
        setRespondedCompositionIds(new Set());
        setThreadId(undefined);
      }
    })();
    return () => { cancelled = true; };
  }, [workspaceId, loadRoom]);

  async function newRoom() {
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }
    const conv = await createConversation(workspaceId, "chatbot");
    if (!conv) return;
    setRooms((prev) => [conv, ...prev]);
    setActiveId(conv.id);
    setThreadId(undefined);
    setMessages([]);
    setAllocatedIds(new Set());
    setRespondedCompositionIds(new Set());
  }

  async function removeRoom(id: string) {
    await deleteConversation(id);
    const next = rooms.filter((r) => r.id !== id);
    setRooms(next);
    if (id === activeId) {
      if (next.length) await loadRoom(next[0]);
      else {
        setActiveId(null);
        setMessages([]);
        setAllocatedIds(new Set());
        setRespondedCompositionIds(new Set());
        setThreadId(undefined);
      }
    }
  }

  const openAllocationModal = (
    content: string,
    requestText: string | undefined,
    messageId: string | null | undefined,
  ) => {
    const tickers = extractTickers(content);
    setBuyTickers(tickers);
    const amount = (requestText ? extractAmount(requestText) : null) ?? extractAnalyzedAmount(content);
    setBuyAmount(amount);
    setBuyForMessageId(messageId ?? null);
    setBuyModalOpen(true);
  };

  const handleAllocationSuccess = async (ticker: string, amount: number, cashRemaining: number) => {
    setBuyModalOpen(false);
    const target = buyForMessageId;
    if (target) setAllocatedIds((prev) => new Set(prev).add(target));
    const confirmMsg = `✓ **Alokasi Berhasil!** Mengalokasikan **${idr(amount)}** ke saham **${ticker}**.\n- Saldo kas tersisa: **${idr(cashRemaining)}**\n- Transaksi telah dicatat di tabel **Riwayat Transaksi** dan posisi diperbarui di halaman **Portofolio**.`;
    // metadata.allocated_for is what marks the original reply as executed on reload.
    const id = activeId
      ? await appendMessage(activeId, {
          role: "assistant",
          content: confirmMsg,
          metadata: target ? { allocated_for: target } : {},
        })
      : null;
    setMessages((prev) => [...prev, { id, role: "assistant", content: confirmMsg }]);
  };

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }

    const sb = createClient();
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;

    let cid = activeId;
    const firstTurn = messages.length === 0;
    if (!cid) {
      const conv = await createConversation(workspaceId, "chatbot", titleFrom(text));
      if (!conv) return;
      cid = conv.id;
      setRooms((prev) => [conv, ...prev]);
      setActiveId(conv.id);
    }

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    if (cid) await appendMessage(cid, { role: "user", content: text });

    try {
      const res = await api.chat(
        { message: text, workspace_id: workspaceId, thread_id: threadId },
        session.access_token,
      );
      setThreadId(res.thread_id);
      // Persisted first so the reply carries its row id — the allocate CTA
      // needs it to record that this specific reply was executed.
      const msgId = cid
        ? await appendMessage(cid, {
            role: "assistant",
            content: res.message,
            auditId: res.audit_id,
            requiresApproval: res.requires_approval,
            metadata: {
              ...(res.awaiting_composition_approval ? { awaiting_composition_approval: true } : {}),
              ...(res.layer0_result ? { layer0_result: res.layer0_result } : {}),
            },
          })
        : null;
      setMessages((prev) => [
        ...prev,
        {
          id: msgId,
          role: "assistant",
          content: res.message,
          auditId: res.audit_id,
          requiresApproval: res.requires_approval,
          awaitingCompositionApproval: res.awaiting_composition_approval,
          layer0Result: res.layer0_result,
        },
      ]);
      if (cid) {
        const rid = cid;
        await updateConversation(rid, {
          thread_id: res.thread_id,
          ...(firstTurn ? { title: titleFrom(text) } : {}),
        });
        setRooms((prev) =>
          [...prev]
            .map((r) =>
              r.id === rid
                ? {
                    ...r,
                    thread_id: res.thread_id,
                    title: firstTurn ? titleFrom(text) : r.title,
                    updated_at: new Date().toISOString(),
                  }
                : r,
            )
            .sort((a, b) => b.updated_at.localeCompare(a.updated_at)),
        );
      }
    } catch {
      const fail = "Maaf, terjadi kesalahan. Coba lagi.";
      setMessages((prev) => [...prev, { role: "assistant", content: fail }]);
      if (cid) await appendMessage(cid, { role: "assistant", content: fail });
    } finally {
      setLoading(false);
    }
  }

  // Setuju/Tidak on a paused composition-gate reply — sends "ya"/"tidak" as
  // plain chat text, since /chat already transparently resumes the graph on
  // that text via find_pending_composition_audit/detect_composition_reply.
  // No dedicated resume endpoint needed here (unlike the dashboard, which
  // uses api.resumeAgent against /agent/resume).
  async function respondToComposition(messageId: string | null | undefined, approval: "approved" | "rejected") {
    if (!activeId || respondingComposition) return;
    setRespondingComposition(true);
    const userText = approval === "approved" ? "Setuju, lanjutkan analisis saham" : "Tidak, batalkan";
    const wireText = approval === "approved" ? "ya" : "tidak";
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    await appendMessage(activeId, {
      role: "user",
      content: userText,
      metadata: messageId ? { composition_for: messageId } : {},
    });
    if (messageId) setRespondedCompositionIds((prev) => new Set(prev).add(messageId));
    try {
      const sb = createClient();
      const { data: { session } } = await sb.auth.getSession();
      if (!session || !workspaceId) return;
      const res = await api.chat(
        { message: wireText, workspace_id: workspaceId, thread_id: threadId },
        session.access_token,
      );
      setThreadId(res.thread_id);
      const msgId = activeId
        ? await appendMessage(activeId, {
            role: "assistant",
            content: res.message,
            auditId: res.audit_id,
            requiresApproval: res.requires_approval,
            metadata: {
              ...(res.awaiting_composition_approval ? { awaiting_composition_approval: true } : {}),
              ...(res.layer0_result ? { layer0_result: res.layer0_result } : {}),
            },
          })
        : null;
      setMessages((prev) => [
        ...prev,
        {
          id: msgId,
          role: "assistant",
          content: res.message,
          auditId: res.audit_id,
          requiresApproval: res.requires_approval,
          awaitingCompositionApproval: res.awaiting_composition_approval,
          layer0Result: res.layer0_result,
        },
      ]);
    } catch {
      const fail = "Maaf, terjadi kesalahan. Coba lagi.";
      setMessages((prev) => [...prev, { role: "assistant", content: fail }]);
      if (activeId) await appendMessage(activeId, { role: "assistant", content: fail });
    } finally {
      setRespondingComposition(false);
    }
  }

  return (
    <div className="flex h-full bg-background">
      {/* Active room */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-b border-border bg-card/40 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-chart-2/10 flex items-center justify-center border border-chart-2/20 shrink-0">
              <Bot className="h-4 w-4 text-chart-2" />
            </div>
            <div className="min-w-0">
              <span className="text-foreground font-bold text-sm block truncate">Astalink AI</span>
              <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" /> Online
              </span>
            </div>
          </div>

          {/* Mobile room switcher */}
          <div className="flex md:hidden items-center gap-2">
            <select
              value={activeId ?? ""}
              onChange={(e) => {
                const r = rooms.find((x) => x.id === e.target.value);
                if (r) loadRoom(r);
              }}
              className="max-w-[130px] text-xs bg-secondary border border-border rounded-lg px-2 py-1.5 text-foreground focus:outline-none"
            >
              <option value="" disabled>Percakapan…</option>
              {rooms.map((r) => (
                <option key={r.id} value={r.id}>{r.title}</option>
              ))}
            </select>
            <button
              onClick={newRoom}
              aria-label="Percakapan baru"
              className="shrink-0 flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all"
            >
              <MessageSquarePlus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-6 space-y-5">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <div className="w-14 h-14 rounded-2xl bg-card border border-border flex items-center justify-center mb-2">
                <Bot className="h-7 w-7 text-chart-2" />
              </div>
              <h3 className="text-foreground font-bold text-sm tracking-tight">Tanya Astalink AI</h3>
              <p className="text-muted-foreground text-xs max-w-xs leading-relaxed">
                Tanya apa saja tentang rekomendasi investasi, alokasi modal, regulasi OJK/UUPM, atau analisis saham.
              </p>
            </div>
          )}

          {messages.map((m, i) => {
            const precedingUser = i > 0 ? messages[i - 1] : null;
            const isAllocated = !!m.id && allocatedIds.has(m.id);
            const isAllocationReply = m.role === "assistant" && hasAllocationPlan(m.content);
            const isCompositionPending =
              m.role === "assistant" &&
              m.awaitingCompositionApproval &&
              !(m.id && respondedCompositionIds.has(m.id));
            // The message 2 back is the paused reply this one resumes from
            // (index i-1 is the synthetic "Setuju/Tidak" user bubble) — its
            // Kas/Saham/Bisnis panel already showed the same layer0Result,
            // so repeating it here would just be a duplicate.
            const twoBack = i >= 2 ? messages[i - 2] : null;
            const isCompositionContinuation =
              m.role === "assistant" &&
              twoBack?.role === "assistant" &&
              !!twoBack.awaitingCompositionApproval;

            return (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "user" ? (
                  <div className="max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap bg-primary text-primary-foreground rounded-tr-none">
                    {m.content}
                  </div>
                ) : (
                  <div className="max-w-[85%] flex flex-col items-start gap-2">
                    <div className="w-full px-4 py-3 rounded-2xl text-sm leading-relaxed bg-glass text-foreground border border-border rounded-tl-none">
                      <ChatMarkdown content={m.content} />
                    </div>
                    {/* Visual Kas/Saham/Bisnis split — same AllocationBar the
                       dashboard shows, so this isn't left as plain text. */}
                    {m.layer0Result?.allocation && !isCompositionContinuation && (
                      <div className="w-full rounded-2xl border border-border bg-glass p-4 space-y-3">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider font-mono">
                            Kas vs Saham vs Bisnis
                          </p>
                          <span className="px-2 py-0.5 rounded border text-[10px] font-bold font-mono text-muted-foreground border-border">
                            CONFIDENCE: {m.layer0Result.confidence_label} ({m.layer0Result.confidence}/100)
                          </span>
                        </div>
                        <AllocationBar allocation={m.layer0Result.allocation} />
                        {m.layer0Result.business_id && (
                          <p className="text-xs text-muted-foreground">
                            Bisnis yang dievaluasi: <strong className="text-foreground">{m.layer0Result.business_name}</strong>
                            {" · "}skor bisnis{" "}
                            <strong className="text-foreground">{m.layer0Result.business_score ?? "UNKNOWN"}</strong>
                            {" vs "}skor saham{" "}
                            <strong className="text-foreground">{m.layer0Result.stock_score ?? "—"}</strong>
                          </p>
                        )}
                        {m.layer0Result.business_id ? (
                          <BusinessPanel layer0={m.layer0Result} />
                        ) : (
                          <VetoPanel flags={m.layer0Result.veto_flags} />
                        )}
                      </div>
                    )}
                    {/* Report + approval action — only on replies to an actual
                       "alokasikan dana" request; other intents (explain, risk
                       review, etc.) have nothing here to approve. */}
                    {isAllocationReply && isAllocated && (
                      <div className="w-full flex items-center gap-2 border-t border-border/60 pt-3">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                        <span className="text-[11px] text-emerald-400">
                          Sudah dieksekusi — dana dialokasikan dari rekomendasi ini.
                        </span>
                        <Link
                          href="/portfolio"
                          className="text-[11px] font-medium text-muted-foreground underline underline-offset-2 hover:text-foreground"
                        >
                          Lihat portofolio
                        </Link>
                      </div>
                    )}

                    {isCompositionPending && (
                      <div className="w-full flex flex-col gap-2 border-t border-border/60 pt-3">
                        <span className="text-[11px] text-muted-foreground leading-relaxed">
                          Setuju dengan komposisi ini? Analisis saham lanjutan baru jalan setelah dikonfirmasi.
                        </span>
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            type="button"
                            disabled={respondingComposition}
                            onClick={() => respondToComposition(m.id, "approved")}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all shadow-md"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            {respondingComposition ? "Memproses…" : "Setuju, Lanjutkan"}
                          </button>
                          <button
                            type="button"
                            disabled={respondingComposition}
                            onClick={() => respondToComposition(m.id, "rejected")}
                            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-xl border border-border bg-secondary text-foreground hover:bg-secondary/80 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
                          >
                            Tidak, Batalkan
                          </button>
                        </div>
                      </div>
                    )}

                    {isAllocationReply && !isAllocated && (
                      <div className="w-full flex flex-col gap-2 border-t border-border/60 pt-3">
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Laporan pertimbangan siap — setujui untuk eksekusi
                        </span>
                        <div className="flex items-center gap-2 flex-wrap">
                          <button
                            onClick={() => openAllocationModal(m.content, precedingUser?.content, m.id)}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition-all shadow-md"
                          >
                            <PlusCircle className="w-3.5 h-3.5" />
                            Setujui &amp; Alokasikan Dana
                          </button>
                          <Link
                            href="/portfolio"
                            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-xl border border-border bg-secondary text-foreground hover:bg-secondary/80 transition-all"
                          >
                            <Wallet className="w-3.5 h-3.5" />
                            Lihat Portofolio
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-glass border border-border rounded-2xl rounded-tl-none px-5 py-4">
                <div className="flex gap-1.5 items-center">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-border bg-card/40 shrink-0">
          <div className="flex gap-3 items-end max-w-4xl mx-auto">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ketik pesan… (misal: rekomendasi alokasi 20 juta ke BBCA dan TLKM)"
              rows={1}
              className="flex-1 resize-none bg-secondary border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-chart-2 focus:ring-1 focus:ring-chart-2/20 transition-all duration-200"
              style={{ maxHeight: "128px" }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              className="shrink-0 h-10 w-10 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed disabled:shadow-none transition-all duration-200"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Rooms sidebar (desktop) */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-l border-border bg-card/30">
        <div className="p-3 border-b border-border">
          <button
            onClick={newRoom}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-all"
          >
            <MessageSquarePlus className="w-4 h-4" /> Percakapan baru
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
          {rooms.length === 0 && (
            <p className="text-[11px] text-muted-foreground/70 px-3 py-4 text-center">
              Belum ada percakapan.
            </p>
          )}
          {rooms.map((r) => (
            <div
              key={r.id}
              onClick={() => loadRoom(r)}
              className={`group flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer transition-colors ${
                r.id === activeId ? "bg-secondary" : "hover:bg-secondary/50"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate text-xs text-foreground">{r.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); removeRoom(r.id); }}
                aria-label="Hapus percakapan"
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-rose-400 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {buyModalOpen && workspaceId && (
        <AllocationBuyModal
          workspaceId={workspaceId}
          suggestedTickers={buyTickers}
          suggestedAmount={buyAmount}
          onClose={() => setBuyModalOpen(false)}
          onSuccess={handleAllocationSuccess}
        />
      )}
    </div>
  );
}
