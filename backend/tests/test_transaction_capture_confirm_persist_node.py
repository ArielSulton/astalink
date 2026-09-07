from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.node import (
    confirm_node,
    persist_node,
    rejected_node,
    resolve_business_node,
    stage_node,
)


def _mock_admin() -> MagicMock:
    sb = MagicMock()
    insert_query = MagicMock()
    insert_query.execute.return_value = MagicMock(data=[{"id": "txn-1"}])
    sb.table.return_value.insert.return_value = insert_query
    return sb


_EXTRACTION = {"item_description": "Nasi goreng", "amount": 15000.0,
               "type": "income", "confidence": 0.9, "raw_input": "x",
               "is_transaction": True}


def test_stage_node_inserts_pending_row() -> None:
    state = {"business_id": "biz-1", "extraction": _EXTRACTION, "source": "whatsapp_text"}
    fake_admin = _mock_admin()

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.transaction_capture.node.compute_plausibility_flag", return_value=False):
        update = stage_node(state)

    assert update == {"transaction_id": "txn-1", "plausibility_flag": False}
    inserted = fake_admin.table.return_value.insert.call_args[0][0]
    assert inserted["status"] == "pending_confirmation"
    assert inserted["business_id"] == "biz-1"


def test_confirm_node_pauses_without_touching_the_database() -> None:
    """confirm_node is replayed from the top when the run resumes, so it must
    have no side effect other than the interrupt itself — the pending row is
    stage_node's job."""
    state = {"business_id": "biz-1", "transaction_id": "txn-1", "plausibility_flag": False,
             "business_name": "Warung Kopi", "extraction": _EXTRACTION,
             "source": "whatsapp_text"}
    fake_admin = _mock_admin()

    def fake_interrupt(payload):
        assert payload["kind"] == "confirmation"
        assert payload["transaction_id"] == "txn-1"
        assert payload["amount"] == 15000.0
        assert payload["business_name"] == "Warung Kopi"
        return {"decision": "confirmed"}

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=fake_admin), \
         patch("app.agents.transaction_capture.node.interrupt", side_effect=fake_interrupt):
        update = confirm_node(state)

    assert update == {"confirmed": True}
    fake_admin.table.assert_not_called()


def test_confirm_node_returns_rejected_on_tidak() -> None:
    state = {"business_id": "biz-1", "transaction_id": "txn-1", "plausibility_flag": False,
             "extraction": _EXTRACTION, "source": "whatsapp_text"}

    with patch("app.agents.transaction_capture.node.interrupt",
               return_value={"decision": "rejected"}):
        assert confirm_node(state)["confirmed"] is False


def test_resolve_business_node_uses_the_only_business_without_asking() -> None:
    state = {"candidate_businesses": [{"id": "biz-1", "name": "Warung Kopi"}]}

    with patch("app.agents.transaction_capture.node.interrupt") as interrupt_mock:
        update = resolve_business_node(state)

    interrupt_mock.assert_not_called()
    assert update["business_id"] == "biz-1"
    assert update["business_name"] == "Warung Kopi"
    assert update["business_cancelled"] is False


def test_resolve_business_node_reuses_what_the_thread_remembers() -> None:
    state = {"candidate_businesses": [{"id": "biz-1", "name": "Warung Kopi"},
                                      {"id": "biz-2", "name": "Toko Maju Jaya"}],
             "business_id": "biz-2"}

    with patch("app.agents.transaction_capture.node.interrupt") as interrupt_mock:
        update = resolve_business_node(state)

    interrupt_mock.assert_not_called()
    assert update["business_id"] == "biz-2"
    assert update["business_name"] == "Toko Maju Jaya"


def test_resolve_business_node_asks_again_when_forced() -> None:
    """WhatsApp's "ganti bisnis" — ignore the remembered choice."""
    state = {"candidate_businesses": [{"id": "biz-1", "name": "Warung Kopi"},
                                      {"id": "biz-2", "name": "Toko Maju Jaya"}],
             "business_id": "biz-2", "force_business_choice": True}

    with patch("app.agents.transaction_capture.node.interrupt",
               return_value={"business_id": "biz-1"}) as interrupt_mock:
        update = resolve_business_node(state)

    assert interrupt_mock.call_args[0][0]["kind"] == "business_selection"
    assert update["business_id"] == "biz-1"
    assert update["force_business_choice"] is False


