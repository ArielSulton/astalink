# M4 — Audit Trail UI & Read API — Design

> **Status:** Draft (awaiting user review)
> **Tanggal:** 2026-07-03
> **Milestone:** M4 (Observability + Audit UI) per `prd-astalink.md`
> **Scope owner:** Backend + Frontend

## 1. Tujuan

Menuntaskan milestone M4: menjadikan klaim inti PRD — *"setiap keputusan dapat dipertanggungjawabkan via `audit_id`"* — nyata di UI, bukan hanya baris di tabel `audit_log`. Saat ini jejak audit ditulis di setiap run tetapi **tidak bisa dibaca**: tidak ada endpoint audit read, dan halaman `/audit` frontend kosong. Deep-link WhatsApp (`{APP_BASE_URL}/audit/{audit_id}`) mengarah ke halaman kosong.

## 2. State saat ini (fakta)

**Sudah ada:**
- Prometheus (:9090) + Grafana (:3005) dengan 3 dashboard (`ai-quality`, `business-funnel`, `pipeline-health`).
- `core/metrics.py`: `NODE_DURATION`, `NODE_ERRORS`, `LEGAL_STATUS`, `REVISION_COUNT`, `EXECUTIONS`. Node didekorasi `@track_node_duration`.
- Tabel `audit_log`, `allocation_plans`, `transactions` terisi tiap run (di-thread lewat `audit_id`).
- `POST /approvals`, `GET /approvals`, `GET /approvals/{id}` — tapi **hanya** menampilkan run berstatus `awaiting_approval`.

**Gap (yang dikerjakan spec ini):**
1. Tidak ada endpoint audit read untuk **semua** run (bukan hanya yang menunggu approval).
2. `frontend/app/(protected)/audit/page.tsx` kosong.
3. Tidak ada halaman `/audit/[auditId]`.
4. Dead code: `backend/app/agents/stubs.py` (16 stub) tak diimpor graph; docstring `graph.py` menyebut "Phase 3 / stubs" padahal semua node sudah riil.

## 3. Non-Goals (YAGNI)

- Dashboard Grafana baru — 3 yang ada cukup.
- Broker riil / sell orders — itu M3, terblokir keputusan partner. Di luar scope.
- Export PDF / CSV audit — belum diminta.
- Snapshot `AgentState` penuh ke kolom JSON baru — ditolak: butuh migrasi DB + ubah node; data dari join tabel yang ada sudah cukup akurat.

## 4. Keputusan arsitektur

**Sumber data audit detail = join tabel yang sudah dipersist** (`audit_log` + `allocation_plans` + `transactions`), bukan snapshot state baru. Alasan: tanpa migrasi DB, tanpa ubah pipeline, akurat karena membaca data yang benar-benar ditulis run. Konsisten dengan cara `GET /approvals/{id}` sudah bekerja (join `audit_log` + `allocation_plans`).

**Read-only, service-role.** Endpoint audit hanya membaca. Pakai `get_admin_client()` (pola sama seperti approvals) dengan filter wajib `workspace_id` + `user_id` agar RLS/isolasi antar-user terjaga.

## 5. Komponen

### A. Backend — audit read API (`app/api/v1/audit.py`)

Router baru, prefix `/audit`, didaftarkan di `api/v1/router.py`. Dependency auth `get_current_user` (pola sama).

**`GET /audit?workspace_id=<id>`** → daftar seluruh run untuk user+workspace, terurut `created_at` desc.
- Query `audit_log` difilter `workspace_id` + `user_id` (dari `user["sub"]`). **Tanpa** filter status (beda dari approvals yang hanya `awaiting_approval`).
- Response: `AuditListResponse { audits: list[AuditSummary] }`.
- `AuditSummary`: `audit_id`, `intent`, `status`, `created_at`, `completed_at | None`.

**`GET /audit/{audit_id}`** → detail satu run.
- Muat `audit_log` (validasi `user_id == user["sub"]`, else 404 — pola `_load_audit` yang sudah ada).
- Join `allocation_plans` (plan_json, legal_status, legal_citations) dan `transactions` (list order).
- Response `AuditDetail`:
  - `audit_id`, `status`, `intent`, `workspace_id`, `created_at`, `completed_at | None`
  - `allocation_plan: dict | None`
  - `legal_status: str | None`, `legal_citations: list[dict]`
  - `transactions: list[dict]`

