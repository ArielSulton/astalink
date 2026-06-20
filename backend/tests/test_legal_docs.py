import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_DOCS = [
    {
        "id": "aaaa-1111",
        "source": "OJK",
        "title": "POJK Nomor 3 Tahun 2021",
        "version": "2021",
        "indexed_at": "2026-01-01T00:00:00+00:00",
    }
]


def test_list_documents_returns_list():
    mock_result = MagicMock()
    mock_result.data = MOCK_DOCS
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.order.return_value.execute.return_value = mock_result

    with patch("app.api.v1.legal.get_admin_client", return_value=mock_sb):
        resp = client.get("/api/v1/legal/documents")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["source"] == "OJK"


def test_upload_rejects_non_pdf():
    fake_token = "fake-token"
    mock_user = {"sub": "user-123"}
    with patch("app.api.deps.verify_token", return_value=mock_user):
        resp = client.post(
            "/api/v1/legal/documents/upload",
            files={"file": ("document.txt", b"plain text", "text/plain")},
            data={"source": "user", "title": "Test"},
            headers={"Authorization": f"Bearer {fake_token}"},
        )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]
