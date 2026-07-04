"use client";
import { useEffect, useRef, useState } from "react";
import { Bot, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { useWorkspace } from "@/components/workspace-context";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const THREAD_KEY = "astalink_chat_thread_id";

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const { workspaceId } = useWorkspace();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem(THREAD_KEY);
    if (saved) setThreadId(saved);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;
    if (!workspaceId) { toast.error("Pilih workspace terlebih dahulu."); return; }

    const sb = createClient();
    const {
      data: { session },
    } = await sb.auth.getSession();
    if (!session) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const res = await api.chat(
        { message: text, workspace_id: workspaceId, thread_id: threadId },
        session.access_token,
      );
      setThreadId(res.thread_id);
      localStorage.setItem(THREAD_KEY, res.thread_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Maaf, terjadi kesalahan. Coba lagi." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function clearThread() {
    localStorage.removeItem(THREAD_KEY);
    setThreadId(undefined);
    setMessages([]);
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-card/40 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-chart-2/10 flex items-center justify-center border border-chart-2/20">
            <Bot className="h-4 w-4 text-chart-2" />
          </div>
          <div>
            <span className="text-foreground font-bold text-sm block">Astalink AI</span>
            <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" /> Online
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearThread}
            className="text-xs text-muted-foreground hover:text-foreground transition-all flex items-center gap-1.5 font-medium py-1 px-2.5 rounded-lg hover:bg-secondary"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Percakapan baru
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-card border border-border flex items-center justify-center mb-2">
              <Bot className="h-7 w-7 text-chart-2" />
            </div>
            <h3 className="text-foreground font-bold text-sm tracking-tight">Tanya Astalink AI</h3>
            <p className="text-muted-foreground text-xs max-w-xs leading-relaxed">
              Tanya apa saja tentang investasi, regulasi OJK/UUPM, atau kondisi pasar saham IDX.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-primary text-primary-foreground rounded-tr-none"
                  : "bg-glass text-foreground border border-border rounded-tl-none"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

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
            placeholder="Ketik pesan… (Enter untuk kirim, Shift+Enter untuk baris baru)"
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
  );
}