Model di `app/models/audit.py` (file baru, cermin `models/approvals.py`).

### B. Frontend — halaman audit

**`api-client.ts`** — tambah method + interface (pola `getApproval`):
- `getAuditList(workspaceId, token) → AuditListResponse`
- `getAuditDetail(auditId, token) → AuditDetail`

**`/audit/page.tsx`** — tabel riwayat run.
- Kolom: waktu, intent, status (badge), link "Lihat". Reuse pola fetch + tabel dari approvals page.
- Empty state: "Belum ada keputusan tercatat."

**`/audit/[auditId]/page.tsx`** — timeline keputusan satu run, urut sesuai pipeline:
1. **Intent** — apa yang diminta user.
2. **Alokasi** — weights + cash dari `allocation_plan`.
3. **Legal** — `legal_status` (badge) + daftar sitasi pasal/ayat (`legal_citations`).
4. **Approval** — status akhir (`approved`/`rejected`/`awaiting_approval`).
5. **Transaksi** — daftar order (`ticker`, side, qty, status) bila ada.

Membuat deep-link WhatsApp `/audit/{audit_id}` berfungsi.

### C. Cleanup fondasi

- Hapus `backend/app/agents/stubs.py` (dead code — dikonfirmasi tak diimpor `graph.py`).
- Betulkan docstring `graph.py` baris 1–5: hapus penyebutan "Phase 3 / remaining stubs" yang menyesatkan; nyatakan semua node riil.
- Update `prd-astalink.md` §13 Timeline: tandai M1–M2 selesai, M3 sebagian (broker sandbox), M4 selesai setelah ini.

## 6. Data flow

```
Browser /audit ──GET /api/v1/audit?workspace_id──> audit.py ──select──> audit_log (filter user+workspace)
Browser /audit/[id] ──GET /api/v1/audit/{id}──> audit.py ──join──> audit_log + allocation_plans + transactions
```

Tidak ada tulis. Tidak ada perubahan pipeline. Tidak ada migrasi DB.

## 7. Error handling

- `audit_id` tak ditemukan atau `user_id` tak cocok → 404 (pola `_load_audit`).
- `allocation_plans` / `transactions` kosong untuk suatu run (mis. run berhenti sebelum optimizer) → field `null` / list kosong, bukan error. Halaman menampilkan bagian yang tersedia saja.
- Frontend: state loading + error fetch (pola api-client yang sudah ada).

## 8. Testing

- `backend/tests/test_audit_api.py`:
  - list mengembalikan semua status (bukan hanya awaiting_approval).
  - list & detail terfilter `user_id` — user lain dapat 404 / list kosong.
  - detail merakit plan + citations + transactions dari tabel.
  - run tanpa allocation_plan → detail tetap 200 dengan field null.
- `pytest` `asyncio_mode="auto"` (async tanpa dekorator).
- Frontend: tidak ada test runner; verifikasi via `tsc --noEmit` + drive halaman di app yang berjalan.

## 9. Urutan implementasi

1. `models/audit.py` (Pydantic).
2. `api/v1/audit.py` + daftarkan di `router.py`.
3. `tests/test_audit_api.py` → hijau.
4. `api-client.ts` method + interface.
5. `/audit/page.tsx` (list).
6. `/audit/[auditId]/page.tsx` (detail).
7. Cleanup: hapus `stubs.py`, betulkan docstring `graph.py`, update PRD.
8. Verifikasi end-to-end: jalankan run → cek muncul di /audit → buka detail.

## 10. Definisi selesai (M4)

- `GET /audit` + `GET /audit/{id}` hijau di test, terfilter per user.
- `/audit` menampilkan riwayat run; `/audit/[auditId]` menampilkan timeline keputusan lengkap.
- Deep-link WhatsApp `/audit/{id}` membuka detail yang benar.
- `stubs.py` terhapus, docstring `graph.py` akurat, PRD §13 diperbarui.
- Stack tetap boot tanpa key opsional (properti boots-without-keys terjaga).
