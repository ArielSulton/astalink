"""Endpoint-level coverage for the business-selection step and the
no-business reply — the 2026-09-07 defect D1, where a transaction message
sent from a workspace that owned no single business fell through to the
advisory graph and was answered as an investment question with no hint that
nothing had been recorded."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agents.state import new_state

OPTIONS = [{"id": "biz-1", "name": "Warung Kopi"},
           {"id": "biz-2", "name": "Toko Maju Jaya"}]


def _make_fake_admin() -> MagicMock:
    """Workspace-ownership query returns the workspace, so the request passes
    assert_workspace_owned."""
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .limit.return_value.execute.return_value = MagicMock(data=[{"id": "ws-1"}])
    return fake_admin


@pytest.fixture(autouse=True)
def _no_remembered_business():
    with patch("app.api.v1.chat.remembered_business_id", return_value=None):
        yield


def _post(client: TestClient, message: str):
    return client.post(
        "/api/v1/chat/",
        json={"message": message, "workspace_id": "ws-1"},
        headers={"Authorization": "Bearer fake-token"},
    )


def _base_patches(businesses, pending):
    return (
        patch("app.api.deps.verify_token", return_value={"sub": "user-1", "email": "t@example.com"}),
        patch("app.api.v1.chat.get_admin_client", return_value=_make_fake_admin()),
        patch("app.api.v1.chat.list_businesses", return_value=businesses),
        patch("app.api.v1.chat.pending_interrupt", return_value=pending),
        patch("app.api.v1.chat.find_pending_composition_audit", return_value=None),
    )


def test_text_without_any_business_requires_business_setup(client: TestClient) -> None:
    a, b, c, d, e = _base_patches([], None)
    with a, b, c, d, e, \
         patch("app.api.v1.chat.capture_graph") as capture_mock, \
         patch("app.api.v1.chat.graph.invoke") as advisory_mock:
        res = _post(client, "saya baru saja menjual kopi 20.000 pada bisnis saya")

    assert res.status_code == 200
    body = res.json()
    assert body["requires_business_setup"] is True
    assert "bisnis" in body["message"].lower()
    capture_mock.invoke.assert_not_called()
    advisory_mock.assert_not_called()


def test_ordinary_advisory_text_without_business_still_reaches_the_graph(
    client: TestClient,
) -> None:
    """The no-business guard must stay narrow — and LLM-free, so users who own
    no business don't pay a model call on every advisory message."""
    final_state = new_state()
    final_state["messages"] = [AIMessage(content="Tentu, ini analisisnya.")]

    a, b, c, d, e = _base_patches([], None)
    with a, b, c, d, e, \
         patch("app.api.v1.chat.graph.invoke", return_value=final_state) as advisory_mock:
        res = _post(client, "bagaimana prospek IHSG minggu ini")

    assert res.status_code == 200
    assert res.json()["requires_business_setup"] is False
    advisory_mock.assert_called_once()


def test_two_businesses_render_a_business_choice_card(client: TestClient) -> None:
    payload = MagicMock()
    payload.value = {"kind": "business_selection", "options": OPTIONS}

    a, b, c, d, e = _base_patches(OPTIONS, None)
    with a, b, c, d, e, \
         patch("app.api.v1.chat.looks_like_transaction", return_value=True), \
         patch("app.api.v1.chat.capture_graph") as capture_mock:
        capture_mock.invoke.return_value = {"__interrupt__": [payload]}
        res = _post(client, "jual teh manis 5rb")

    assert res.status_code == 200
    body = res.json()
    assert body["pending_business_choice"] == {"options": OPTIONS}
    assert body["pending_transaction"] is None
    assert "bisnis yang mana" in body["message"].lower()


def test_bizsel_marker_resumes_the_question_and_shows_the_confirmation(
    client: TestClient,
) -> None:
    confirm = MagicMock()
    confirm.value = {
        "kind": "confirmation", "transaction_id": "txn-1", "item_description": "Teh manis",
        "amount": 5000.0, "type": "income", "plausibility_flag": False,
        "business_name": "Toko Maju Jaya",
    }

    a, b, c, d, e = _base_patches(OPTIONS, {"kind": "business_selection", "options": OPTIONS})
    with a, b, c, d, e, \
         patch("app.api.v1.chat.resume_business_choice") as resume_mock:
        resume_mock.return_value = {"__interrupt__": [confirm]}
        res = _post(client, "bizsel_biz-2")

    assert res.status_code == 200
    assert resume_mock.call_args.args[1] == "biz-2"
    body = res.json()
    assert body["pending_transaction"]["business_name"] == "Toko Maju Jaya"
    assert "Bisnis: Toko Maju Jaya" in body["message"]


def test_unparseable_business_reply_reshows_the_question(client: TestClient) -> None:
    """Never guess which business the user meant."""
    a, b, c, d, e = _base_patches(OPTIONS, {"kind": "business_selection", "options": OPTIONS})
    with a, b, c, d, e, \
         patch("app.api.v1.chat.resume_business_choice") as resume_mock:
        res = _post(client, "hmm gimana ya")

    assert res.status_code == 200
    resume_mock.assert_not_called()
    assert res.json()["pending_business_choice"] == {"options": OPTIONS}


def test_cancelling_the_business_question_records_nothing(client: TestClient) -> None:
    a, b, c, d, e = _base_patches(OPTIONS, {"kind": "business_selection", "options": OPTIONS})
    with a, b, c, d, e, \
         patch("app.api.v1.chat.resume_business_choice",
               return_value={"business_cancelled": True}) as resume_mock:
        res = _post(client, "bizsel_batal")

    assert res.status_code == 200
    assert resume_mock.call_args.args[1] is None
    assert "dibatalkan" in res.json()["message"]


def test_a_pending_confirmation_no_longer_needs_a_database_row(client: TestClient) -> None:
    """Pause detection reads graph state, so the deflection lasts exactly as
    long as the graph is paused — no orphaned row, no 24-hour TTL (D3)."""
    a, b, c, d, e = _base_patches(OPTIONS, {"kind": "confirmation"})
    with a, b, c, d, e, \
         patch("app.api.v1.chat.capture_graph") as capture_mock, \
         patch("app.api.v1.chat.graph.invoke") as advisory_mock:
        res = _post(client, "jual kopi 10rb")

    assert "menunggu konfirmasi" in res.json()["message"]
    capture_mock.invoke.assert_not_called()
    advisory_mock.assert_not_called()
