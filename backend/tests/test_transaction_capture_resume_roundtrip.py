"""Drives the capture subgraph through REAL interrupt/resume round trips.

Every other confirm/persist test patches `interrupt` with a plain function,
so the node body runs exactly once and LangGraph's resume-time re-execution
of the interrupted task never happens. That is precisely the condition under
which the pending-row INSERT was duplicated (2026-09-07 investigation: the
row shown to the user stayed pending_confirmation forever while a second,
invisible row got confirmed). This file compiles the graph and resumes it
for real instead, so a side effect that cannot survive replay fails here.
"""
from __future__ import annotations

import itertools
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents.transaction_capture.schemas import TransactionExtraction

BIZ_ONE = [{"id": "biz-1", "name": "Warung Kopi"}]
BIZ_TWO = [{"id": "biz-1", "name": "Warung Kopi"},
           {"id": "biz-2", "name": "Toko Maju Jaya"}]

EXTRACTION = TransactionExtraction(
    is_transaction=True,
    item_description="Kopi",
    amount=20000.0,
    type="income",
    confidence=0.95,
    raw_input="aku menjual kopi 20 ribu rupiah",
)


class _Query:
    """One chained Supabase query against a single in-memory table."""

    def __init__(self, rows: list[dict], op: str, payload: dict | None = None):
        self._rows, self._op, self._payload = rows, op, payload
        self._filters: list[tuple[str, object]] = []

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def gte(self, col, val):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def _matching(self) -> list[dict]:
        return [r for r in self._rows
                if all(str(r.get(c)) == str(v) for c, v in self._filters)]

    def execute(self):
        if self._op == "select":
            return type("Res", (), {"data": self._matching()})
        if self._op == "update":
            for r in self._matching():
                r.update(self._payload)
            return type("Res", (), {"data": self._matching()})
        raise AssertionError(f"unsupported op {self._op}")


class _Table:
    def __init__(self, rows: list[dict], ids):
        self._rows, self._ids = rows, ids

    def insert(self, payload: dict):
        row = {**payload, "id": f"txn-{next(self._ids)}"}
        row.setdefault("confirmed_at", None)
        self._rows.append(row)
        return type("Q", (), {"execute": staticmethod(
            lambda: type("Res", (), {"data": [row]}))})()

    def select(self, *_cols):
        return _Query(self._rows, "select")

    def update(self, payload: dict):
        return _Query(self._rows, "update", payload)


class FakeSupabase:
    """Minimal in-memory stand-in for the supabase-py admin client."""

    def __init__(self):
        self.rows: dict[str, list[dict]] = {}
        self._ids = itertools.count(1)

    def table(self, name: str) -> _Table:
        return _Table(self.rows.setdefault(name, []), self._ids)


@pytest.fixture
def fake_db() -> FakeSupabase:
    return FakeSupabase()


def _compile_graph():
    """Production wiring, in-process checkpointer."""
    from app.agents.transaction_capture import graph as graph_mod

    with patch.object(graph_mod, "get_checkpointer", return_value=MemorySaver()):
        return graph_mod.build_capture_graph()


class _Chain:
    def invoke(self, _messages):
        return EXTRACTION


def _patched(fake_db):
    from app.agents.transaction_capture import node as node_mod

    return (
        patch.object(node_mod, "get_admin_client", return_value=fake_db),
        patch.object(node_mod, "_build_chain", return_value=_Chain()),
        patch.object(node_mod, "compute_plausibility_flag", return_value=False),
    )


def _capture(fake_db, *, candidates, decision, business_reply=None,
             thread="txn-roundtrip", remembered=None):
    """Run a full capture. Returns (business_payload, confirm_payload)."""
    a, b, c = _patched(fake_db)
    with a, b, c:
        g = _compile_graph()
        cfg = {"configurable": {"thread_id": thread}}
        out = g.invoke(
            {"candidate_businesses": candidates, "workspace_id": "ws-1",
             "business_id": remembered, "source": "web_text",
             "text_body": EXTRACTION.raw_input},
            config=cfg,
        )
        business_payload = None
        interrupts = out.get("__interrupt__") or []
        assert interrupts, "graph should have paused"
        if interrupts[0].value.get("kind") == "business_selection":
            business_payload = interrupts[0].value
            out = g.invoke(Command(resume={"business_id": business_reply}), config=cfg)
            interrupts = out.get("__interrupt__") or []
            if business_reply is None:
                return business_payload, None
            assert interrupts, "graph should have paused at the confirmation"
        confirm_payload = interrupts[0].value
        g.invoke(Command(resume={"decision": decision}), config=cfg)
        return business_payload, confirm_payload


# --------------------------------------------------------------------------
# The duplicate-row regression (D2)
# --------------------------------------------------------------------------

