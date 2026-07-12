import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


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


def _post_wa_message(client: TestClient, monkeypatch, *, message_id: str, text: str,
                     final_state: dict) -> str:
    """Send one signed WhatsApp webhook payload and return the text passed to
    send_text (an AttributeError is raised if send_text was never called)."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": message_id,
            "from": "6281234567890",
            "type": "text",
            "text": {"body": text},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke", return_value=final_state), \
         patch("app.api.v1.whatsapp.send_text") as send_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})
        assert resp.status_code == 200
        send_mock.assert_called_once()
        return send_mock.call_args.kwargs["body"]


def test_whatsapp_reply_for_informational_intent_has_no_approval_link(monkeypatch, client: TestClient) -> None:
    """Before this fix, ANY reply with user_approval is None — including
    EXPLAIN/evaluate_business/risk_review answers, which never touch HITL —
    was wrongly sent as 'Saya sudah menyiapkan rekomendasi alokasi, review
    & approve di: .../approvals/{audit_id}'. An informational answer must be
    relayed as-is, with no approval link appended."""
    final_state = {
        "audit_id": "audit-explain-1",
        "intent": "explain",
        "messages": [AIMessage(content="RSI (Relative Strength Index) mengukur momentum harga.")],
        "legal_status": None,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.EXPLAIN-1",
                            text="apa itu RSI?", final_state=final_state)

    assert body == "RSI (Relative Strength Index) mengukur momentum harga."
    assert "approvals" not in body.lower()
    assert "rekomendasi alokasi" not in body.lower()


def test_whatsapp_reply_appends_approval_link_when_awaiting_hitl(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus

    final_state = {
        "audit_id": "audit-hitl-1",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": None,
        "transactions": [],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.HITL-1",
                            text="alokasikan 10jt ke BBCA", final_state=final_state)

    assert "Approvals" in body
    assert "audit-hitl-1" in body
    assert body.endswith("/approvals/audit-hitl-1")


def test_whatsapp_reply_appends_audit_link_after_execution(monkeypatch, client: TestClient) -> None:
    from app.agents.state import LegalStatus, UserApproval

    final_state = {
        "audit_id": "audit-exec-1",
        "intent": "allocate_stocks",
        "messages": [],
        "legal_status": LegalStatus.APPROVED,
        "user_approval": UserApproval.APPROVED,
        "transactions": [
            {"ticker": "BBCA", "side": "buy", "quantity": 10, "status": "filled", "broker_ref": "r1"},
        ],
        "errors": [],
    }
    body = _post_wa_message(client, monkeypatch, message_id="wamid.EXEC-1",
                            text="ya, setuju", final_state=final_state)

    assert "BBCA" in body
    assert "berhasil dieksekusi" in body.lower()
    assert body.endswith("/audit/audit-exec-1")


def test_whatsapp_sends_fallback_reply_when_pipeline_raises(monkeypatch, client: TestClient) -> None:
    """Reproduces a live incident: optimizer_node crashed with an unhandled
    TypeError (comparing a string "amount" entity to a float balance), the
    exception propagated all the way up through this webhook handler, the
    request 500'd, and send_text() was never reached — the user saw no
    reply at all with zero indication anything failed. The pipeline must
    never be allowed to fail silently."""
    secret = "appsec"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    import importlib, app.core.config
    importlib.reload(app.core.config)

    payload = {
        "entry": [{"changes": [{"value": {"messages": [{
            "id": "wamid.CRASH-1",
            "from": "6281234567890",
            "type": "text",
            "text": {"body": "rekomendasi invest dana 20 juta rupiah"},
        }]}}]}]
    }
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    fake_admin = MagicMock()
    fake_admin.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    fake_admin.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"user_id": "u1", "workspace_id": "w1"}
    )

    with patch("app.api.v1.whatsapp.get_admin_client", return_value=fake_admin), \
         patch("app.api.v1.whatsapp.graph.invoke",
               side_effect=TypeError("'<' not supported between instances of 'float' and 'str'")), \
         patch("app.api.v1.whatsapp.send_text") as send_mock:
        resp = client.post("/api/v1/whatsapp/webhook", content=body,
                           headers={"X-Hub-Signature-256": sig,
                                    "Content-Type": "application/json"})

    assert resp.status_code == 200
    send_mock.assert_called_once()
    reply = send_mock.call_args.kwargs["body"]
    assert reply
    assert "maaf" in reply.lower()
