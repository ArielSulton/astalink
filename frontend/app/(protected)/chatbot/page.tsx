"use client";
import { useEffect, useRef, useState } from "react";
import { Bot, Send } from "lucide-react";
import { api } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

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
        { message: text, thread_id: threadId },
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
    <div className="flex flex-col" style={{ height: "calc(100vh - 0px)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e2028] shrink-0">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-[#0052ff]" />
          <span className="text-white font-medium text-sm">Astalink AI</span>
        </div>
        <button
          onClick={clearThread}
          className="text-xs text-[#5b616e] hover:text-[#a8acb3] transition-colors"
        >
          Percakapan baru
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <Bot className="h-14 w-14 text-[#2a2d36]" />
            <p className="text-[#5b616e] text-sm max-w-xs">
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
              className={`max-w-[78%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-[#0052ff] text-white rounded-br-sm"
                  : "bg-[#16181c] text-[#dee1e6] border border-[#2a2d36] rounded-bl-sm"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#16181c] border border-[#2a2d36] rounded-2xl rounded-bl-sm px-4 py-3.5">
              <div className="flex gap-1.5 items-center">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 rounded-full bg-[#a8acb3] animate-bounce"
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
      <div className="px-6 py-4 border-t border-[#1e2028] shrink-0">
        <div className="flex gap-2 items-end">
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
            className="flex-1 resize-none bg-[#16181c] border border-[#2a2d36] rounded-xl px-4 py-3 text-sm text-white placeholder:text-[#5b616e] focus:outline-none focus:border-[#0052ff] transition-colors"
            style={{ maxHeight: "128px" }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="shrink-0 h-10 w-10 rounded-xl bg-[#0052ff] text-white flex items-center justify-center hover:bg-[#0047db] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
