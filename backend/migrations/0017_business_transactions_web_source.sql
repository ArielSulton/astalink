-- 0017_business_transactions_web_source.sql
-- Widens business_transactions.source to accept web-chatbot-originated
-- transactions alongside the existing WhatsApp values. See
-- docs/superpowers/specs/2026-09-06-chatbot-transaction-capture-design.md.

alter table public.business_transactions
    drop constraint if exists business_transactions_source_check;

alter table public.business_transactions
    add constraint business_transactions_source_check
    check (source in ('whatsapp_text', 'whatsapp_voice', 'whatsapp_photo', 'web_text', 'web_photo'));
