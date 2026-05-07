-- 0002_audit_log.sql
-- The audit_log is the source of truth for every pipeline run. Every node
-- (N1..N7) writes to it, keyed by audit_id. This is what makes "audit trail
-- end-to-end" enforceable.

create table if not exists public.audit_log (
    audit_id uuid primary key,
    workspace_id uuid not null references public.workspaces (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    intent text,
    status text not null default 'in_progress',
        -- in_progress | awaiting_approval | approved | rejected | executed | failed
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    payload jsonb not null default '{}'::jsonb
);

create index if not exists audit_log_workspace_idx
    on public.audit_log (workspace_id, created_at desc);
create index if not exists audit_log_user_idx
    on public.audit_log (user_id, created_at desc);
create index if not exists audit_log_status_idx
    on public.audit_log (status);
