"use client";
/**
 * Per-user chat history persisted in Supabase (tables from migration 0015),
 * read/written directly via the browser client with RLS enforcing per-account
 * isolation — the same direct-Supabase pattern the transactions/assets pages
 * use. The dashboard keeps one conversation per (user, workspace); the chatbot
 * keeps many (multi-room). Answer generation still goes through the backend
 * (/chat, /agent/run); this module only stores and loads the transcript.
 */
import { createClient } from "@/lib/supabase/client";

export type ChatSurface = "dashboard" | "chatbot";

export interface ChatConversation {
  id: string;
  title: string;
  thread_id: string | null;
  surface: ChatSurface;
  updated_at: string;
}

export interface ChatMessageRow {
  id: string;
  role: "user" | "assistant";
  content: string;
  audit_id: string | null;
  requires_approval: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

const CONV_COLS = "id, title, thread_id, surface, updated_at";
const MSG_COLS = "id, role, content, audit_id, requires_approval, metadata, created_at";

async function currentUserId(): Promise<string | null> {
  const { data } = await createClient().auth.getUser();
  return data.user?.id ?? null;
}

export async function listConversations(
  workspaceId: string,
  surface: ChatSurface,
): Promise<ChatConversation[]> {
  const { data } = await createClient()
    .from("chat_conversations")
    .select(CONV_COLS)
    .eq("workspace_id", workspaceId)
    .eq("surface", surface)
    .order("updated_at", { ascending: false });
  return (data as ChatConversation[] | null) ?? [];
}

export async function getMessages(conversationId: string): Promise<ChatMessageRow[]> {
  const { data } = await createClient()
    .from("chat_messages")
    .select(MSG_COLS)
    .eq("conversation_id", conversationId)
    .order("created_at", { ascending: true });
  return (data as ChatMessageRow[] | null) ?? [];
}

export async function createConversation(
  workspaceId: string,
  surface: ChatSurface,
  title = "Percakapan baru",
): Promise<ChatConversation | null> {
  const userId = await currentUserId();
  if (!userId) return null;
  const { data } = await createClient()
    .from("chat_conversations")
    .insert({ user_id: userId, workspace_id: workspaceId, surface, title })
    .select(CONV_COLS)
    .single();
  return (data as ChatConversation | null) ?? null;
}

/** The dashboard's single conversation for this workspace, created lazily. */
export async function getOrCreateDashboardConversation(
  workspaceId: string,
): Promise<ChatConversation | null> {
  const existing = await listConversations(workspaceId, "dashboard");
  if (existing.length) return existing[0];
  return createConversation(workspaceId, "dashboard", "Asisten AI");
}

export async function appendMessage(
  conversationId: string,
  msg: {
    role: "user" | "assistant";
    content: string;
    auditId?: string | null;
    requiresApproval?: boolean;
    metadata?: Record<string, unknown>;
  },
): Promise<void> {
  const sb = createClient();
  await sb.from("chat_messages").insert({
    conversation_id: conversationId,
    role: msg.role,
    content: msg.content,
    audit_id: msg.auditId ?? null,
    requires_approval: msg.requiresApproval ?? false,
    metadata: msg.metadata ?? {},
  });
  await sb
    .from("chat_conversations")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", conversationId);
}

export async function updateConversation(
  id: string,
  patch: { title?: string; thread_id?: string },
): Promise<void> {
  await createClient()
    .from("chat_conversations")
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq("id", id);
}

export async function deleteConversation(id: string): Promise<void> {
  await createClient().from("chat_conversations").delete().eq("id", id);
}

/** First user line, trimmed to a room title. */
export function titleFrom(text: string): string {
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > 40 ? t.slice(0, 40) + "…" : t || "Percakapan baru";
}
