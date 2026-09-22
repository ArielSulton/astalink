"""One writer for every reply that hands the user nothing.

Thirteen places used to return a canned sentence when the pipeline could not
produce work. They were identical every time, pushed the work back onto the
user, and never mentioned data the system already held — someone asking
"uang yang barusan masuk ini enaknya ke mana?" got "Maaf, saya kurang paham
maksud pesan Anda" while their balance sat in the database.

This module composes that sentence instead: anchored to the conversation
that is actually happening, allowed to name real figures, and always closing
with one concrete next step. The old sentences stay on in FALLBACKS — a
Gemini outage degrades to yesterday's behavior, never to silence.

Numbers are never the model's to invent. Callers compute and format them
into `facts`, the prompt forbids anything outside it, and the fallback path
carries no numbers at all.
"""
from __future__ import annotations

import logging
import re
from enum import StrEnum
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.context_snapshot import WorkspaceSnapshot
from app.core.gemini import extract_text, get_chat_model

log = logging.getLogger(__name__)

MAX_HISTORY = 10
MAX_SENTENCES = 3


class DeadEndReason(StrEnum):
    EMPTY_MESSAGE = "empty_message"
    INTENT_LLM_ERROR = "intent_llm_error"
    LOW_CONFIDENCE = "low_confidence"
    QA_NO_QUESTION = "qa_no_question"
    QA_EMPTY_ANSWER = "qa_empty_answer"
    QA_LLM_ERROR = "qa_llm_error"
    BUSINESS_NOT_FOUND = "business_not_found"
    BUSINESS_NO_RECORDS = "business_no_records"
    BUSINESS_UNCOMPUTABLE = "business_uncomputable"
    RISK_INSUFFICIENT_HISTORY = "risk_insufficient_history"
    PORTFOLIO_STATUS_UNAVAILABLE = "portfolio_status_unavailable"
    OPTIMIZER_NO_TICKERS = "optimizer_no_tickers"
    CHAT_GENERIC_FAILURE = "chat_generic_failure"


# The exact sentences that shipped before this module. Kept verbatim so that
# when Gemini is unavailable the user lands on the old behavior rather than
# on nothing. test_reply_writer.py asserts every reason has one.
FALLBACKS: dict[DeadEndReason, str] = {
    DeadEndReason.EMPTY_MESSAGE:
        "Pesannya kosong. Coba tulis ulang apa yang ingin Anda tanyakan.",
    DeadEndReason.INTENT_LLM_ERROR:
        "Maaf, saya lagi mengalami gangguan teknis dan belum bisa memproses "
        "pesan Anda. Coba kirim ulang sebentar lagi.",
    DeadEndReason.LOW_CONFIDENCE:
        "Bisa dijelaskan lagi tujuan Anda? Misal: alokasi dana, valuasi "
        "bisnis, atau review risiko.",
    DeadEndReason.QA_NO_QUESTION:
        "Maaf, saya tidak menangkap pertanyaannya. Bisa diulangi?",
    DeadEndReason.QA_EMPTY_ANSWER:
        "Maaf, saya belum bisa menjawab pertanyaan itu. Coba tanyakan dengan "
        "cara lain.",
    DeadEndReason.QA_LLM_ERROR:
        "Maaf, terjadi kendala saat menjawab. Silakan coba lagi.",
    DeadEndReason.BUSINESS_NOT_FOUND:
        "Saya tidak menemukan bisnis yang cocok di workspace ini. Tambahkan "
        "bisnis beserta catatan keuangannya lebih dulu di menu Bisnis Saya, "
        "lalu minta valuasi lagi.",
    DeadEndReason.BUSINESS_NO_RECORDS:
        "Bisnisnya ketemu, tapi belum ada catatan keuangan (laba per tahun) "
        "untuk dihitung. Lengkapi catatan keuangannya di menu Bisnis Saya, "
        "lalu coba lagi.",
    DeadEndReason.BUSINESS_UNCOMPUTABLE:
        "Maaf, valuasi bisnis belum bisa dihitung untuk permintaan ini. "
        "Pastikan bisnis dan catatan keuangannya sudah terdaftar di menu "
        "Bisnis Saya.",
    DeadEndReason.RISK_INSUFFICIENT_HISTORY:
        "Review risiko membutuhkan minimal satu ticker dengan riwayat harga "
        "yang cukup. Sebutkan sahamnya, misalnya: \"Review risiko portofolio "
        "dengan BBCA dan TLKM\".",
    DeadEndReason.PORTFOLIO_STATUS_UNAVAILABLE:
        "Ringkasan posisi portofolio lewat chat belum tersedia. Silakan buka "
        "halaman Asset View untuk melihat alokasi yang sudah disetujui, atau "
        "halaman Transactions untuk riwayat eksekusi.",
    DeadEndReason.OPTIMIZER_NO_TICKERS:
        "Untuk kasih rekomendasi alokasi, saya perlu tahu saham yang ingin "
        "Anda pertimbangkan. Sebutkan ticker-nya, misalnya: \"alokasikan 20 "
        "juta ke BBCA dan TLKM\".",
    DeadEndReason.CHAT_GENERIC_FAILURE:
        "Maaf, saya tidak dapat memproses permintaan ini.",
}

