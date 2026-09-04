-- 0016_business_transactions.sql
-- Individual business transactions captured via WhatsApp (text/voice/photo),
-- extracted by Gemini and confirmed by the user before being rolled up into
-- business_financial_records (0010_businesses.sql). See
-- docs/superpowers/specs/2026-09-04-business-pos-automation-design.md.

create table if not exists public.business_transactions (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references public.businesses (id) on delete cascade,
    occurred_at timestamptz not null default now(),
    type text not null check (type in ('income', 'expense')),
    item_description text,
    amount numeric not null,
    source text not null check (source in ('whatsapp_text', 'whatsapp_voice', 'whatsapp_photo')),
    raw_input text,
    media_ref text,
    confidence numeric not null,
    plausibility_flag boolean not null default false,
    status text not null default 'pending_confirmation'
        check (status in ('pending_confirmation', 'confirmed', 'rejected')),
    wa_message_id text unique,
    confirmed_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists business_transactions_business_idx
    on public.business_transactions (business_id, occurred_at desc);
create index if not exists business_transactions_pending_idx
    on public.business_transactions (business_id, status)
    where status = 'pending_confirmation';

alter table public.business_transactions enable row level security;
create policy business_transactions_select_own on public.business_transactions
    for select using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_transactions_insert_own on public.business_transactions
    for insert with check (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_transactions_update_own on public.business_transactions
    for update using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
