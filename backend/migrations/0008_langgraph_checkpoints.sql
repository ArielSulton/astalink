-- 0008_langgraph_checkpoints.sql
-- LangGraph PostgresSaver schema. In practice, app.core.checkpointer calls
-- saver.setup() at runtime, which idempotently creates/migrates this same
-- schema (tracked via a checkpoint_migrations table) — this file exists so
-- the team can see the shape without spinning up the app, and so a fresh
-- Supabase project has the tables before setup() ever runs. If
-- langgraph-checkpoint-postgres adds columns/indexes in a future version,
-- setup() applies them automatically even if this file drifts.
-- Schema reference:
-- https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/

create table if not exists public.checkpoints (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb,
    metadata jsonb not null default '{}'::jsonb,
    primary key (thread_id, checkpoint_ns, checkpoint_id)
);

create table if not exists public.checkpoint_writes (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    task_id text not null,
    task_path text not null default '',
    idx int not null,
    channel text not null,
    type text,
    blob bytea,
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

create table if not exists public.checkpoint_blobs (
    thread_id text not null,
    checkpoint_ns text not null default '',
    channel text not null,
    version text not null,
    type text not null,
    blob bytea,
    primary key (thread_id, checkpoint_ns, channel, version)
);

-- Service-role only (the backend never exposes raw checkpoint state to users).
alter table public.checkpoints enable row level security;
alter table public.checkpoint_writes enable row level security;
alter table public.checkpoint_blobs enable row level security;
