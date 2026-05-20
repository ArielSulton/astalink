import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    # Deferred import: keeps pytest collection cheap and avoids triggering
    # heavy graph compilation for tests that only need a few unit-level imports.
    from app.main import app
    return TestClient(app)
