-- 0007_rls_policies.sql
-- Deny-by-default RLS on every Phase 0 table. Service-role (used by the
-- backend admin client) bypasses RLS — but the backend should still filter
-- by workspace_id in queries; RLS is the safety net, not the only check.

-- workspaces: a user can read/write only their own workspaces
alter table public.workspaces enable row level security;
create policy workspaces_select_own on public.workspaces
    for select using (owner_user_id = auth.uid());
create policy workspaces_insert_own on public.workspaces
    for insert with check (owner_user_id = auth.uid());
create policy workspaces_update_own on public.workspaces
    for update using (owner_user_id = auth.uid());
create policy workspaces_delete_own on public.workspaces
    for delete using (owner_user_id = auth.uid());

-- audit_log: a user can read only audit rows for workspaces they own.
-- Inserts come from the backend service-role client (RLS bypassed).
alter table public.audit_log enable row level security;
create policy audit_log_select_own on public.audit_log
    for select using (
        workspace_id in (
            select id from public.workspaces where owner_user_id = auth.uid()
        )
    );

-- allocation_plans: same pattern (read-only via user JWT)
alter table public.allocation_plans enable row level security;
create policy allocation_plans_select_own on public.allocation_plans
    for select using (
        audit_id in (
            select audit_id from public.audit_log
            where workspace_id in (
                select id from public.workspaces where owner_user_id = auth.uid()
            )
        )
    );

-- transactions: same pattern
alter table public.transactions enable row level security;
create policy transactions_select_own on public.transactions
    for select using (
        audit_id in (
            select audit_id from public.audit_log
            where workspace_id in (
                select id from public.workspaces where owner_user_id = auth.uid()
            )
        )
    );

-- pin_codes: a user can read/write only their own row
alter table public.pin_codes enable row level security;
create policy pin_codes_select_own on public.pin_codes
    for select using (user_id = auth.uid());
create policy pin_codes_insert_own on public.pin_codes
    for insert with check (user_id = auth.uid());
create policy pin_codes_update_own on public.pin_codes
    for update using (user_id = auth.uid());

-- regulation_documents: world-readable (regulations aren't user-scoped),
-- writes only via service-role.
alter table public.regulation_documents enable row level security;
create policy regulation_documents_select_all on public.regulation_documents
    for select using (true);
