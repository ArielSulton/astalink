-- 0006_regulation_documents.sql
-- Index of regulation PDFs ingested by Phase 1's RAG pipeline. The chunks
-- themselves live in Pinecone (dense) + a serialized BM25 index file (sparse);
-- this table is the metadata catalog.

create table if not exists public.regulation_documents (
    id uuid primary key default gen_random_uuid(),
    source text not null,        -- e.g. 'OJK', 'UUPM', 'Perpajakan'
    title text not null,
    version text,
    doc_hash text not null unique,
    indexed_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists regulation_documents_source_idx
    on public.regulation_documents (source);
