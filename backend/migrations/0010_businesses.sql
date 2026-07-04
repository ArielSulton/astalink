-- 0010_businesses.sql
-- User-owned businesses (for N2b Business Evaluator / DCF valuation) and
-- their per-period financial records (aset/omset/profit). Replaces the dead
-- financials_csv/CSVConnector mechanism with real, queryable data scoped by
-- workspace like every other domain table in this app.

create table if not exists public.businesses (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    name text not null,
    industry text,
    description text,
    created_at timestamptz not null default now()
);

create index if not exists businesses_workspace_idx
    on public.businesses (workspace_id, created_at desc);

create table if not exists public.business_financial_records (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null references public.businesses (id) on delete cascade,
    period_year int not null,
    aset numeric not null,
    omset numeric not null,
    profit numeric not null,
    created_at timestamptz not null default now(),
    unique (business_id, period_year)
);

create index if not exists business_financial_records_business_idx
    on public.business_financial_records (business_id, period_year desc);

-- RLS: same workspace-ownership pattern as audit_log/allocation_plans/transactions
-- (0007_rls_policies.sql). The backend's service-role admin client bypasses
-- this — app/api/v1/business.py enforces ownership explicitly in code.
alter table public.businesses enable row level security;
create policy businesses_select_own on public.businesses
    for select using (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
create policy businesses_insert_own on public.businesses
    for insert with check (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
create policy businesses_update_own on public.businesses
    for update using (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );
create policy businesses_delete_own on public.businesses
    for delete using (
        workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
    );

alter table public.business_financial_records enable row level security;
create policy business_financial_records_select_own on public.business_financial_records
    for select using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_financial_records_insert_own on public.business_financial_records
    for insert with check (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
create policy business_financial_records_update_own on public.business_financial_records
    for update using (
        business_id in (
            select id from public.businesses
            where workspace_id in (select id from public.workspaces where owner_user_id = auth.uid())
        )
    );
