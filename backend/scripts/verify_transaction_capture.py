"""Verify the transaction-capture flow end to end against the REAL stack.

Unit tests run against a fake Supabase client, which is what let a
duplicate-INSERT bug reach production (2026-09-07): the row shown to the
user stayed pending_confirmation forever while a second, invisible row got
confirmed. This script drives the actual HTTP endpoint, the actual graph,
the actual Postgres checkpointer and the actual tables, using a throwaway
user so nobody's real workspaces are touched. It cleans up after itself.

Usage, from the repo root with the dev stack running:

    docker cp backend/scripts/verify_transaction_capture.py astalink-backend-1:/tmp/v.py
    MSYS_NO_PATHCONV=1 docker exec astalink-backend-1 sh -c \\
        "cd /app && uv run --no-sync python /tmp/v.py"

Exits 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import secrets
import uuid

import httpx

from app.core.config import settings
from app.core.supabase_admin import get_admin_client

BASE = "http://localhost:8000/api/v1"
MESSAGE = "aku menjual kopi 20 ribu rupiah"
EXPECTED_AMOUNT = 20000.0

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{f' — {detail}' if detail else ''}")
    if not ok:
        failures.append(label)


class Session:
    def __init__(self, token: str):
        self.token = token
        self.thread: str | None = None

    def send(self, message: str, workspace_id: str, timeout: float = 300.0) -> dict:
        body = {"message": message, "workspace_id": workspace_id}
        if self.thread:
            body["thread_id"] = self.thread
        r = httpx.post(f"{BASE}/chat/", json=body,
                       headers={"Authorization": f"Bearer {self.token}"}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        self.thread = data.get("thread_id")
        return data


def main() -> int:
    sb = get_admin_client()
    email = f"verify-capture-{uuid.uuid4().hex[:10]}@example.com"
    password = secrets.token_urlsafe(18)
    user_id = None

    try:
        user_id = sb.auth.admin.create_user({
            "email": email, "password": password, "email_confirm": True,
        }).user.id
        token = httpx.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
            headers={"apikey": settings.SUPABASE_ANON_KEY}, timeout=30.0,
        ).json()["access_token"]

        def workspace_with(names: list[str]) -> tuple[str, list[str]]:
            ws = sb.table("workspaces").insert({
                "owner_user_id": user_id, "type": "business",
                "name": f"verify-{uuid.uuid4().hex[:6]}",
            }).execute().data[0]["id"]
            ids = [sb.table("businesses").insert({
                "workspace_id": ws, "name": n, "industry": "F&B",
            }).execute().data[0]["id"] for n in names]
            return ws, ids

        def rows(biz_ids: list[str]) -> list[dict]:
            out: list[dict] = []
            for b in biz_ids:
                out += sb.table("business_transactions").select("*").eq(
                    "business_id", b).execute().data or []
            return out

        # ------------------------------------------------------------------
        print("\nA. Satu bisnis — alur normal")
        ws_one, one = workspace_with(["Warung Kopi"])
        s = Session(token)
        card = s.send(MESSAGE, ws_one)
        check("kartu konfirmasi muncul", bool(card.get("pending_transaction")),
              card.get("message", "")[:80])
        check("tidak menanyakan bisnis", card.get("pending_business_choice") is None)
        if not card.get("pending_transaction"):
            return 1
        shown_id = card["pending_transaction"]["transaction_id"]
        check("nominal benar", card["pending_transaction"]["amount"] == EXPECTED_AMOUNT,
              str(card["pending_transaction"]["amount"]))
        check("tipe income", card["pending_transaction"]["type"] == "income")
        check("tidak ada peringatan palsu",
              card["pending_transaction"]["plausibility_flag"] is False)

        ack = s.send("txn_ya", ws_one)
        check("balasan konfirmasi", "tercatat" in ack.get("message", "").lower(),
              ack.get("message", "")[:60])

        got = rows(one)
        check("tepat satu baris tertulis", len(got) == 1, f"dapat {len(got)}")
        if len(got) == 1:
            check("baris yang dikonfirmasi = baris yang ditampilkan", got[0]["id"] == shown_id)
            check("status confirmed", got[0]["status"] == "confirmed", got[0]["status"])
            check("confirmed_at terisi", got[0]["confirmed_at"] is not None)
            check("source web_text", got[0]["source"] == "web_text")
        check("tidak ada baris pending yatim",
              not [r for r in got if r["status"] == "pending_confirmation"])

        rec = sb.table("business_financial_records").select("omset,profit").eq(
            "business_id", one[0]).execute().data or []
        check("omset naik tepat sekali",
              bool(rec) and float(rec[0]["omset"]) == EXPECTED_AMOUNT,
              str(rec))

        follow = s.send("halo, apa kabar", ws_one)
        check("chatbot masih bisa dipakai setelah transaksi",
              "menunggu konfirmasi" not in follow.get("message", "").lower(),
              follow.get("message", "")[:60])

        # ------------------------------------------------------------------
        print("\nB. Dua bisnis — AI bertanya dulu")
        ws_two, two = workspace_with(["Warung Kopi", "Toko Maju Jaya"])
        s2 = Session(token)
        ask = s2.send("jual teh manis 5rb", ws_two)
        choice = ask.get("pending_business_choice")
        check("kartu pilih-bisnis muncul", bool(choice), ask.get("message", "")[:80])
        check("belum ada baris tertulis", len(rows(two)) == 0)
        if not choice:
            return 1
        check("kedua bisnis ditawarkan", len(choice["options"]) == 2,
              str([o["name"] for o in choice["options"]]))

        picked = choice["options"][1]
        card2 = s2.send(f"bizsel_{picked['id']}", ws_two)
        check("kartu konfirmasi menyusul", bool(card2.get("pending_transaction")))
        check("nama bisnis tercantum",
              (card2.get("pending_transaction") or {}).get("business_name") == picked["name"],
              str((card2.get("pending_transaction") or {}).get("business_name")))
        s2.send("txn_ya", ws_two)

        got2 = rows(two)
        check("tepat satu baris di workspace 2-bisnis", len(got2) == 1, f"dapat {len(got2)}")
        if len(got2) == 1:
            check("tercatat ke bisnis yang dipilih", got2[0]["business_id"] == picked["id"])

        again = s2.send("jual kopi 8rb", ws_two)
        check("pilihan bisnis diingat di percakapan yang sama",
              again.get("pending_business_choice") is None
              and bool(again.get("pending_transaction")),
              again.get("message", "")[:70])
        check("bisnis yang diingat benar",
              (again.get("pending_transaction") or {}).get("business_name") == picked["name"])
        s2.send("txn_tidak", ws_two)

        # ------------------------------------------------------------------
        print("\nC. Tanpa bisnis — pesan jelas, bukan diam")
        ws_none = sb.table("workspaces").insert({
            "owner_user_id": user_id, "type": "business",
            "name": f"verify-{uuid.uuid4().hex[:6]}",
        }).execute().data[0]["id"]
        s3 = Session(token)
        blocked = s3.send(MESSAGE, ws_none)
        check("CTA daftarkan bisnis muncul",
              blocked.get("requires_business_setup") is True,
              blocked.get("message", "")[:80])

        print()
        print("SEMUA CEK LULUS" if not failures else "GAGAL: " + ", ".join(failures))
        return 1 if failures else 0

    finally:
        if user_id:
            try:
                sb.auth.admin.delete_user(user_id)
                print("\ncleanup: user sekali-pakai dihapus (cascade ke workspace/bisnis/transaksi)")
            except Exception as exc:  # noqa: BLE001 — report, never mask the result
                print(f"\ncleanup GAGAL: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
