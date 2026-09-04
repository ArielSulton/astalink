"""Tests for the transaction-capture subgraph."""
from app.agents.transaction_capture.graph import build_capture_graph


def test_build_capture_graph_compiles_with_expected_nodes() -> None:
    g = build_capture_graph()
    node_names = set(g.get_graph().nodes.keys())
    assert {"extract", "confirm", "persist", "rejected"} <= node_names


def test_route_after_extract_ends_on_gate_failure() -> None:
    from app.agents.transaction_capture.graph import _route_after_extract
    assert _route_after_extract({"gate_failed": True}) == "__end__"
    assert _route_after_extract({"gate_failed": False}) == "confirm"


def test_route_after_confirm_branches_on_confirmed() -> None:
    from app.agents.transaction_capture.graph import _route_after_confirm
    assert _route_after_confirm({"confirmed": True}) == "persist"
    assert _route_after_confirm({"confirmed": False}) == "rejected"
