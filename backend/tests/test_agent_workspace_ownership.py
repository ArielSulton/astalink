"""Tests that /api/v1/agent/run verifies workspace ownership before invoking
the graph pipeline — guarding against the authorization bypass where any
authenticated user could read another user's workspace data via the
service-role admin client inside the agent nodes."""
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.agents.state import new_state


def _make_fake_admin(owned: bool) -> MagicMock:
    """Return a fake Supabase admin client whose workspace ownership query
    returns data=[{"id": "ws-1"}] (owned=True) or data=[] (owned=False)."""
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        MagicMock(data=[{"id": "ws-1"}]) if owned else MagicMock(data=[])
    )
    return fake_admin


def test_run_agent_rejects_unowned_workspace(client: TestClient) -> None:
    """Calling /agent/run with a workspace_id not owned by the authenticated
    user must return 403 and must NOT invoke the graph pipeline."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "user@example.com"}
    fake_admin = _make_fake_admin(owned=False)

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.agent.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.agent.graph.invoke") as mock_graph:
        resp = client.post(
            "/api/v1/agent/run",
            json={"message": "hello", "workspace_id": "ws-not-mine"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 403
    mock_graph.assert_not_called()


def test_run_agent_allows_owned_workspace(client: TestClient) -> None:
    """Calling /agent/run with a workspace the user owns must reach
    graph.invoke (ownership passes) and return 200."""
    mock_user = {"sub": str(uuid.uuid4()), "email": "user@example.com"}
    fake_admin = _make_fake_admin(owned=True)

    fake_final = new_state()
    fake_final["audit_id"] = "audit-42"
    fake_final["messages"] = []

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.agent.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.agent.graph.invoke", return_value=fake_final) as mock_graph:
        resp = client.post(
            "/api/v1/agent/run",
            json={"message": "hello", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    mock_graph.assert_called_once()
