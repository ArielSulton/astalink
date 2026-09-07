"""Tests for the transaction-capture subgraph."""
from app.agents.transaction_capture.graph import build_capture_graph


def test_build_capture_graph_compiles_with_expected_nodes() -> None:
    g = build_capture_graph()
    node_names = set(g.get_graph().nodes.keys())
    assert {"extract", "resolve_business", "stage", "confirm", "persist", "rejected"} <= node_names


def test_route_after_extract_ends_on_gate_failure() -> None:
    from app.agents.transaction_capture.graph import _route_after_extract
    assert _route_after_extract({"gate_failed": True}) == "__end__"
    assert _route_after_extract({"gate_failed": False}) == "resolve_business"


def test_route_after_resolve_ends_when_the_user_cancelled() -> None:
    """Batalkan on the business card must end the run BEFORE stage_node, so
    no pending row is ever written and there is nothing to clean up."""
    from app.agents.transaction_capture.graph import _route_after_resolve
    assert _route_after_resolve({"business_cancelled": True}) == "__end__"
    assert _route_after_resolve({"business_cancelled": False}) == "stage"


def test_route_after_confirm_branches_on_confirmed() -> None:
    from app.agents.transaction_capture.graph import _route_after_confirm
    assert _route_after_confirm({"confirmed": True}) == "persist"
    assert _route_after_confirm({"confirmed": False}) == "rejected"