# What the user is actually stuck on, in plain Indonesian. The model reads
# this rather than the enum value, so it can say something true about the
# situation instead of inferring it from a code name.
_SITUATIONS: dict[DeadEndReason, str] = {
    DeadEndReason.EMPTY_MESSAGE: "Pesan pengguna kosong.",
    DeadEndReason.INTENT_LLM_ERROR:
        "Sistem gagal memproses pesan karena gangguan teknis sesaat.",
    DeadEndReason.LOW_CONFIDENCE:
        "Sistem belum yakin apa yang diminta pengguna dari pesan terakhirnya.",
    DeadEndReason.QA_NO_QUESTION: "Tidak ada pertanyaan yang bisa ditangkap.",
    DeadEndReason.QA_EMPTY_ANSWER:
        "Sistem tidak berhasil menyusun jawaban untuk pertanyaan itu.",
    DeadEndReason.QA_LLM_ERROR: "Terjadi kendala teknis saat menyusun jawaban.",
    DeadEndReason.BUSINESS_NOT_FOUND:
        "Tidak ada bisnis yang cocok dengan permintaan di workspace ini.",
    DeadEndReason.BUSINESS_NO_RECORDS:
        "Bisnisnya ada, tapi catatan keuangannya belum diisi sehingga valuasi "
        "tidak bisa dihitung.",
    DeadEndReason.BUSINESS_UNCOMPUTABLE:
        "Valuasi bisnis tidak bisa dihitung untuk permintaan ini.",
    DeadEndReason.RISK_INSUFFICIENT_HISTORY:
        "Review risiko butuh minimal satu saham dengan riwayat harga cukup, "
        "dan itu belum terpenuhi.",
    DeadEndReason.PORTFOLIO_STATUS_UNAVAILABLE:
        "Ringkasan posisi/holdings lewat chat belum tersedia; halaman Asset "
        "View dan Transactions sudah ada untuk itu.",
    DeadEndReason.OPTIMIZER_NO_TICKERS:
        "Permintaan alokasi masuk tapi tidak ada saham yang bisa dianalisis.",
    DeadEndReason.CHAT_GENERIC_FAILURE:
        "Permintaan tidak bisa diproses dan tidak ada hasil yang bisa "
        "ditampilkan.",
}

SYSTEM = """\
Anda menulis SATU balasan singkat untuk pengguna AstaLink ketika sistem
tidak bisa menghasilkan analisis apa pun untuk permintaannya.

Aturan wajib:
1. Sambung persis topik yang sedang dibahas di riwayat percakapan. Jangan
   memulai dari nol, jangan mengulang salam, jangan memperkenalkan diri.
2. DILARANG menyebut angka, kode saham, nama bisnis, atau tanggal yang
   tidak ada di DATA atau di riwayat percakapan. Jangan mengarang nominal.
3. Maksimal 3 kalimat, bahasa Indonesia, nada tenang dan setara — bukan
   minta maaf berlebihan.
4. Tutup dengan SATU langkah konkret yang bisa dijawab pengguna secara
   singkat.
5. Jangan menjanjikan tindakan yang sistem tidak lakukan. AstaLink memberi
   rekomendasi dan analisis; ia tidak mengeksekusi transaksi.

Balas dengan teks biasa saja, tanpa markdown, tanpa daftar bernomor."""


def _history(state: dict[str, Any]) -> list[BaseMessage]:
    messages = [m for m in state.get("messages") or []
                if isinstance(m, (HumanMessage, AIMessage))]
    return messages[-MAX_HISTORY:]


def _trim(text: str) -> str:
    """Keep at most MAX_SENTENCES sentences, cut on sentence boundaries so an
    over-long reply never arrives mid-word."""
    parts = re.findall(r"[^.!?]+[.!?]", text)
    if not parts:
        return text.strip()
    return "".join(parts[:MAX_SENTENCES]).strip()


def compose_dead_end_reply(
    *,
    reason: DeadEndReason,
    state: dict[str, Any],
    snapshot: WorkspaceSnapshot | None = None,
    facts: dict[str, str] | None = None,
    fallback: str | None = None,
) -> str:
    """Compose the user-facing sentence for a dead end. Never raises, never
    recurses — on any failure the caller gets the canned sentence."""
    safety_net = fallback if fallback is not None else FALLBACKS[reason]

    blocks = [f"SITUASI: {_SITUATIONS[reason]}"]
    if facts:
        rendered = "\n".join(f"- {k}: {v}" for k, v in facts.items())
        blocks.append(f"DATA:\n{rendered}")
    if snapshot is not None and not snapshot.is_empty:
        blocks.append(f"DATA WORKSPACE:\n{snapshot.render_for_prompt()}")
    blocks.append("Tulis balasannya sekarang.")

    try:
        response = get_chat_model().invoke([
            SystemMessage(content=SYSTEM),
            *_history(state),
            HumanMessage(content="\n\n".join(blocks)),
        ])
        text = _trim(extract_text(response.content).strip())
    except Exception as exc:  # noqa: BLE001
        log.error("reply_writer: compose failed for %s: %s", reason, exc)
        return safety_net

    return text or safety_net
