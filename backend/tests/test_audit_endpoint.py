import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_list_audit_returns_all_statuses_for_user_workspace(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    workspace_id = str(uuid.uuid4())

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .eq.return_value.order.return_value.execute.return_value) = MagicMock(
        data=[
            {"audit_id": "a1", "intent": "allocate_stocks", "status": "approved",
             "created_at": "2026-05-04T00:00:00Z", "completed_at": "2026-05-04T00:01:00Z",
             "workspace_id": workspace_id, "user_id": user["sub"]},
            {"audit_id": "a2", "intent": "allocate_stocks", "status": "rejected",
             "created_at": "2026-05-03T00:00:00Z", "completed_at": None,
             "workspace_id": workspace_id, "user_id": user["sub"]},
        ]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit?workspace_id={workspace_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["audits"]) == 2
    statuses = {a["status"] for a in body["audits"]}
    assert statuses == {"approved", "rejected"}


def test_get_audit_detail_assembles_plan_and_transactions(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = [
        MagicMock(data={"audit_id": audit_id, "status": "approved",
                        "intent": "allocate_stocks", "workspace_id": "w",
                        "created_at": "2026-05-04T00:00:00Z",
                        "completed_at": "2026-05-04T00:01:00Z",
                        "user_id": user["sub"]}),
        MagicMock(data={"plan_json": {"weights": [{"ticker": "BBCA", "weight": 0.5}], "cash": 1000},
                        "legal_status": "approved", "legal_citations": []}),
    ]
    # transactions: .table().select().eq().execute() (no .single)
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(
        data=[{"ticker": "BBCA", "side": "buy", "quantity": 5, "status": "filled",
               "broker_ref": "SBX-1"}]
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_id"] == audit_id
    assert body["allocation_plan"]["cash"] == 1000
    assert body["legal_status"] == "approved"
    assert len(body["transactions"]) == 1
    assert body["transactions"][0]["ticker"] == "BBCA"


def test_get_audit_detail_rejects_other_users_run(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.return_value) = MagicMock(
        data={"audit_id": audit_id, "status": "approved", "intent": "x",
              "workspace_id": "w", "created_at": "2026-05-04T00:00:00Z",
              "completed_at": None, "user_id": "SOMEONE-ELSE"}
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 404


def test_get_audit_detail_tolerates_missing_plan(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = [
        MagicMock(data={"audit_id": audit_id, "status": "rejected",
                        "intent": "allocate_stocks", "workspace_id": "w",
                        "created_at": "2026-05-04T00:00:00Z",
                        "completed_at": None, "user_id": user["sub"]}),
        MagicMock(data=None),  # no allocation_plans row
    ]
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["allocation_plan"] is None
    assert body["transactions"] == []


def test_get_audit_detail_returns_404_when_single_raises(client: TestClient) -> None:
    """Real supabase-py raises APIError when .single() matches no row —
    the endpoint must map that to 404, not 500."""
    from postgrest.exceptions import APIError

    user = {"sub": str(uuid.uuid4())}

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = APIError(
        {"message": "JSON object requested, multiple (or no) rows returned",
         "code": "PGRST116", "hint": None, "details": None}
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get("/api/v1/audit/missing-id",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 404


def test_get_audit_detail_tolerates_plan_lookup_apierror(client: TestClient) -> None:
    """A run that stopped before the optimizer has no allocation_plans row;
    the real client raises APIError on .single() — detail must still be 200."""
    from postgrest.exceptions import APIError

    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.side_effect) = [
        MagicMock(data={"audit_id": audit_id, "status": "in_progress",
                        "intent": "clarify", "workspace_id": "w",
                        "created_at": "2026-05-04T00:00:00Z",
                        "completed_at": None, "user_id": user["sub"]}),
        APIError({"message": "no rows", "code": "PGRST116",
                  "hint": None, "details": None}),
    ]
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    assert resp.json()["allocation_plan"] is None
