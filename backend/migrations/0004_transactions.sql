-- 0004_transactions.sql
-- Records each broker order placed by N7. The unique constraint on
-- (audit_id, ticker, side) gives N7 idempotency: re-running the node for the
-- same plan does not double-execute.

create table if not exists public.transactions (
    id uuid primary key default gen_random_uuid(),
    allocation_plan_id uuid not null references public.allocation_plans (id) on delete cascade,
    audit_id uuid not null references public.audit_log (audit_id) on delete cascade,
    ticker text not null,
    side text not null,            -- 'buy' | 'sell'
    quantity numeric not null,
    broker_ref text,               -- broker's order id
    status text not null,          -- 'pending' | 'filled' | 'failed'
    executed_at timestamptz,
    payload jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (audit_id, ticker, side)
);

create index if not exists transactions_audit_idx
    on public.transactions (audit_id);
create index if not exists transactions_plan_idx
    on public.transactions (allocation_plan_id);
