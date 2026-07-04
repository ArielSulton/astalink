from app.agents.state import LegalStatus, new_state


def test_rejection_handler_appends_alternatives_message() -> None:
    from app.agents.rejection import rejection_handler
    state = new_state()
    state["legal_status"] = LegalStatus.REJECTED
    state["legal_citations"] = [{"source": "OJK", "pasal": "3", "ayat": "1",
                                 "chunk_id": "x", "span": "dilarang"}]
    update = rejection_handler(state)
    msgs = update["messages"]
    assert msgs and "tidak dapat" in msgs[-1].content.lower()
