-- 0003_allocation_plans.sql
-- Each pipeline run produces zero or more allocation plans. A plan can be
-- revised by the optimizer (N5) up to a configured cap; revision_count tracks
-- this so the graph can terminate after max revisions.

create table if not exists public.allocation_plans (
    id uuid primary key default gen_random_uuid(),
    audit_id uuid not null references public.audit_log (audit_id) on delete cascade,
    plan_json jsonb not null,
    legal_status text,
        -- approved | partial | rejected | rejected_after_max_revisions | null
    legal_citations jsonb not null default '[]'::jsonb,
    revision_count int not null default 0,
    created_at timestamptz not null default now()
);

create index if not exists allocation_plans_audit_idx
    on public.allocation_plans (audit_id, created_at desc);
