from fastapi.testclient import TestClient


def test_audit_api_is_disabled(client: TestClient) -> None:
    """Jejak Audit is retained internally but is not an exposed product API."""
    response = client.get(
        "/api/v1/audit",
        params={"workspace_id": "00000000-0000-0000-0000-000000000001"},
        headers={"Authorization": "Bearer unused"},
    )

    assert response.status_code == 404
