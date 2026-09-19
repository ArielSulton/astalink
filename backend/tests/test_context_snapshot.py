from unittest.mock import MagicMock, patch

from app.agents.context_snapshot import (
    MAX_TRANSACTIONS,
    WorkspaceSnapshot,
    format_rupiah,
    load_snapshot,
)


def test_load_snapshot_without_workspace_id_returns_empty_without_querying() -> None:
    """A run with no _workspace_id (WhatsApp binding not resolved yet, or a
    unit test) must not touch Supabase at all."""
    with patch("app.agents.context_snapshot.get_admin_client") as get_client:
        snapshot = load_snapshot(None)

    get_client.assert_not_called()
    assert snapshot.is_empty
    assert snapshot.render_for_prompt() == ""


def test_load_snapshot_swallows_db_failure() -> None:
    """Snapshot is a nice-to-have: a broken Supabase must degrade the reply,
    never break the run."""
    with patch("app.agents.context_snapshot.get_admin_client",
               side_effect=RuntimeError("no service role key")):
        snapshot = load_snapshot("ws-1")

    assert snapshot.is_empty


def test_load_snapshot_collects_balance_businesses_transactions_holdings() -> None:
    sb = MagicMock()

    def table(name: str):
        t = MagicMock()
        if name == "workspaces":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
                MagicMock(data=[{"cash_balance": 12_400_000}])
        elif name == "businesses":
            t.select.return_value.eq.return_value.execute.return_value = \
                MagicMock(data=[{"id": "b-1", "name": "Warung Kopi Ampera"}])
        elif name == "business_intake_profiles":
            t.select.return_value.in_.return_value.execute.return_value = \
                MagicMock(data=[{"business_id": "b-1"}])
        elif name == "business_transactions":
            t.select.return_value.in_.return_value.eq.return_value.order.return_value \
                .limit.return_value.execute.return_value = MagicMock(data=[
                    {"occurred_at": "2026-09-18T09:00:00+00:00", "amount": 4_100_000,
                     "type": "income", "source": "whatsapp_photo", "business_id": "b-1"},
                ])
        elif name == "holdings":
            t.select.return_value.eq.return_value.execute.return_value = \
                MagicMock(data=[{"ticker": "BBCA", "quantity": 200}])
        return t

    sb.table.side_effect = table

    with patch("app.agents.context_snapshot.get_admin_client", return_value=sb):
        snapshot = load_snapshot("ws-1")

    assert snapshot.cash_balance == 12_400_000
    assert [b.name for b in snapshot.businesses] == ["Warung Kopi Ampera"]
    assert snapshot.businesses[0].has_intake_profile is True
    assert len(snapshot.recent_transactions) == 1
    assert snapshot.recent_transactions[0].amount == 4_100_000
    assert snapshot.recent_transactions[0].business_name == "Warung Kopi Ampera"
    assert [h.ticker for h in snapshot.holdings] == ["BBCA"]
    assert not snapshot.is_empty


def test_render_for_prompt_mentions_real_numbers() -> None:
    snapshot = WorkspaceSnapshot(
        cash_balance=12_400_000,
        recent_transactions=[],
        holdings=[],
        businesses=[],
    )
    rendered = snapshot.render_for_prompt()

    assert "Rp 12.400.000" in rendered


def test_format_rupiah_uses_indonesian_thousands_separator() -> None:
    assert format_rupiah(12_400_000) == "Rp 12.400.000"


def test_max_transactions_is_five() -> None:
    assert MAX_TRANSACTIONS == 5
