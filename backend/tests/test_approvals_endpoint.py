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


def _fake_audit_admin(audit_id: str, user_sub: str, thread_id: str | None) -> MagicMock:
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"audit_id": audit_id, "status": "awaiting_approval", "workspace_id": "w",
              "user_id": user_sub, "thread_id": thread_id}
    )
    return fake_admin


def test_approve_resumes_using_audits_stored_thread_id_not_audit_id(client: TestClient) -> None:
    """Live incident: approve/reject used to resume the graph under
    thread_id=audit_id, which never matches the real thread any entry point
    invoked under (chat.py/agent.py/whatsapp.py each build a different
    format) — silently starting a fresh, empty run instead of resuming the
    real paused one. Must resume under the audit's stored thread_id."""
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-1"
    real_thread_id = "user-xyz:thread-real"
    fake_admin = _fake_audit_admin(audit_id, user["sub"], real_thread_id)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.approvals.verify_user_pin"), \
         patch("app.api.v1.approvals.graph.invoke", return_value={"transactions": []}) as mock_invoke:
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/approve",
            json={"pin": "1234"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 200
    mock_invoke.assert_called_once()
    assert mock_invoke.call_args.kwargs["config"]["configurable"]["thread_id"] == real_thread_id


def test_reject_resumes_using_audits_stored_thread_id_not_audit_id(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-2"
    real_thread_id = "wa-628-w1"
    fake_admin = _fake_audit_admin(audit_id, user["sub"], real_thread_id)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.approvals.graph.invoke", return_value={}) as mock_invoke:
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/reject",
            json={},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 200
    mock_invoke.assert_called_once()
    assert mock_invoke.call_args.kwargs["config"]["configurable"]["thread_id"] == real_thread_id


def test_approve_without_recorded_thread_id_returns_409(client: TestClient) -> None:
    """An audit_log row created before the thread_id fix (or if the write
    somehow failed) has no thread_id — resuming under any guessed value
    would silently create an unrelated empty run, so this must fail loudly
    instead of pretending to succeed."""
    user = {"sub": str(uuid.uuid4())}
    audit_id = "audit-3"
    fake_admin = _fake_audit_admin(audit_id, user["sub"], None)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.approvals.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.approvals.verify_user_pin"), \
         patch("app.api.v1.approvals.graph.invoke") as mock_invoke:
        resp = client.post(
            f"/api/v1/approvals/{audit_id}/approve",
            json={"pin": "1234"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 409
    mock_invoke.assert_not_called()
