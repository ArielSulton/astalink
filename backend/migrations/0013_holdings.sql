-- 0013_holdings.sql
-- Sandbox portfolio holdings + realized P&L support.
--
-- `holdings` is the source of truth for accumulated positions per workspace:
-- execution (N7) upserts a row on every filled BUY (weighted-average cost),
-- and the portfolio sell endpoint decrements it. This is what the /portfolio
-- page and the dashboard summary read.
--
-- The `transactions` table is relaxed so a manual portfolio SELL (which has no
-- allocation plan or audit run behind it) can be recorded in the same ledger:
--   - allocation_plan_id / audit_id become nullable (manual sells have neither)
--   - workspace_id is added so both pipeline buys and manual sells carry their
--     workspace directly (and RLS no longer needs the audit_log join)
--   - price + realized_pnl capture execution price and, on sells, the realized
--     gain/loss (SUM over sells = total realized P&L for a workspace)

create table if not exists public.holdings (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    ticker text not null,
    quantity numeric not null,
    avg_cost numeric not null,
    updated_at timestamptz not null default now(),
    unique (workspace_id, ticker)
);

create index if not exists holdings_workspace_idx
    on public.holdings (workspace_id);

alter table public.holdings enable row level security;
create policy holdings_select_own on public.holdings
    for select using (
        workspace_id in (
            select id from public.workspaces where owner_user_id = auth.uid()
        )
    );

-- transactions: relax NOT NULL + extend for manual sells and P&L.
-- (unique(audit_id, ticker, side) is unaffected: Postgres treats NULL audit_id
--  as distinct, so multiple manual sells of the same ticker never collide.)
alter table public.transactions
    alter column allocation_plan_id drop not null,
    alter column audit_id drop not null,
    add column if not exists workspace_id uuid references public.workspaces (id) on delete cascade,
    add column if not exists price numeric,
    add column if not exists realized_pnl numeric;

-- Backfill workspace_id on existing rows via their audit run.
update public.transactions t
set workspace_id = a.workspace_id
from public.audit_log a
where t.audit_id = a.audit_id and t.workspace_id is null;

create index if not exists transactions_workspace_idx
    on public.transactions (workspace_id);

-- Additional RLS policy: read transactions by direct workspace ownership too,
-- covering manual sells that have no audit_id. Permissive policies are OR'd,
-- so the existing audit_log-join policy still applies to pipeline rows.
create policy transactions_select_by_workspace on public.transactions
    for select using (
        workspace_id in (
            select id from public.workspaces where owner_user_id = auth.uid()
        )
    );
