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


def _fake_audit_admin(audit_id: str, user_sub: str) -> MagicMock:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"audit_id": audit_id, "status": "awaiting_approval", "workspace_id": "w",
              "user_id": user_sub}
    )
    return fake_admin


def test_approve_records_acknowledgement_without_resuming_any_graph(client: TestClient) -> None:
    """Advisory mode: n6_hitl/n7_execute aren't wired into graph.py, so there
    is never a paused run to resume. approve() must not touch the graph at
    all — it only flips audit_log.status to record the user's decision."""
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-1"
    fake_admin = _fake_audit_admin(audit_id, user["sub"])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.approvals.verify_user_pin"):
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/approve",
            json={"pin": "1234"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"audit_id": audit_id, "status": "acknowledged"}
    fake_admin.table.return_value.update.assert_called_once()
    assert fake_admin.table.return_value.update.call_args[0][0]["status"] == "acknowledged"


def test_reject_records_decline_without_resuming_any_graph(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-2"
    fake_admin = _fake_audit_admin(audit_id, user["sub"])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/reject",
            json={},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"audit_id": audit_id, "status": "declined"}
    fake_admin.table.return_value.update.assert_called_once()
    assert fake_admin.table.return_value.update.call_args[0][0]["status"] == "declined"


def test_approve_without_pin_returns_400(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-3"
    fake_admin = _fake_audit_admin(audit_id, user["sub"])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin):
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/approve",
            json={},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 400
