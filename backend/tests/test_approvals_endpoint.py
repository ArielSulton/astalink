import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_list_approvals_returns_pending_for_user_workspace(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    workspace_id = str(uuid.uuid4())

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[
            {"audit_id": "a1", "intent": "allocate_stocks", "status": "awaiting_approval",
             "payload": {}, "created_at": "2026-05-04T00:00:00Z", "workspace_id": workspace_id},
        ]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/approvals?workspace_id={workspace_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["approvals"]) == 1
    assert body["approvals"][0]["audit_id"] == "a1"


def test_get_approval_returns_full_plan(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = [
        MagicMock(data={"audit_id": audit_id, "status": "awaiting_approval",
                        "payload": {}, "intent": "allocate_stocks",
                        "workspace_id": "w", "user_id": user["sub"]}),
        MagicMock(data={"plan_json": {"weights": [], "cash": 0},
                        "legal_status": "approved", "legal_citations": []}),
    ]

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/approvals/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"] == audit_id
    assert body["plan_json"] is not None
