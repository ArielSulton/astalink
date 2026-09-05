from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.resume import (
    detect_transaction_reply,
    find_pending_transaction,
    resolve_single_business,
    resume_transaction,
)


def test_detect_transaction_reply_recognizes_yes_variants() -> None:
    for text in ["ya", "Ya", "iya", "setuju", "oke", "ok", "benar", "betul"]:
        assert detect_transaction_reply(text) == "confirmed", text


def test_detect_transaction_reply_recognizes_no_variants() -> None:
    for text in ["tidak", "Tidak.", "gak", "ga", "nggak", "batal", "salah"]:
        assert detect_transaction_reply(text) == "rejected", text


def test_detect_transaction_reply_recognizes_button_ids() -> None:
    """The transaction confirmation card uses distinct button ids
    (txn_ya/txn_tidak) so a tap on it can never be misinterpreted as a
    reply to the composition-gate card, which uses plain ya/tidak."""
    assert detect_transaction_reply("txn_ya") == "confirmed"
    assert detect_transaction_reply("txn_tidak") == "rejected"


def test_detect_transaction_reply_returns_none_for_longer_phrases() -> None:
    assert detect_transaction_reply("jual nasi goreng 15rb") is None
    assert detect_transaction_reply("") is None


def test_resolve_single_business_returns_id_when_exactly_one() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "biz-1"}],
    )
    assert resolve_single_business(fake_admin, "ws-1") == "biz-1"


def test_resolve_single_business_returns_none_when_zero_or_multiple() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    assert resolve_single_business(fake_admin, "ws-1") is None

    fake_admin.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "biz-1"}, {"id": "biz-2"}],
    )
    assert resolve_single_business(fake_admin, "ws-1") is None


def test_resolve_single_business_degrades_gracefully_on_error() -> None:
    fake_admin = MagicMock()
    fake_admin.table.side_effect = Exception("db down")
    assert resolve_single_business(fake_admin, "ws-1") is None


def test_find_pending_transaction_returns_latest_id() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "txn-42"}],
        )
    assert find_pending_transaction(fake_admin, "biz-1") == "txn-42"


def test_find_pending_transaction_returns_none_when_empty() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    assert find_pending_transaction(fake_admin, "biz-1") is None


def test_find_pending_transaction_filters_by_created_at_cutoff() -> None:
    """A pending row is only ever fetched through a query chain that applies
    a .gte("created_at", ...) cutoff — verifying the chain includes that
    call (rather than any specific timestamp value) is what matters here,
    since a stale row older than the cutoff would simply never match the
    real database's WHERE clause and the query would return empty."""
    fake_admin = MagicMock()
    gte_call = fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.gte
    gte_call.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    assert find_pending_transaction(fake_admin, "biz-1") is None
    assert gte_call.call_args[0][0] == "created_at"


def test_resume_transaction_invokes_capture_graph_with_command_resume() -> None:
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"confirmed": True}
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        result = resume_transaction("wa-txn-628123-ws-1", "confirmed")

    assert result == {"confirmed": True}
    fake_graph.invoke.assert_called_once()
    call_kwargs = fake_graph.invoke.call_args
    assert call_kwargs.kwargs["config"]["configurable"]["thread_id"] == "wa-txn-628123-ws-1"
