"""Q&A Node (N8) — direct-answer path for pure informational questions.

When N1 classifies a message as EXPLAIN there is nothing to allocate,
optimize, or legally validate — running the full analyst → optimizer →
legal → HITL pipeline would only burn latency/LLM cost and pollute the
audit/approvals surface. This node answers the question directly with
Gemini and the run ends.

For regulation-flavoured questions it grounds the answer in the same
hybrid retriever the Legal node uses; retrieval failure degrades to an
ungrounded answer instead of failing the run."""
from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration

log = logging.getLogger(__name__)

SYSTEM = """\
Kamu adalah asisten keuangan Astalink untuk investor saham IDX (Bursa Efek \
Indonesia). Jawab pertanyaan pengguna dalam Bahasa Indonesia dengan ringkas, \
akurat, dan mudah dipahami (maksimal sekitar 150 kata). Gunakan konteks pasar \
Indonesia (IDX, OJK) bila relevan.

Jika disediakan blok KONTEKS REGULASI, dasarkan jawaban pada konteks itu dan \
sebutkan sumber beserta pasalnya. Jangan mengarang isi pasal.

Jangan memberikan rekomendasi beli/jual saham spesifik — arahkan pengguna \
untuk menjalankan analisis portofolio di dashboard bila mereka ingin \
rekomendasi alokasi. Tutup jawaban regulasi/keuangan sensitif dengan catatan \
singkat bahwa ini bukan nasihat keuangan."""

_REGULATORY_HINTS = (
    "ojk", "regulasi", "peraturan", "pasal", "ayat", "uupm", "pojk",
    "hukum", "legal", "pajak", "undang",
)

_MAX_CONTEXT_CHUNKS = 4


def _regulation_context(question: str) -> str:
    """Best-effort regulation grounding; empty string when not applicable."""
    if not any(hint in question.lower() for hint in _REGULATORY_HINTS):
        return ""
    try:
        from app.agents.legal.node import get_hybrid_retriever

        chunks = get_hybrid_retriever().retrieve(question, k=_MAX_CONTEXT_CHUNKS)
    except Exception as exc:  # noqa: BLE001 — grounding is optional
        log.warning("qa_node: regulation retrieval failed, answering ungrounded: %s", exc)
        return ""

    lines = []
    for c in chunks:
        ref = c.source + (f" Pasal {c.pasal}" if c.pasal else "") + (
            f" ayat ({c.ayat})" if c.ayat else ""
        )
        lines.append(f"[{ref}] {c.text}")
    return "\n".join(lines)


def _last_human_text(state: AgentState) -> str:
    for msg in reversed(state.get("messages") or []):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


@track_node_duration("n8_qa")
def qa_node(state: AgentState) -> AgentState:
    question = _last_human_text(state)
    if not question:
        return {
            "messages": [*state.get("messages", []),
                         AIMessage(content="Maaf, saya tidak menangkap pertanyaannya. Bisa diulangi?")],
        }

    context = _regulation_context(question)
    prompt = question if not context else (
        f"KONTEKS REGULASI:\n{context}\n\nPERTANYAAN:\n{question}"
    )

    try:
        response = get_chat_model().invoke([
            SystemMessage(content=SYSTEM),
            HumanMessage(content=prompt),
        ])
        answer = extract_text(response.content).strip() or (
            "Maaf, saya belum bisa menjawab pertanyaan itu. Coba tanyakan dengan cara lain."
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("qa_node: answer generation failed: %s", exc)
        return {
            "messages": [*state.get("messages", []),
                         AIMessage(content="Maaf, terjadi kendala saat menjawab. Silakan coba lagi.")],
            "errors": [*state.get("errors", []), {"node": "qa", "reason": str(exc)}],
        }

    return {"messages": [*state.get("messages", []), AIMessage(content=answer)]}
