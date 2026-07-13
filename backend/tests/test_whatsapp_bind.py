import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _fake_admin(*, pending_row, ws_owned: bool, insert_raises: bool = False) -> MagicMock:
    """Build a fake Supabase admin client wired for the /whatsapp/bind chains:
    - select on whatsapp_pending_codes: .select().eq().execute()
    - select on workspaces (via assert_workspace_owned): .select().eq().eq().limit().execute()
    - insert on whatsapp_bindings: .insert().execute()
    - update on whatsapp_pending_codes: .update().eq().execute()
    """
    fake = MagicMock()
    fake.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[pending_row] if pending_row is not None else []
    )
    fake.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "ws-1"}] if ws_owned else []
    )
    if insert_raises:
        fake.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key")
    else:
        fake.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
    return fake


def _pending_row(*, phone="6281234567890", expires_in_hours=1, consumed=False) -> dict:
    return {
        "code": "abc123",
        "phone_e164": phone,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat(),
        "consumed_at": datetime.now(timezone.utc).isoformat() if consumed else None,
    }


def test_bind_success(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=_pending_row(), ws_owned=True)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "abc123", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 204
    fake_admin.table.return_value.insert.assert_called_once_with({
        "user_id": user["sub"],
        "phone_e164": "6281234567890",
        "workspace_id": "ws-1",
    })
    fake_admin.table.return_value.update.assert_called_once()
    update_kwargs = fake_admin.table.return_value.update.call_args[0][0]
    assert "consumed_at" in update_kwargs


def test_bind_code_not_found(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=None, ws_owned=True)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "nope", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 404


def test_bind_code_expired(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=_pending_row(expires_in_hours=-1), ws_owned=True)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "abc123", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 410


def test_bind_code_already_consumed(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=_pending_row(consumed=True), ws_owned=True)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "abc123", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 410


def test_bind_workspace_not_owned(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=_pending_row(), ws_owned=False)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "abc123", "workspace_id": "not-mine"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 403


def test_bind_phone_already_bound(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = _fake_admin(pending_row=_pending_row(), ws_owned=True, insert_raises=True)

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin):
        resp = client.post(
            "/api/v1/whatsapp/bind",
            json={"code": "abc123", "workspace_id": "ws-1"},
            headers={"Authorization": "Bearer x"},
        )

    assert resp.status_code == 409
