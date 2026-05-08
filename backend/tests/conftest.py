import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    # Deferred import: importing app.main eagerly would pull in app.agents.graph
    # -> market_node -> talib, which is unavailable on dev machines that don't
    # have the C library installed.  Skip gracefully instead of erroring so that
    # tests using this fixture behave the same as the graph/market tests.
    pytest.importorskip("talib")
    from app.main import app
    return TestClient(app)
