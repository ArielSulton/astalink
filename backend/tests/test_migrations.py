"""Structural tests for the migration files. We assert each file exists and
contains the expected DDL keywords, but we do NOT execute SQL — the team
applies migrations manually through Supabase Studio."""
from pathlib import Path

MIG_DIR = Path(__file__).parent.parent / "migrations"


def _read(name: str) -> str:
    return (MIG_DIR / name).read_text().lower()


def test_migration_0001_workspaces_exists() -> None:
    sql = _read("0001_workspaces.sql")
    assert "create table" in sql
    assert "workspaces" in sql
    assert "owner_user_id" in sql
    assert "type" in sql
    assert "personal" in sql and "business" in sql


def test_migration_0002_audit_log_exists() -> None:
    sql = _read("0002_audit_log.sql")
    assert "create table" in sql
    assert "audit_log" in sql
    assert "audit_id" in sql
    assert "workspace_id" in sql
    assert "intent" in sql
    assert "payload" in sql
    assert "jsonb" in sql


def test_migration_0003_allocation_plans_exists() -> None:
    sql = _read("0003_allocation_plans.sql")
    assert "create table" in sql
    assert "allocation_plans" in sql
    assert "audit_id" in sql
    assert "plan_json" in sql
    assert "legal_status" in sql
    assert "revision_count" in sql


def test_migration_0004_transactions_exists() -> None:
    sql = _read("0004_transactions.sql")
    assert "create table" in sql
    assert "transactions" in sql
    assert "allocation_plan_id" in sql
    assert "broker_ref" in sql
    assert "unique" in sql


def test_migration_0005_pin_codes_exists() -> None:
    sql = _read("0005_pin_codes.sql")
    assert "create table" in sql
    assert "pin_codes" in sql
    assert "hashed_pin" in sql
    assert "salt" in sql
    assert "attempts" in sql
    assert "locked_until" in sql


def test_migration_0006_regulation_documents_exists() -> None:
    sql = _read("0006_regulation_documents.sql")
    assert "create table" in sql
    assert "regulation_documents" in sql
    assert "doc_hash" in sql
    assert "indexed_at" in sql


def test_migration_0007_rls_policies_exists() -> None:
    sql = _read("0007_rls_policies.sql")
    for table in (
        "workspaces",
        "audit_log",
        "allocation_plans",
        "transactions",
        "pin_codes",
        "regulation_documents",
    ):
        assert f"alter table public.{table} enable row level security" in sql, \
            f"RLS not enabled on {table}"
    assert sql.count("create policy") >= 6, "expected ≥6 policies"
    assert "owner_user_id = auth.uid()" in sql or "auth.uid() = owner_user_id" in sql


def test_migration_0008_langgraph_checkpoints_exists() -> None:
    sql = _read("0008_langgraph_checkpoints.sql")
    assert "checkpoints" in sql
    assert "checkpoint_writes" in sql or "checkpoint_blobs" in sql


def test_migration_0009_whatsapp_exists() -> None:
    sql = _read("0009_whatsapp.sql")
    for table in ("whatsapp_bindings", "whatsapp_messages_seen", "whatsapp_pending_codes"):
        assert table in sql
    assert "phone_e164" in sql
