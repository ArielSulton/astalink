import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def test_create_business_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/business", json={"name": "Toko A", "workspace_id": "ws-1"})
    assert resp.status_code == 401


def test_create_business_rejects_workspace_not_owned_by_user(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.business.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/business",
            json={"name": "Toko A", "workspace_id": "ws-not-mine"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 403


def test_create_business_succeeds_for_owned_workspace(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()

    ownership_query = MagicMock()
    ownership_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "ws-1"}])

    insert_query = MagicMock()
    insert_query.insert.return_value.execute.return_value = MagicMock(data=[{
        "id": "biz-1", "name": "Toko A", "industry": None,
        "description": None, "created_at": "2026-01-01T00:00:00+00:00",
    }])

    def _table(name: str):
        return ownership_query if name == "workspaces" else insert_query

    fake_admin.table.side_effect = _table

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.business.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/business",
            json={"name": "Toko A", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Toko A"


def test_list_businesses_requires_workspace_id_query_param(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    with patch("app.api.deps.verify_token", return_value=mock_user):
        resp = client.get("/api/v1/business", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 422


def test_get_business_returns_404_when_not_found(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[])

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.business.get_admin_client", return_value=fake_admin):
        resp = client.get("/api/v1/business/nonexistent-id", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 404


def test_add_financial_record_upserts_by_period(client: TestClient) -> None:
    mock_user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()

    business_query = MagicMock()
    business_query.select.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "biz-1", "workspace_id": "ws-1", "name": "Toko A",
                          "industry": None, "description": None,
                          "created_at": "2026-01-01T00:00:00+00:00"}])

    ownership_query = MagicMock()
    ownership_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = \
        MagicMock(data=[{"id": "ws-1"}])

    records_query = MagicMock()
    records_query.upsert.return_value.execute.return_value = MagicMock(data=[{
        "id": "rec-1", "period_year": 2024, "aset": 100.0, "omset": 200.0, "profit": 30.0,
    }])

    def _table(name: str):
        if name == "businesses":
            return business_query
        if name == "workspaces":
            return ownership_query
        return records_query

    fake_admin.table.side_effect = _table

    with patch("app.api.deps.verify_token", return_value=mock_user), \
         patch("app.api.v1.business.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/business/biz-1/financials",
            json={"period_year": 2024, "aset": 100.0, "omset": 200.0, "profit": 30.0},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    assert resp.json()["period_year"] == 2024
