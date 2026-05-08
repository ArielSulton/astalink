import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_set_pin_creates_row(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    fake_admin = MagicMock()
    fake_admin.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{}])

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.pin.get_admin_client", return_value=fake_admin):
        resp = client.post("/api/v1/users/me/pin", json={"pin": "123456"},
                           headers={"Authorization": "Bearer x"})

    assert resp.status_code == 204
    fake_admin.table.assert_called_with("pin_codes")


def test_set_pin_rejects_short_pin(client: TestClient) -> None:
    user = {"sub": str(uuid.uuid4())}
    with patch("app.api.deps.verify_token", return_value=user):
        resp = client.post("/api/v1/users/me/pin", json={"pin": "12"},
                           headers={"Authorization": "Bearer x"})
    assert resp.status_code == 422
