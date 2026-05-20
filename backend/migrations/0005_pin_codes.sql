-- 0005_pin_codes.sql
-- PIN-based approval gate for HITL (Phase 5). The hashing algorithm
-- (Argon2) is enforced in application code, not in DDL; this table just
-- stores the hash, salt, and a lockout counter.

create table if not exists public.pin_codes (
    user_id uuid primary key references auth.users (id) on delete cascade,
    hashed_pin text not null,
    salt text not null,
    attempts int not null default 0,
    last_failed_at timestamptz,
    locked_until timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
