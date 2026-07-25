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

/** Inserts a message and returns its id, which callers need to link a later
 *  "this recommendation was executed" marker back to the reply it belongs to. */
export async function appendMessage(
  conversationId: string,
  msg: {
    role: "user" | "assistant";
    content: string;
    auditId?: string | null;
    requiresApproval?: boolean;
    metadata?: Record<string, unknown>;
  },
): Promise<string | null> {
  const sb = createClient();
  const { data } = await sb
    .from("chat_messages")
    .insert({
      conversation_id: conversationId,
      role: msg.role,
      content: msg.content,
      audit_id: msg.auditId ?? null,
      requires_approval: msg.requiresApproval ?? false,
      metadata: msg.metadata ?? {},
    })
    .select("id")
    .single();
  await sb
    .from("chat_conversations")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", conversationId);
  return (data as { id: string } | null)?.id ?? null;
}

/**
 * Ids of replies whose allocation the user already executed. Derived from the
 * confirmation messages themselves (`metadata.allocated_for`) rather than a
 * flag on the original reply: chat_messages has insert/select/delete RLS
 * policies but no update policy, so an append is the only write that survives.
 */
export function allocatedReplyIds(rows: ChatMessageRow[]): Set<string> {
  const ids = new Set<string>();
  for (const r of rows) {
    const target = r.metadata?.allocated_for;
    if (typeof target === "string") ids.add(target);
  }
  return ids;
}

// Same append-only marker pattern as allocatedReplyIds — a Setuju/Tidak
// answer on the composition gate appends a new row pointing back at the
// paused reply, since chat_messages has no update policy under RLS.
export function compositionRespondedIds(rows: ChatMessageRow[]): Set<string> {
  const ids = new Set<string>();
  for (const r of rows) {
    const target = r.metadata?.composition_for;
    if (typeof target === "string") ids.add(target);
  }
  return ids;
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
