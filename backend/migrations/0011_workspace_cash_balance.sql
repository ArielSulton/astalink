-- 0011_workspace_cash_balance.sql
-- Sandbox virtual cash balance per workspace. AstaLink's execution layer
-- only ever talks to SandboxBroker (backend/app/integrations/broker.py) —
-- no real money moves — so every workspace gets a virtual starting balance
-- that the optimizer/execution pipeline treats as real available cash,
-- debited on every filled order (backend/app/core/wallet.py).

alter table public.workspaces
    add column if not exists cash_balance numeric not null default 1000000000;