def test_resolve_business_node_cancels_on_a_null_choice() -> None:
    state = {"candidate_businesses": [{"id": "biz-1", "name": "Warung Kopi"},
                                      {"id": "biz-2", "name": "Toko Maju Jaya"}]}

    with patch("app.agents.transaction_capture.node.interrupt",
               return_value={"business_id": None}):
        update = resolve_business_node(state)

    assert update["business_cancelled"] is True
    assert update["business_id"] is None


def test_resolve_business_node_cancels_when_there_are_no_businesses() -> None:
    """The API layer refuses to invoke with zero businesses; this is the belt
    and braces that stops a bad caller writing an orphan row."""
    with patch("app.agents.transaction_capture.node.interrupt") as interrupt_mock:
        update = resolve_business_node({"candidate_businesses": []})

    interrupt_mock.assert_not_called()
    assert update["business_cancelled"] is True


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


def test_persist_node_carries_forward_nonzero_aset_from_prior_year() -> None:
    """Verify that aset from prior year is carried forward exactly, not zeroed."""
    state = {"transaction_id": "txn-1", "business_id": "biz-1",
             "extraction": {"type": "income", "amount": 10000.0}}

    bt_table = MagicMock()
    bt_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    bfr_table = MagicMock()
    # Query for current year returns empty
    current_year_select = MagicMock()
    current_year_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # Query for prior year returns a record with non-zero aset
    prior_year_select = MagicMock()
    prior_year_select.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"aset": 75000.0}]
    )
    bfr_table.select.side_effect = [current_year_select, prior_year_select]
    bfr_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    sb = MagicMock()
    sb.table.side_effect = lambda name: bt_table if name == "business_transactions" else bfr_table

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb):
        persist_node(state)

    # Assert the inserted row carries forward the prior aset exactly
    inserted = bfr_table.insert.call_args[0][0]
    assert inserted["aset"] == 75000.0, f"Expected aset=75000.0, got {inserted['aset']}"
    assert inserted["omset"] == 10000.0
    assert inserted["profit"] == 10000.0


def test_persist_node_increments_existing_year_record_for_income() -> None:
    """Verify income increments both omset and profit for existing year."""
    state = {"transaction_id": "txn-1", "business_id": "biz-1",
             "extraction": {"type": "income", "amount": 25000.0}}

    bt_table = MagicMock()
    bt_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    bfr_table = MagicMock()
    existing_select = MagicMock()
    existing_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "rec-1", "omset": 100000.0, "profit": 50000.0}],
    )
    bfr_table.select.return_value = existing_select
    bfr_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    sb = MagicMock()
    sb.table.side_effect = lambda name: bt_table if name == "business_transactions" else bfr_table

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb):
        persist_node(state)

    updated = bfr_table.update.call_args[0][0]
    assert updated["omset"] == 125000.0  # 100000 + 25000
    assert updated["profit"] == 75000.0  # 50000 + 25000


def test_persist_node_creates_new_year_record_for_expense() -> None:
    """Verify expense creates new year with omset=0.0 and negative profit."""
    state = {"transaction_id": "txn-1", "business_id": "biz-1",
             "extraction": {"type": "expense", "amount": 8000.0}}

    bt_table = MagicMock()
    bt_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])

    bfr_table = MagicMock()
    # Query for current year returns empty
    current_year_select = MagicMock()
    current_year_select.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # Query for prior year returns empty
    prior_year_select = MagicMock()
    prior_year_select.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    bfr_table.select.side_effect = [current_year_select, prior_year_select]
    bfr_table.insert.return_value.execute.return_value = MagicMock(data=[{}])

    sb = MagicMock()
    sb.table.side_effect = lambda name: bt_table if name == "business_transactions" else bfr_table

    with patch("app.agents.transaction_capture.node.get_admin_client", return_value=sb):
        persist_node(state)

    inserted = bfr_table.insert.call_args[0][0]
    assert inserted["business_id"] == "biz-1"
    assert inserted["omset"] == 0.0, f"Expected omset=0.0 for expense new-year, got {inserted['omset']}"
    assert inserted["profit"] == -8000.0, f"Expected profit=-8000.0 for expense, got {inserted['profit']}"
    assert inserted["aset"] == 0.0