def test_confirmed_capture_writes_exactly_one_row(fake_db):
    _, payload = _capture(fake_db, candidates=BIZ_ONE, decision="confirmed")

    rows = fake_db.rows["business_transactions"]
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}: {rows}"
    assert rows[0]["id"] == payload["transaction_id"], (
        "the row the user was shown must be the row that gets confirmed"
    )
    assert rows[0]["status"] == "confirmed"
    assert rows[0]["confirmed_at"] is not None
    assert rows[0]["amount"] == 20000.0
    assert rows[0]["type"] == "income"
    assert rows[0]["source"] == "web_text"
    assert rows[0]["business_id"] == "biz-1"


def test_rejected_capture_leaves_one_rejected_row_and_no_rollup(fake_db):
    _, payload = _capture(fake_db, candidates=BIZ_ONE, decision="rejected")

    rows = fake_db.rows["business_transactions"]
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}: {rows}"
    assert rows[0]["id"] == payload["transaction_id"]
    assert rows[0]["status"] == "rejected"
    assert fake_db.rows.get("business_financial_records", []) == []


def test_no_pending_row_survives_a_confirmed_capture(fake_db):
    """The regression that bricked the chatbot: a leftover pending row made
    the old find_pending_transaction() deflect every later message for 24h."""
    _capture(fake_db, candidates=BIZ_ONE, decision="confirmed")

    pending = [r for r in fake_db.rows["business_transactions"]
               if r["status"] == "pending_confirmation"]
    assert pending == [], f"orphaned pending rows left behind: {pending}"


def test_confirmed_capture_rolls_up_financial_record(fake_db):
    _capture(fake_db, candidates=BIZ_ONE, decision="confirmed")

    recs = fake_db.rows["business_financial_records"]
    assert len(recs) == 1
    assert recs[0]["omset"] == 20000.0
    assert recs[0]["profit"] == 20000.0


# --------------------------------------------------------------------------
# Business selection (D1)
# --------------------------------------------------------------------------

def test_single_business_never_asks(fake_db):
    business_payload, confirm_payload = _capture(
        fake_db, candidates=BIZ_ONE, decision="confirmed")

    assert business_payload is None, "a lone business must not be asked about"
    assert confirm_payload["business_name"] == "Warung Kopi"


def test_two_businesses_ask_first_then_confirm(fake_db):
    business_payload, confirm_payload = _capture(
        fake_db, candidates=BIZ_TWO, decision="confirmed", business_reply="biz-2")

    assert business_payload["kind"] == "business_selection"
    assert business_payload["options"] == BIZ_TWO
    assert confirm_payload["kind"] == "confirmation"
    assert confirm_payload["business_name"] == "Toko Maju Jaya"

    rows = fake_db.rows["business_transactions"]
    assert len(rows) == 1
    assert rows[0]["business_id"] == "biz-2"
    assert rows[0]["status"] == "confirmed"


def test_remembered_business_skips_the_question(fake_db):
    business_payload, confirm_payload = _capture(
        fake_db, candidates=BIZ_TWO, decision="confirmed", remembered="biz-2")

    assert business_payload is None
    assert confirm_payload["business_name"] == "Toko Maju Jaya"
    assert fake_db.rows["business_transactions"][0]["business_id"] == "biz-2"


def test_stale_remembered_business_is_discarded_and_asked_again(fake_db):
    """A business that was deleted, or belongs to another workspace, must not
    silently become the target of a new transaction."""
    business_payload, _ = _capture(
        fake_db, candidates=BIZ_TWO, decision="confirmed",
        remembered="biz-gone", business_reply="biz-1")

    assert business_payload is not None
    assert fake_db.rows["business_transactions"][0]["business_id"] == "biz-1"


def test_cancelling_the_business_question_writes_nothing(fake_db):
    """Batalkan on the business card ends the run before stage_node, so no
    row is ever created — nothing to clean up afterwards."""
    business_payload, confirm_payload = _capture(
        fake_db, candidates=BIZ_TWO, decision="confirmed", business_reply=None)

    assert business_payload["kind"] == "business_selection"
    assert confirm_payload is None
    assert fake_db.rows.get("business_transactions", []) == []


# --------------------------------------------------------------------------
# Extraction gate
# --------------------------------------------------------------------------

def test_gate_failure_never_asks_which_business(fake_db):
    """A message we could not read must not cost the user a business choice."""
    from app.agents.transaction_capture import node as node_mod

    class _BadChain:
        def invoke(self, _messages):
            return TransactionExtraction(
                is_transaction=False, item_description=None, amount=None,
                type=None, confidence=0.1, raw_input="halo",
            )

    with patch.object(node_mod, "get_admin_client", return_value=fake_db), \
         patch.object(node_mod, "_build_chain", return_value=_BadChain()):
        g = _compile_graph()
        out = g.invoke(
            {"candidate_businesses": BIZ_TWO, "workspace_id": "ws-1",
             "source": "web_text", "text_body": "halo"},
            config={"configurable": {"thread_id": "txn-gate"}},
        )

    assert out.get("gate_failed") is True
    assert not out.get("__interrupt__")
    assert fake_db.rows.get("business_transactions", []) == []
