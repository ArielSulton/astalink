-- 0009_whatsapp.sql

create table if not exists public.whatsapp_bindings (
    user_id uuid primary key references auth.users (id) on delete cascade,
    phone_e164 text not null unique,
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    bound_at timestamptz not null default now()
);
create index if not exists wa_bindings_phone_idx on public.whatsapp_bindings (phone_e164);

create table if not exists public.whatsapp_messages_seen (
    message_id text primary key,
    received_at timestamptz not null default now()
);

create table if not exists public.whatsapp_pending_codes (
    code text primary key,
    phone_e164 text not null,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    consumed_at timestamptz
);

alter table public.whatsapp_bindings enable row level security;
create policy wa_bindings_select_own on public.whatsapp_bindings
    for select using (user_id = auth.uid());
create policy wa_bindings_insert_own on public.whatsapp_bindings
    for insert with check (user_id = auth.uid());
create policy wa_bindings_delete_own on public.whatsapp_bindings
    for delete using (user_id = auth.uid());

-- messages_seen + pending_codes are service-role only (no client access)
alter table public.whatsapp_messages_seen enable row level security;
alter table public.whatsapp_pending_codes enable row level security;
