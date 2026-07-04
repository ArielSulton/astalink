# AstaLink Database Migrations

Plain SQL migrations applied manually via the Supabase Studio SQL editor.

## How to apply

1. Open your Supabase project → **SQL Editor**.
2. Paste the contents of each `NNNN_*.sql` file in numerical order.
3. Run each. Verify under **Table Editor** that the new table appears with the
   expected columns and that **Enable RLS** shows green.
4. After all migrations are applied, smoke-test from the Phase 0 acceptance
   checklist (insert one workspace as the authenticated user, confirm select
   returns it; confirm a second user cannot select it).

## Why not automated?

For the hackathon timeline, manual application via Supabase Studio is the
team's chosen workflow. A future enhancement could move this to
`supabase migration` CLI or the [supabase-py migrations API], but that's out
of scope for Phase 0.

## File order

| File | Purpose |
|------|---------|
| `0001_workspaces.sql` | Workspace isolation (Personal/Business) |
| `0002_audit_log.sql` | End-to-end pipeline trace |
| `0003_allocation_plans.sql` | Per-run allocation proposals + revision count |
| `0004_transactions.sql` | Broker orders with idempotency constraint |
| `0005_pin_codes.sql` | HITL approval gate storage |
| `0006_regulation_documents.sql` | RAG metadata catalog |
| `0007_rls_policies.sql` | Deny-by-default workspace-scoped access |
| `0008_langgraph_checkpoints.sql` | LangGraph checkpoint tables (schema kept current via `saver.setup()`) |
| `0009_whatsapp.sql` | WhatsApp binding + dedup + pending-code tables |
| `0010_businesses.sql` | User-owned businesses + per-period financial records (aset/omset/profit) |
| `0011_workspace_cash_balance.sql` | Sandbox virtual cash balance per workspace (seeded at Rp 1,000,000,000) |
