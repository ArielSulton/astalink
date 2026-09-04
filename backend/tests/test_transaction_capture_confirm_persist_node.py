from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.node import confirm_node, persist_node, rejected_node


def _mock_admin() -> MagicMock:
    sb = MagicMock()
    insert_query = MagicMock()
    insert_query.execute.return_value = MagicMock(data=[{"id": "txn-1"}])
    sb.table.return_value.insert.return_value = insert_query
    return sb


def test_confirm_node_inserts_pending_row_and_pauses(monkeypatch) -> None:
    state = {
        "business_id": "biz-1",
        "extraction": {"item_description": "Nasi goreng", "amount": 15000.0,
                        "type": "income", "confidence": 0.9, "raw_input": "x",
                        "is_transaction": True},
        "source": "whatsapp_text",
    }
    fake_admin = _mock_admin()

    def fake_interrupt(payload):
        assert payload["transaction_id"] == "txn-1"
        assert payload["amount"] == 15000.0
        return {"decision": "confirmed"}

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.transaction_capture.node.compute_plausibility_flag", return_value=False), \
         patch("app.agents.transaction_capture.node.interrupt", side_effect=fake_interrupt):
        update = confirm_node(state)

    assert update == {"confirmed": True, "transaction_id": "txn-1", "plausibility_flag": False}
    inserted = fake_admin.table.return_value.insert.call_args[0][0]
    assert inserted["status"] == "pending_confirmation"
    assert inserted["business_id"] == "biz-1"


def test_confirm_node_returns_rejected_on_tidak(monkeypatch) -> None:
    state = {
        "business_id": "biz-1",
        "extraction": {"item_description": "Nasi goreng", "amount": 15000.0,
                        "type": "income", "confidence": 0.9, "raw_input": "x",
                        "is_transaction": True},
        "source": "whatsapp_text",
    }
    fake_admin = _mock_admin()

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.transaction_capture.node.compute_plausibility_flag", return_value=False), \
         patch("app.agents.transaction_capture.node.interrupt", return_value={"decision": "rejected"}):
        update = confirm_node(state)

    assert update["confirmed"] is False


def test_persist_node_marks_confirmed_and_creates_new_year_record() -> None:
    state = {"transaction_id": "txn-1", "business_id": "biz-1",
             "extraction": {"type": "income", "amount": 15000.0}}

    bt_table = MagicMock()
    bt_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    bfr_table = MagicMock()
    bfr_select = MagicMock()
    bfr_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    bfr_prior_select = MagicMock()
    bfr_prior_select.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    bfr_table.select.side_effect = [bfr_select, bfr_prior_select]
    bfr_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    sb2 = MagicMock()
    sb2.table.side_effect = lambda name: bt_table if name == "business_transactions" else bfr_table

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb2):
        persist_node(state)

    bt_table.update.assert_called_once()
    assert bt_table.update.call_args[0][0]["status"] == "confirmed"
    inserted = bfr_table.insert.call_args[0][0]
    assert inserted["business_id"] == "biz-1"
    assert inserted["omset"] == 15000.0
    assert inserted["profit"] == 15000.0
    assert inserted["aset"] == 0.0


def test_persist_node_increments_existing_year_record_for_expense() -> None:
    state = {"transaction_id": "txn-1", "business_id": "biz-1",
             "extraction": {"type": "expense", "amount": 5000.0}}

    bt_table = MagicMock()
    bt_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    bfr_table = MagicMock()
    existing_select = MagicMock()
    existing_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "rec-1", "omset": 100000.0, "profit": 20000.0}],
    )
    bfr_table.select.return_value = existing_select
    bfr_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    sb = MagicMock()
    sb.table.side_effect = lambda name: bt_table if name == "business_transactions" else bfr_table

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb):
        persist_node(state)

    updated = bfr_table.update.call_args[0][0]
    assert updated["omset"] == 100000.0  # unchanged, expense doesn't touch omset
    assert updated["profit"] == 15000.0  # 20000 - 5000


def test_rejected_node_marks_row_rejected() -> None:
    state = {"transaction_id": "txn-1"}
    sb = MagicMock()
    update_query = MagicMock()
    update_query.eq.return_value.execute.return_value = MagicMock(data=[{}])
    sb.table.return_value.update.return_value = update_query

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb):
        rejected_node(state)

    assert sb.table.return_value.update.call_args[0][0]["status"] == "rejected"
