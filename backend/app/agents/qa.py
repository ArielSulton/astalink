"""Q&A Node (N8) — direct-answer path for questions and brainstorming.

When N1 classifies a message as EXPLAIN there is nothing to allocate,
optimize, or legally validate — running the full analyst → optimizer →
legal → HITL pipeline would only burn latency/LLM cost and pollute the
audit/approvals surface. This node answers directly with Gemini and the
run ends.

It is the chatbot's conversational half: it receives the thread's prior
messages (injected by the API layer) so follow-ups stay coherent, and it
grounds its answers in optional context blocks — regulation chunks from
the legal retriever for OJK/UUPM-flavoured questions, and a live market
snapshot (price/indicators/news) when the question references tickers.
Either retrieval failing degrades to an ungrounded answer instead of
failing the run."""
from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.market.node import build_ticker_snapshot
from app.agents.state import AgentState
from app.core.gemini import extract_text, get_chat_model
from app.core.metrics import track_node_duration

log = logging.getLogger(__name__)

SYSTEM = """\
Kamu adalah asisten AI-CIO AstaLink — partner diskusi dan brainstorming untuk \
investor Indonesia (konteks pasar IDX/BEI dan regulasi OJK). Jawab dalam Bahasa \
Indonesia yang jelas dan membumi, maksimal sekitar 250 kata. Kamu boleh \
berdiskusi bebas: konsep keuangan, ide bisnis, perbandingan sektor, outlook \
pasar, maupun pertanyaan umum — gunakan riwayat percakapan agar jawaban nyambung.

Jika disediakan blok KONTEKS REGULASI, dasarkan jawaban pada konteks itu dan \
sebutkan sumber beserta pasalnya. Jangan mengarang isi pasal.

Jika disediakan blok KONTEKS DATA PASAR, gunakan HANYA angka dari blok itu saat \
membahas harga/indikator — jangan pernah mengarang angka yang tidak ada di data.

Kamu boleh membahas saham tertentu secara analitis, tetapi jangan memberikan \
rekomendasi beli/jual yang bersifat kepastian. Bila pengguna ingin rekomendasi \
alokasi sungguhan, arahkan mereka memintanya langsung di chat, misalnya: \
"alokasikan 10 juta ke BBCA" — pipeline analisis lengkap akan berjalan. Tutup \
jawaban keuangan yang sensitif dengan catatan singkat bahwa ini alat riset, \
bukan nasihat keuangan."""

_REGULATORY_HINTS = (
    "ojk", "regulasi", "peraturan", "pasal", "ayat", "uupm", "pojk",
    "hukum", "legal", "pajak", "undang",
)

_MAX_CONTEXT_CHUNKS = 4
_MAX_CONTEXT_TICKERS = 4
_MAX_NEWS_PER_TICKER = 3
_MAX_HISTORY = 20

# All-caps 4-letter words that look like IDX codes but never are — indices,
# regulators, and common finance acronyms. Keeps the regex fallback from
# firing yfinance lookups on non-tickers.
_TICKER_STOPWORDS = {
    "IHSG", "UUPM", "POJK", "BUMN", "UMKM", "MACD", "EBIT", "CAGR",
    "NPWP", "SBSN", "APBN", "HAKI", "PSAK", "SBUX",
}


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


def _detect_tickers(question: str, entities: dict) -> list[str]:
    """N1's extracted tickers first; fall back to all-caps 4-letter codes."""
    tickers = [str(t).upper() for t in entities.get("tickers") or []]
    if not tickers:
        tickers = [t for t in re.findall(r"\b[A-Z]{4}\b", question)
                   if t not in _TICKER_STOPWORDS]
    # de-dupe, keep order
    return list(dict.fromkeys(tickers))[:_MAX_CONTEXT_TICKERS]


def _fmt_num(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}".rstrip("0").rstrip(".")


def _market_context(question: str, entities: dict) -> str:
    """Best-effort live snapshot for referenced tickers; empty on failure."""
    tickers = _detect_tickers(question, entities)
    if not tickers:
        return ""

    lines: list[str] = []
    for ticker in tickers:
        try:
            snap = build_ticker_snapshot(ticker)
        except Exception as exc:  # noqa: BLE001 — data pull is optional
            log.warning("qa_node: market snapshot failed for %s: %s", ticker, exc)
            continue
        if snap.last_close is None:
            # yfinance returned nothing — probably not a real IDX code
            continue
        lines.append(
            f"- {ticker}: close={_fmt_num(snap.last_close)}, "
            f"RSI14={_fmt_num(snap.rsi14)}, SMA20={_fmt_num(snap.sma20)}, "
            f"EMA50={_fmt_num(snap.ema50)}, MACD={_fmt_num(snap.macd)}")
        for item in snap.news[:_MAX_NEWS_PER_TICKER]:
            lines.append(f"  - berita ({item.sentiment}): {item.title}")
    return "\n".join(lines)


def _last_human_text(state: AgentState) -> str:
    for msg in reversed(state.get("messages") or []):
        if isinstance(msg, HumanMessage):
            return str(msg.content)
    return ""


def _history(state: AgentState) -> list[BaseMessage]:
    """Prior human/AI turns, excluding the current (last) human message."""
    messages = [m for m in state.get("messages") or []
                if isinstance(m, (HumanMessage, AIMessage))]
    if messages and isinstance(messages[-1], HumanMessage):
        messages = messages[:-1]
    return messages[-_MAX_HISTORY:]


@track_node_duration("n8_qa")
def qa_node(state: AgentState) -> AgentState:
    question = _last_human_text(state)
    if not question:
        return {
            "messages": [*state.get("messages", []),
                         AIMessage(content="Maaf, saya tidak menangkap pertanyaannya. Bisa diulangi?")],
        }

    context_blocks = []
    regulation = _regulation_context(question)
    if regulation:
        context_blocks.append(f"KONTEKS REGULASI:\n{regulation}")
    market = _market_context(question, state.get("entities") or {})
    if market:
        context_blocks.append(f"KONTEKS DATA PASAR:\n{market}")

    prompt = question if not context_blocks else (
        "\n\n".join(context_blocks) + f"\n\nPERTANYAAN:\n{question}"
    )

    try:
        response = get_chat_model().invoke([
            SystemMessage(content=SYSTEM),
            *_history(state),
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
