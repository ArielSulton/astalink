import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.state import LegalStatus, new_state


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
    assert data["requires_approval"] is True
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
