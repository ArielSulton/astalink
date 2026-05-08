import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_legal_check_endpoint_returns_decision(client: TestClient) -> None:
    audit_id = str(uuid.uuid4())
    user = {"sub": str(uuid.uuid4()), "email": "u@test.com"}

    fake_state_update = {
        "legal_status": "partial",
        "legal_citations": [{
            "source": "OJK", "pasal": "3", "ayat": "1",
            "chunk_id": "OJK-3-1-_-0", "span": "dilarang"}],
    }

    with patch("app.api.deps.verify_token", return_value=user), \
         patch("app.api.v1.legal.legal_node", return_value=fake_state_update):
        resp = client.post(
            "/api/v1/legal/check",
            json={
                "audit_id": audit_id,
                "workspace_id": str(uuid.uuid4()),
                "allocation_plan": {
                    "weights": [{"ticker": "GGRM", "weight": 1.0}],
                    "cash": 10_000_000,
                },
            },
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["legal_status"] == "partial"
    assert body["legal_citations"][0]["pasal"] == "3"


def test_legal_check_endpoint_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/legal/check", json={})
    assert resp.status_code == 401
