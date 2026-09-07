import uuid

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.state import LegalStatus, new_state


@pytest.fixture(autouse=True)
def _no_remembered_business():
    """chat.py asks the capture thread which business it last used, which
    reads the real checkpointer. Default it to "nothing remembered" for every
    test; the ones that care patch it themselves."""
    with patch("app.api.v1.chat.remembered_business_id", return_value=None):
        yield


def _make_fake_admin(owned: bool) -> MagicMock:
    """Return a fake Supabase admin client whose workspace ownership query
    returns data=[{"id": "ws-1"}] (owned=True) or data=[] (owned=False)."""
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"id": "ws-1"}]) if owned else MagicMock(data=[])
    )
    return fake_admin


def test_chat_endpoint_without_auth_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat/",
        json={"message": "Hello", "workspace_id": "ws-1"},
    )
    assert response.status_code == 401


def test_chat_endpoint_delegates_to_main_pipeline(client: TestClient) -> None:
    """`/chat` must run the SAME LangGraph pipeline as `/agent/run` (FR-19) —
    not a separate, stateless Gemini wrapper. Verified by mocking
    `graph.invoke` directly and asserting chat.py builds a proper AgentState
    (thread-scoped, workspace_id present) and formats its reply via
    build_chat_reply (Task 6)."""
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["messages"] = [AIMessage(content="Halo! Ada yang bisa saya bantu?")]
    fake_final_state["_needs_clarification"] = True

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state) as mock_invoke:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Halo! Ada yang bisa saya bantu?"
    assert "thread_id" in data

    mock_invoke.assert_called_once()
    call_args, call_kwargs = mock_invoke.call_args
    initial_state = call_args[0]
    assert initial_state["_user_id"] == "user-123"
    assert initial_state["_workspace_id"] == "ws-1"
    assert initial_state["entities"]["workspace_id"] == "ws-1"
    assert call_kwargs["config"]["configurable"]["thread_id"].startswith("user-123:")
    # _thread_id must be the SAME value the graph is invoked under, so
    # intent_node can persist it to audit_log for approvals.py to resume with.
    assert initial_state["_thread_id"] == call_kwargs["config"]["configurable"]["thread_id"]


def test_chat_endpoint_returns_500_when_pipeline_produces_no_messages(client: TestClient) -> None:
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)
    fake_final_state = new_state()
    fake_final_state["messages"] = []

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state):
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 500


