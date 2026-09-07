from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agents.transaction_capture.resume import (
    BUSINESS_CANCEL,
    detect_business_choice,
    detect_transaction_reply,
    fresh_capture_input,
    list_businesses,
    pending_interrupt,
    remembered_business_id,
    resume_business_choice,
    resume_transaction,
)

OPTIONS = [{"id": "biz-1", "name": "Warung Kopi"},
           {"id": "biz-2", "name": "Toko Maju Jaya"}]


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


# --------------------------------------------------------------------------
# Business choice
# --------------------------------------------------------------------------

def test_detect_business_choice_accepts_the_web_marker() -> None:
    assert detect_business_choice("bizsel_biz-2", OPTIONS) == "biz-2"


def test_detect_business_choice_rejects_a_marker_for_another_workspace() -> None:
    """A stale card from a different workspace must not select anything."""
    assert detect_business_choice("bizsel_biz-99", OPTIONS) is None


def test_detect_business_choice_accepts_whatsapp_numbering() -> None:
    assert detect_business_choice("1", OPTIONS) == "biz-1"
    assert detect_business_choice("2", OPTIONS) == "biz-2"


def test_detect_business_choice_rejects_out_of_range_numbers() -> None:
    assert detect_business_choice("0", OPTIONS) is None
    assert detect_business_choice("3", OPTIONS) is None


def test_detect_business_choice_accepts_an_exact_name() -> None:
    assert detect_business_choice("Warung Kopi", OPTIONS) == "biz-1"
    assert detect_business_choice("toko maju jaya", OPTIONS) == "biz-2"


def test_detect_business_choice_recognizes_cancellation() -> None:
    for text in ["batal", "Batalkan", "cancel", "bizsel_batal"]:
        assert detect_business_choice(text, OPTIONS) == BUSINESS_CANCEL, text


def test_detect_business_choice_returns_none_for_anything_else() -> None:
    assert detect_business_choice("jual kopi 5rb", OPTIONS) is None
    assert detect_business_choice("", OPTIONS) is None


# --------------------------------------------------------------------------
# Business listing
# --------------------------------------------------------------------------

def test_list_businesses_returns_id_and_name_oldest_first() -> None:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.order \
        .return_value.execute.return_value = MagicMock(
            data=[{"id": "biz-1", "name": "Warung Kopi"},
                  {"id": "biz-2", "name": "Toko Maju Jaya"}],
        )
    assert list_businesses(fake_admin, "ws-1") == OPTIONS


def test_list_businesses_degrades_gracefully_on_error() -> None:
    fake_admin = MagicMock()
    fake_admin.table.side_effect = Exception("db down")
    assert list_businesses(fake_admin, "ws-1") == []


# --------------------------------------------------------------------------
# Graph-state pause detection
# --------------------------------------------------------------------------

def _snapshot(interrupt_values: list[dict], values: dict | None = None):
    tasks = tuple(
        SimpleNamespace(interrupts=(SimpleNamespace(value=v),)) for v in interrupt_values
    )
    return SimpleNamespace(tasks=tasks, values=values or {})


def test_pending_interrupt_reports_the_kind_it_is_waiting_for() -> None:
    fake_graph = MagicMock()
    fake_graph.get_state.return_value = _snapshot(
        [{"kind": "business_selection", "options": OPTIONS}])
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        payload = pending_interrupt("txn-thread")

    assert payload["kind"] == "business_selection"
    assert fake_graph.get_state.call_args[0][0]["configurable"]["thread_id"] == "txn-thread"


def test_pending_interrupt_is_none_for_an_unused_thread() -> None:
    """A thread that never ran has no tasks — no TTL, no stale-row guessing."""
    fake_graph = MagicMock()
    fake_graph.get_state.return_value = _snapshot([])
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        assert pending_interrupt("never-used") is None


def test_pending_interrupt_degrades_gracefully_when_the_checkpointer_fails() -> None:
    fake_graph = MagicMock()
    fake_graph.get_state.side_effect = Exception("checkpointer down")
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        assert pending_interrupt("txn-thread") is None


def test_remembered_business_id_reads_the_threads_last_choice() -> None:
    fake_graph = MagicMock()
    fake_graph.get_state.return_value = _snapshot([], {"business_id": "biz-2"})
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        assert remembered_business_id("txn-thread") == "biz-2"


def test_remembered_business_id_is_none_on_a_fresh_thread() -> None:
    fake_graph = MagicMock()
    fake_graph.get_state.return_value = _snapshot([], {})
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        assert remembered_business_id("txn-thread") is None


# --------------------------------------------------------------------------
# Input construction
# --------------------------------------------------------------------------

def test_fresh_capture_input_resets_every_per_run_field() -> None:
    """Invoking on an existing thread merges into the previous checkpoint, so
    a stale extraction or transaction_id would otherwise leak into the new
    capture."""
    payload = fresh_capture_input(
        workspace_id="ws-1", candidate_businesses=OPTIONS,
        source="web_text", text_body="jual kopi 5rb", remembered="biz-2",
    )

    assert payload["extraction"] is None
    assert payload["gate_failed"] is False
    assert payload["transaction_id"] is None
    assert payload["confirmed"] is None
    assert payload["business_name"] is None
    assert payload["business_cancelled"] is False
    assert payload["plausibility_flag"] is False
    # business_id is the deliberate exception: it carries the remembered choice.
    assert payload["business_id"] == "biz-2"
    assert payload["candidate_businesses"] == OPTIONS


def test_fresh_capture_input_can_force_the_question() -> None:
    payload = fresh_capture_input(
        workspace_id="ws-1", candidate_businesses=OPTIONS, source="whatsapp_text",
        text_body="jual kopi 5rb", remembered="biz-2", force_business_choice=True,
    )
    assert payload["force_business_choice"] is True


# --------------------------------------------------------------------------
# Resume
# --------------------------------------------------------------------------

def test_resume_transaction_invokes_capture_graph_with_command_resume() -> None:
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"confirmed": True}
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        result = resume_transaction("wa-txn-628123-ws-1", "confirmed")

    assert result == {"confirmed": True}
    fake_graph.invoke.assert_called_once()
    call_kwargs = fake_graph.invoke.call_args
    assert call_kwargs.kwargs["config"]["configurable"]["thread_id"] == "wa-txn-628123-ws-1"


def test_resume_business_choice_passes_the_id_through() -> None:
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {"__interrupt__": []}
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        resume_business_choice("txn-thread", "biz-2")

    assert fake_graph.invoke.call_args.args[0].resume == {"business_id": "biz-2"}


def test_resume_business_choice_passes_none_to_cancel() -> None:
    fake_graph = MagicMock()
    fake_graph.invoke.return_value = {}
    with patch("app.agents.transaction_capture.graph.capture_graph", fake_graph):
        resume_business_choice("txn-thread", None)

    assert fake_graph.invoke.call_args.args[0].resume == {"business_id": None}
