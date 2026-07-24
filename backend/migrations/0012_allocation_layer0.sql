-- 0012_allocation_layer0.sql
-- Layer 0 capital-allocation inputs:
--   * business_intake_profiles — B0 intake schema per business. Stored as a
--     single jsonb document matching app/agents/allocation/schemas.py
--     BusinessProfile (every leaf field is {value, evidence}); the evidence
--     tag (verified/claimed/estimated/unknown) is part of the data model,
--     so a typed-column layout would double the column count for no gain.
--   * investor_profiles — L0-2 personal-constraint answers per workspace
--     (emergency fund, borrowed capital, horizon, net worth, debt, hours).

create table if not exists public.business_intake_profiles (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references public.businesses (id) on delete cascade,
    profile jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now(),
    unique (business_id)
);

create table if not exists public.investor_profiles (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    profile jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now(),
    unique (workspace_id)
);

-- RLS: same workspace-ownership pattern as businesses (0010). The backend's
-- service-role admin client bypasses this — the API layer enforces ownership
-- explicitly in code.
alter table public.business_intake_profiles enable row level security;
create policy business_intake_profiles_select_own on public.business_intake_profiles
    for select using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_intake_profiles_insert_own on public.business_intake_profiles
    for insert with check (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_intake_profiles_update_own on public.business_intake_profiles
    for update using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );

alter table public.investor_profiles enable row level security;
create policy investor_profiles_select_own on public.investor_profiles
    for select using (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
create policy investor_profiles_insert_own on public.investor_profiles
    for insert with check (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
create policy investor_profiles_update_own on public.investor_profiles
    for update using (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
