"""Rejection Handler — when Legal status is rejected (or rejected_after_max_revisions),
emit a user-facing message that includes alternative actions, never bare 'no'."""
from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.state import AgentState


def rejection_handler(state: AgentState) -> AgentState:
    citations = state.get("legal_citations") or []
    cite_lines = [
        f"- {c.get('source')} Pasal {c.get('pasal')} ayat ({c.get('ayat')}): {c.get('span', '')}"
        for c in citations
    ] or ["(tidak ada kutipan yang dapat dibuktikan)"]

    msg = (
        "Alokasi yang Anda usulkan tidak dapat dilanjutkan karena pembatasan regulasi:\n"
        + "\n".join(cite_lines)
        + "\n\nSaran alternatif:\n"
        "- Pertimbangkan ETF sektor serupa yang tidak terbatas untuk investor ritel.\n"
        "- Bagi alokasi ke instrumen pendapatan tetap (obligasi pemerintah).\n"
        "- Hubungi ahli keuangan untuk skenario yang membutuhkan struktur khusus."
    )
    return {"messages": [*state.get("messages", []), AIMessage(content=msg)]}
