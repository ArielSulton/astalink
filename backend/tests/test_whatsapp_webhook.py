import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_webhook_get_verifies_subscription(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "appsec")
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "secret123",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_get_rejects_wrong_verify_token(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "secret123")
    import importlib, app.core.config
    importlib.reload(app.core.config)

    resp = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong",
                "hub.challenge": "12345"},
    )
    assert resp.status_code == 403


def test_webhook_post_dedupes_replays(client: TestClient, monkeypatch) -> None:
    """Same Meta message_id arriving twice must invoke the graph at most once."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.MSG-ABC",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "alokasikan ke BBCA"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    # First call: row doesn't exist — insert succeeds.
    # Second call: insert fails on PK conflict — caught and treated as already-seen.
    insert_mock = fake_admin.table.return_value.insert
    insert_mock.return_value.execute.side_effect = [
        MagicMock(data=[{}]),       # first
        Exception("duplicate key"),  # second
    ]
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    invoke_mock = MagicMock(return_value={"messages": [], "transactions": [],
                                          "audit_id": "abc", "user_approval": "approved"})

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", invoke_mock), \
         patch("app.api.v1.whatsapp.send_text"):
        # First delivery
        r1 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})
        # Replay
        r2 = client.post("/api/v1/whatsapp/webhook", content=body,
                         headers={"X-Hub-Signature-256": sig,
                                  "Content-Type": "application/json"})

    assert r1.status_code == 200 and r2.status_code == 200
    assert invoke_mock.call_count == 1, "graph must run exactly once for a replayed message_id"
