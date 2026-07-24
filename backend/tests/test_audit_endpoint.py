import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _detail_mocks(
    fake_admin: MagicMock,
    audit_row: dict | None,
    plan_rows: list[dict],
    tx_rows: list[dict],
) -> None:
    """Wire the three query chains used by GET /audit/{id}."""
    # audit_log: .table().select().eq().single().execute()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .single.return_value.execute.return_value) = MagicMock(data=audit_row)
    # allocation_plans: .table().select().eq().order().limit().execute()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .order.return_value.limit.return_value.execute.return_value) = MagicMock(data=plan_rows)
    # transactions: .table().select().eq().execute()
    (fake_admin.table.return_value.select.return_value.eq.return_value
     .execute.return_value) = MagicMock(data=tx_rows)


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


def test_list_audit_rejects_malformed_workspace_id(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get("/api/v1/audit?workspace_id=not-a-uuid",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 422
    fake_admin.table.assert_not_called()


def test_get_audit_detail_assembles_plan_and_transactions(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    _detail_mocks(
        fake_admin,
        audit_row={"audit_id": audit_id, "status": "approved",
                   "intent": "allocate_stocks", "workspace_id": "w",
                   "created_at": "2026-05-04T00:00:00Z",
                   "completed_at": "2026-05-04T00:01:00Z",
                   "user_id": user["sub"]},
        plan_rows=[{"plan_json": {"weights": [{"ticker": "BBCA", "weight": 0.5}], "cash": 1000},
                    "legal_status": "approved", "legal_citations": []}],
        tx_rows=[{"ticker": "BBCA", "side": "buy", "quantity": 5, "status": "filled",
                  "broker_ref": "SBX-1"}],
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


def test_get_audit_detail_uses_latest_plan_for_revised_run(client: TestClient) -> None:
    """Revised runs insert several allocation_plans rows for one audit_id.
    The endpoint must order by created_at desc and take the newest — never
    .single(), which raises APIError on multiple rows."""
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    _detail_mocks(
        fake_admin,
        audit_row={"audit_id": audit_id, "status": "awaiting_approval",
                   "intent": "allocate_stocks", "workspace_id": "w",
                   "created_at": "2026-05-04T00:00:00Z",
                   "completed_at": None, "user_id": user["sub"]},
        # DB returns rows already ordered desc; limit(1) keeps only the newest.
        plan_rows=[{"plan_json": {"weights": [{"ticker": "TLKM", "weight": 1.0}], "cash": 42},
                    "legal_status": "approved",
                    "legal_citations": [{"source": "OJK", "pasal": "2"}]}],
        tx_rows=[],
    )

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.audit.get_admin_client", return_value=fake_admin):
        resp = client.get(f"/api/v1/audit/{audit_id}",
                          headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["allocation_plan"]["cash"] == 42
    assert body["legal_status"] == "approved"
    # The revision-safe query shape: newest-first, one row.
    plan_chain = fake_admin.table.return_value.select.return_value.eq.return_value
    plan_chain.order.assert_called_once_with("created_at", desc=True)
    plan_chain.order.return_value.limit.assert_called_once_with(1)


def test_get_audit_detail_rejects_other_users_run(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    audit_id = "a1"

    fake_admin = MagicMock()
    _detail_mocks(
        fake_admin,
        audit_row={"audit_id": audit_id, "status": "approved", "intent": "x",
                   "workspace_id": "w", "created_at": "2026-05-04T00:00:00Z",
                   "completed_at": None, "user_id": "SOMEONE-ELSE"},
        plan_rows=[],
        tx_rows=[],
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
    _detail_mocks(
        fake_admin,
        audit_row={"audit_id": audit_id, "status": "rejected",
                   "intent": "allocate_stocks", "workspace_id": "w",
                   "created_at": "2026-05-04T00:00:00Z",
                   "completed_at": None, "user_id": user["sub"]},
        plan_rows=[],  # run stopped before the optimizer
        tx_rows=[],
    )

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