def test_chat_response_carries_audit_and_approval_fields(client: TestClient) -> None:
    """The web chat needs audit_id + requires_approval to render an
    Approvals CTA button under the assistant bubble."""
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["audit_id"] = "audit-abc"
    fake_final_state["intent"] = "allocate_stocks"
    fake_final_state["legal_status"] = LegalStatus.APPROVED
    fake_final_state["messages"] = [AIMessage(content="ok")]

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state):
        response = client.post(
            "/api/v1/chat/",
            json={"message": "alokasikan 20 juta ke BBCA", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["audit_id"] == "audit-abc"
    # Advisory mode (2026-09 concept change): /chat produces reports and
    # recommendations only — no HITL approval, no automatic execution — so
    # chat.py always reports requires_approval=False. This assertion said
    # True and had been failing since that change landed; the audit_id is
    # what the Approvals CTA actually needs.
    assert data["requires_approval"] is False
    assert data["intent"] == "allocate_stocks"


def test_chat_injects_prior_thread_history_into_invoke(client: TestClient) -> None:
    """Follow-up messages must carry the thread's prior conversation so the
    QA node can answer with context (chat.py used to overwrite `messages`
    with just the new HumanMessage every turn)."""
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    prior = [HumanMessage(content="apa itu RSI?"),
             AIMessage(content="RSI adalah indikator momentum.")]
    fake_snapshot = MagicMock()
    fake_snapshot.values = {"messages": prior}

    fake_final_state = new_state()
    fake_final_state["messages"] = [AIMessage(content="Lanjutan jawaban.")]

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.get_state", return_value=fake_snapshot), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state) as mock_invoke:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "kalau dibanding MACD?", "workspace_id": "ws-1",
                  "thread_id": "thread-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    initial_state = mock_invoke.call_args[0][0]
    sent = initial_state["messages"]
    assert [m.content for m in sent] == [
        "apa itu RSI?",
        "RSI adalah indikator momentum.",
        "kalau dibanding MACD?",
    ]


def test_chat_persists_the_actual_reply_text_to_thread_history(client: TestClient) -> None:
    """Live incident: build_chat_reply's output (the report actually shown
    to the user for the allocation path) is computed from final_state on
    every call but is never itself appended to state["messages"] by any
    graph node — only n8_qa's informational path writes a final AIMessage.
    Without persisting it here, a genuine follow-up on the next turn
    ("kenapa alokasi bisnis 0%?") has no report text anywhere in its
    load_thread_history() context to refer back to, and gets misclassified
    as a fresh allocation request instead of a follow-up. update_state must
    be called with the reply actually returned to the client."""
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["messages"] = [HumanMessage(content="alokasikan 10 juta ke BBCA")]
    fake_final_state["intent"] = "allocate_stocks"
    fake_final_state["legal_status"] = "approved"

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state), \
         patch("app.api.v1.chat.graph.update_state") as mock_update_state:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "alokasikan 10 juta ke BBCA", "workspace_id": "ws-1",
                  "thread_id": "thread-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    reply_text = response.json()["message"]

    mock_update_state.assert_called_once()
    _, kwargs = mock_update_state.call_args
    persisted_messages = kwargs["values"]["messages"]
    assert persisted_messages[0].content == "alokasikan 10 juta ke BBCA"
    assert isinstance(persisted_messages[-1], AIMessage)
    assert persisted_messages[-1].content == reply_text
    assert kwargs["config"]["configurable"]["thread_id"].startswith("user-123:")


def test_chat_reply_persistence_failure_does_not_break_the_response(client: TestClient) -> None:
    """update_state is a best-effort side channel — if it throws (DB hiccup,
    etc.), the user must still get their actual answer back."""
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["messages"] = [AIMessage(content="Halo!")]
    fake_final_state["_needs_clarification"] = True

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state), \
         patch("app.api.v1.chat.graph.update_state", side_effect=RuntimeError("db down")):
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Halo!"


