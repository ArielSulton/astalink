import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_create_workspace_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/workspaces", json={"name": "Personal", "type": "personal"})
    assert resp.status_code == 401


def test_create_workspace_returns_seeded_cash_balance(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{
        "id": "ws-1", "name": "Personal", "type": "personal",
        "cash_balance": 1_000_000_000,
    }])

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.workspaces.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/workspaces",
            json={"name": "Personal", "type": "personal"},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == 1_000_000_000
