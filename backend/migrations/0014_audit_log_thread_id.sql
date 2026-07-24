-- 0014_audit_log_thread_id.sql
-- Persist the LangGraph thread_id each pipeline run was actually invoked
-- under, so the Approvals endpoint can resume the SAME paused run instead of
-- guessing a thread_id (it previously used audit_id, which never matches any
-- real thread — chat.py, agent.py, and whatsapp.py each build a different
-- thread_id format — silently starting a fresh, empty run on approve/reject).

alter table public.audit_log
    add column if not exists thread_id text;