def test_chat_history_fetch_failure_degrades_to_single_message(client: TestClient) -> None:
    mock_user = {"sub": "user-123", "email": "test@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["messages"] = [AIMessage(content="ok")]

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.get_state", side_effect=RuntimeError("boom")), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state) as mock_invoke:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-1", "thread_id": "thread-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    sent = mock_invoke.call_args[0][0]["messages"]
    assert len(sent) == 1
    assert sent[0].content == "halo"


def test_chat_rejects_workspace_not_owned_by_user(client: TestClient) -> None:
    """Calling /chat/ with a workspace_id not owned by the authenticated user
    must return 403 and must NOT invoke the graph pipeline."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "user@example.com"}
    fake_admin = _make_fake_admin(owned=False)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke") as mock_graph:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-not-mine"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 403
    mock_graph.assert_not_called()


def test_chat_allows_owned_workspace(client: TestClient) -> None:
    """Calling /chat/ with an owned workspace must reach graph.invoke."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "user@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final_state = new_state()
    fake_final_state["messages"] = [AIMessage(content="Halo!")]

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.graph.invoke", return_value=fake_final_state) as mock_graph:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "halo", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    mock_graph.assert_called_once()


def test_chat_photo_routes_to_capture_not_advisory_graph(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value=None), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.chat.graph.invoke") as advisory_invoke_mock:
        fake_capture_graph.invoke.return_value = {
            "__interrupt__": [type("I", (), {"value": {
                "transaction_id": "txn-1", "item_description": "Struk belanja",
                "amount": 50000.0, "type": "expense", "plausibility_flag": False,
            }})()],
        }
        response = client.post(
            "/api/v1/chat/",
            json={"message": "", "workspace_id": "ws-1",
                  "photo_base64": "ZmFrZS1qcGVn", "photo_mime_type": "image/jpeg"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pending_transaction"]["item_description"] == "Struk belanja"
    advisory_invoke_mock.assert_not_called()
    sent = fake_capture_graph.invoke.call_args.args[0]
    assert sent["source"] == "web_photo"
    # The graph resolves the business itself now (it may have to ask), so the
    # caller hands it the candidates rather than a pre-picked id.
    assert sent["candidate_businesses"] == [{"id": "biz-1", "name": "Warung Kopi"}]
    assert sent["business_id"] is None  # nothing remembered on a fresh thread


def test_chat_ambiguous_text_routes_to_capture(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value=None), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.looks_like_transaction", return_value=True), \
         patch("app.api.v1.chat.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.chat.graph.invoke") as advisory_invoke_mock:
        fake_capture_graph.invoke.return_value = {"gate_failed": True, "extraction": None}
        response = client.post(
            "/api/v1/chat/",
            json={"message": "jual nasi goreng 15rb", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    advisory_invoke_mock.assert_not_called()
    assert fake_capture_graph.invoke.call_args.args[0]["source"] == "web_text"


def test_chat_pending_transaction_resumes_via_txn_marker(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value={"kind": "confirmation"}), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.resume_transaction", return_value={"confirmed": True}) as resume_mock, \
         patch("app.api.v1.chat.graph.invoke") as advisory_invoke_mock:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "txn_ya", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    resume_mock.assert_called_once()
    assert resume_mock.call_args.args[1] == "confirmed"
    advisory_invoke_mock.assert_not_called()


def test_chat_composition_reply_not_swallowed_when_transaction_also_pending(client: TestClient) -> None:
    """The exact I4 collision, ported: a plain 'ya' while BOTH a pending
    transaction and a pending composition approval exist must not silently
    resolve the transaction — it's ambiguous and must be deflected."""
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value={"kind": "confirmation"}), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value="audit-1"), \
         patch("app.api.v1.chat.resume_transaction") as resume_txn_mock, \
         patch("app.api.v1.chat.resume_composition") as resume_comp_mock, \
         patch("app.api.v1.chat.graph.invoke") as advisory_invoke_mock:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "ya", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    resume_txn_mock.assert_not_called()
    resume_comp_mock.assert_not_called()
    advisory_invoke_mock.assert_not_called()
    body = response.json()["message"].lower()
    assert "transaksi" in body and "alokasi" in body


def test_chat_photo_without_single_business_requires_business_setup(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[]), \
         patch("app.api.v1.chat.pending_interrupt", return_value=None), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.capture_graph") as fake_capture_graph:
        response = client.post(
            "/api/v1/chat/",
            json={"message": "", "workspace_id": "ws-1",
                  "photo_base64": "ZmFrZS1qcGVn", "photo_mime_type": "image/jpeg"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["requires_business_setup"] is True
    fake_capture_graph.invoke.assert_not_called()


def test_chat_allocation_request_with_business_reaches_advisory_graph(client: TestClient) -> None:
    """business_id being set must not force every message through the
    capture path — an ordinary allocation request must still reach the
    advisory graph when looks_like_transaction correctly says no."""
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    advisory_final = {"audit_id": "a1", "intent": "allocate_capital",
                      "messages": [AIMessage(content="ok")], "legal_status": None,
                      "user_approval": None, "transactions": [], "errors": []}

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value=None), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.looks_like_transaction", return_value=False), \
         patch("app.api.v1.chat.capture_graph") as fake_capture_graph, \
         patch("app.api.v1.chat.graph.invoke", return_value=advisory_final):
        response = client.post(
            "/api/v1/chat/",
            json={"message": "alokasikan 20 juta ke BBCA", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    fake_capture_graph.invoke.assert_not_called()


def test_chat_capture_exception_returns_graceful_message_not_500(client: TestClient) -> None:
    mock_user = {"sub": "user-1", "email": "t@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.chat.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.chat.list_businesses", return_value=[{"id": "biz-1", "name": "Warung Kopi"}]), \
         patch("app.api.v1.chat.pending_interrupt", return_value=None), \
         patch("app.api.v1.chat.find_pending_composition_audit", return_value=None), \
         patch("app.api.v1.chat.looks_like_transaction", return_value=True), \
         patch("app.api.v1.chat.capture_graph") as fake_capture_graph:
        fake_capture_graph.invoke.side_effect = Exception("db write failed")
        response = client.post(
            "/api/v1/chat/",
            json={"message": "jual nasi goreng 15rb", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    assert "maaf" in response.json()["message"].lower()
