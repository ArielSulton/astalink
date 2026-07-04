import time
from fastapi.testclient import TestClient


def test_metrics_endpoint_exposes_prometheus_format(client: TestClient) -> None:
    # Trigger at least one request so HTTP histograms have data
    client.get("/api/v1/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    # Default instrumentator metrics
    assert "http_request_duration_seconds" in text
    # AstaLink custom metrics
    assert "astalink_node_duration_seconds" in text
    assert "astalink_legal_status_total" in text
    assert "astalink_revision_count" in text


def test_track_node_duration_decorator_records_histogram() -> None:
    from app.core.metrics import track_node_duration
    from prometheus_client import REGISTRY

    @track_node_duration("test_node")
    def some_node(state):
        time.sleep(0.01)
        return state

    some_node({})
    samples = [s for m in REGISTRY.collect() for s in m.samples
               if s.name.startswith("astalink_node_duration_seconds")
               and s.labels.get("node") == "test_node"]
    # Histogram emits _count, _sum, _bucket
    assert any(s.name == "astalink_node_duration_seconds_count" for s in samples)


def test_record_legal_status_increments_counter() -> None:
    from app.core.metrics import record_legal_status
    from prometheus_client import REGISTRY

    record_legal_status("approved")
    record_legal_status("approved")
    record_legal_status("rejected")

    samples = {(s.labels.get("status"),): s.value for m in REGISTRY.collect()
               for s in m.samples if s.name == "astalink_legal_status_total"}
    assert samples.get(("approved",), 0) >= 2
    assert samples.get(("rejected",), 0) >= 1


def test_record_checkpointer_degraded_increments_counter() -> None:
    from app.core.metrics import record_checkpointer_degraded
    from prometheus_client import REGISTRY

    before = next((s.value for m in REGISTRY.collect() for s in m.samples
                   if s.name == "astalink_checkpointer_degraded_total"), 0.0)

    record_checkpointer_degraded()

    after = next((s.value for m in REGISTRY.collect() for s in m.samples
                  if s.name == "astalink_checkpointer_degraded_total"), 0.0)
    assert after == before + 1
