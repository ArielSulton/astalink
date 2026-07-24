-- 0015_chat_history.sql
-- Persistent per-user chat history for the dashboard AI assistant and the
-- chatbot page. A conversation groups messages; chatbot conversations are
-- multi-room (the user switches between them), while the dashboard uses a
-- single conversation per (user, workspace) that its "Clear" button deletes.
--
-- thread_id is the LangGraph thread the chatbot continues a room under (null
-- for the dashboard, whose runAgent calls are each independent). RLS scopes
-- every row to its owner (auth.uid()), so history follows the account across
-- devices. Read/written directly by the frontend Supabase client — no backend
-- endpoint — the same pattern the transactions/assets pages already use.

create table if not exists public.chat_conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users (id) on delete cascade,
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    surface text not null check (surface in ('dashboard', 'chatbot')),
    title text not null default 'Percakapan baru',
    thread_id text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists chat_conversations_scope_idx
    on public.chat_conversations (user_id, workspace_id, surface, updated_at desc);

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.chat_conversations (id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null default '',
    audit_id text,
    requires_approval boolean not null default false,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists chat_messages_conversation_idx
    on public.chat_messages (conversation_id, created_at);

-- RLS: a user sees/writes only their own conversations; messages are gated
-- through conversation ownership.
alter table public.chat_conversations enable row level security;
create policy chat_conversations_select_own on public.chat_conversations
    for select using (user_id = auth.uid());
create policy chat_conversations_insert_own on public.chat_conversations
    for insert with check (user_id = auth.uid());
create policy chat_conversations_update_own on public.chat_conversations
    for update using (user_id = auth.uid());
create policy chat_conversations_delete_own on public.chat_conversations
    for delete using (user_id = auth.uid());

alter table public.chat_messages enable row level security;
create policy chat_messages_select_own on public.chat_messages
    for select using (
        conversation_id in (
            select id from public.chat_conversations where user_id = auth.uid()
        )
    );
create policy chat_messages_insert_own on public.chat_messages
    for insert with check (
        conversation_id in (
            select id from public.chat_conversations where user_id = auth.uid()
        )
    );
create policy chat_messages_delete_own on public.chat_messages
    for delete using (
        conversation_id in (
            select id from public.chat_conversations where user_id = auth.uid()
        )
    );
