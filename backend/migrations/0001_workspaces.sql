-- 0001_workspaces.sql
-- A workspace isolates one user's data; users may have multiple workspaces
-- (e.g. one Personal + one Business). RLS policies (0007) gate access by
-- workspace ownership.

create type workspace_type as enum ('personal', 'business');

create table if not exists public.workspaces (
    id uuid primary key default gen_random_uuid(),
    owner_user_id uuid not null references auth.users (id) on delete cascade,
    type workspace_type not null,
    name text not null,
    created_at timestamptz not null default now()
);

create index if not exists workspaces_owner_idx
    on public.workspaces (owner_user_id);
