# AstaLink — Product Requirements Document (PRD)

> **Status:** Draft
> **Versi:** 1.0
> **Tanggal:** 2026-07-02
> **Pemilik (Owner):** Tim AstaLink (Hackathon Digdaya)
> **Stakeholders:** Engineering (Backend/LangGraph, Frontend), Product, Legal/Compliance, Data/ML, DevOps

> **Asumsi:** PRD ini di-*reverse-engineer* dari kode yang ada saat ini (`backend/app/agents`, `backend/app/api`, `frontend/app`). Beberapa hal yang belum eksplisit di kode (target bisnis, SLA, roadmap komersial) diisi dengan asumsi wajar dan ditandai di bagian terkait. Broker eksekusi (N7) saat ini masih tahap integrasi/stub sesuai catatan di `graph.py`.

---

## 1. Ringkasan Eksekutif (Executive Summary)

AstaLink adalah **"AI-CIO" (AI Chief Investment Officer)** untuk portofolio investasi Indonesia. Sebuah permintaan pengguna (mis. "alokasikan Rp 100 juta ke saham perbankan") mengalir melalui pipeline **LangGraph** yang menganalisis pasar, menyusun rencana alokasi ter-optimasi, **memvalidasinya terhadap regulasi keuangan Indonesia** (RAG atas dokumen hukum yang di-upload), lalu **berhenti untuk persetujuan manusia + PIN** sebelum mengeksekusi transaksi ke broker.

Produk menyasar investor ritel/HNW dan pengelola portofolio yang butuh keputusan investasi cepat namun tetap **patuh regulasi dan dapat diaudit penuh**. Hasil yang diharapkan: keputusan alokasi yang lebih cepat, transparan (setiap langkah punya `audit_id`), dan aman secara hukum karena ada *legal gate* + *human-in-the-loop* wajib sebelum uang bergerak.

## 2. Latar Belakang & Masalah (Background & Problem Statement)

- **Konteks:** Keputusan alokasi portofolio saat ini bergantung pada analis manusia yang lambat dan mahal, sementara tool robo-advisor umum tidak memahami konteks regulasi OJK/IDX dan tidak menyediakan jejak audit yang layak.
- **Masalah:**
  - Investor sulit mendapat rekomendasi alokasi yang **sekaligus** ter-optimasi secara kuantitatif **dan** tervalidasi terhadap regulasi Indonesia.
  - Eksekusi otomatis penuh berisiko: kesalahan alokasi bisa langsung memindahkan dana nyata tanpa checkpoint.
  - Tidak ada jejak audit yang menghubungkan "kenapa keputusan ini diambil" dengan "regulasi mana yang mendasarinya".
- **Bukti/Sinyal:** Regulasi pasar modal Indonesia (OJK/IDX) kompleks dan sering berubah; kesalahan kepatuhan berbiaya tinggi. Kebutuhan *explainability* + *auditability* pada sistem keuangan berbasis AI meningkat.
- **Peluang:** Menggabungkan optimasi portofolio kuantitatif + RAG hukum + HITL wajib dalam satu pipeline yang dapat diaudit adalah diferensiasi kuat vs robo-advisor generik.

## 3. Tujuan & Sasaran (Goals & Objectives)

- **Tujuan Produk:**
  - Menyediakan rekomendasi alokasi portofolio otomatis yang **tervalidasi regulasi Indonesia** sebelum sampai ke pengguna.
  - Menjamin **tidak ada transaksi tereksekusi tanpa persetujuan manusia + verifikasi PIN**.
  - Menyediakan **jejak audit end-to-end** (`audit_id`) untuk setiap keputusan dan sitasi hukumnya.
  - Boot & jalan tanpa semua API key eksternal (degradasi anggun) untuk memudahkan pengembangan dan demo.
- **Non-Goals (di luar scope saat ini):**
  - Bukan platform trading real-time / high-frequency.
  - Bukan penasihat pajak atau perencana keuangan holistik.
  - Tidak menjamin imbal hasil investasi; keluaran bersifat rekomendasi ter-optimasi, bukan janji return.
  - Tidak menggantikan izin/lisensi manajer investasi — asumsi: dipakai dalam konteks berlisensi atau sebagai *decision-support*.

## 4. Metrik Keberhasilan (Success Metrics / KPIs)

| Metrik | Baseline | Target | Cara Ukur |
|--------|----------|--------|-----------|
| Waktu dari permintaan → rencana alokasi siap-review | manual (jam) | < 60 detik | Durasi node Prometheus (`track_node_duration`) |
| Tingkat lolos validasi legal tanpa revisi | — | ≥ 70% run | `legal_status = approved` di run pertama |
| Akurasi sitasi hukum (span terverifikasi ada di chunk) | — | ≥ 95% | Grader legal (cek `span` ⊂ chunk text) |
| Run yang berhenti benar di HITL sebelum eksekusi | — | 100% (untuk intent eksekusi) | Cek `interrupt()` terpicu sebelum N7 |
| Kelengkapan jejak audit (`audit_id` konsisten hulu-hilir) | — | 100% run | Rekonstruksi dari tabel `audit_log` |
| Loop revisi legal tidak melebihi cap | — | 100% ≤ 3 revisi | `revision_count ≤ MAX_REVISIONS` |

**Guardrail metrics (tidak boleh memburuk):**
- Zero transaksi tereksekusi tanpa `user_approval = approved` + PIN valid.
- Zero halusinasi angka: narasi node tidak boleh memuat angka di luar data terkomputasi.
- Lockout PIN berfungsi (attempt gagal → terkunci) — tidak boleh bypass.

## 5. Target Pengguna & Persona (Target Users & Personas)

**Persona 1 — Investor Ritel/HNW ("Rina")**
- **Kebutuhan:** Rekomendasi alokasi cepat & paham konteks Indonesia; ingin tahu keputusan aman secara hukum.
- **Frustrasi:** Robo-advisor generik tidak paham regulasi lokal; takut salah alokasi dana besar.
- **Konteks:** Web app di desktop/mobile, saat rebalancing portofolio atau menyetor dana baru.

**Persona 2 — Manajer Portofolio / Analis ("Budi")**
- **Kebutuhan:** *Decision-support* ter-optimasi + validasi kepatuhan otomatis + audit trail untuk pertanggungjawaban.
- **Frustrasi:** Menyusun & mengecek kepatuhan manual memakan waktu; sulit membuktikan dasar regulasi tiap keputusan.
- **Konteks:** Dashboard web, review approval sebelum eksekusi, akses riwayat audit.

**Persona 3 — Tim Compliance/Legal ("Sari")**
- **Kebutuhan:** Setiap keputusan tervalidasi terhadap regulasi + sitasi pasal/ayat yang bisa diverifikasi.
- **Frustrasi:** Kepatuhan sering jadi *afterthought* dan tidak terdokumentasi.
- **Konteks:** Meninjau `legal_docs`, memeriksa `audit_log` & sitasi.

## 6. User Stories / Use Cases

- **US-1:** Sebagai investor, saya ingin mengirim permintaan alokasi dalam bahasa natural agar sistem menyusun rencana portofolio untuk saya. *(Happy path)*
- **US-2:** Sebagai investor, saya ingin melihat rencana alokasi + status legal + sitasi regulasi sebelum menyetujui, agar saya paham dasar keputusannya.
- **US-3:** Sebagai investor, saya ingin **menyetujui dengan PIN** sebelum transaksi dieksekusi, agar dana saya tidak berpindah tanpa konfirmasi eksplisit.
- **US-4:** Sebagai investor, saya ingin **menolak** rencana, agar run berakhir tanpa eksekusi.
- **US-5:** Sebagai compliance, saya ingin sistem otomatis menandai rencana yang melanggar regulasi (`rejected`/`partial`) dan menyarankan alternatif, bukan sekadar menolak.
- **US-6:** Sebagai analis, saya ingin melihat riwayat audit lengkap tiap keputusan via `audit_id`, agar keputusan dapat dipertanggungjawabkan.
- **US-7:** Sebagai pengguna, saya ingin melanjutkan percakapan (`thread_id`) agar konteks tidak hilang antar permintaan.
- **US-8:** Sebagai pengguna, saya ingin menerima notifikasi/approval via WhatsApp agar bisa menyetujui di luar dashboard. *(Kanal opsional)*

## 7. Persyaratan Fungsional (Functional Requirements)

| ID | Kebutuhan | Prioritas | Kriteria Penerimaan |
|----|-----------|-----------|---------------------|
| FR-1 | **N1 Intent** — klasifikasi maksud pengguna + ekstraksi entitas | Must | `IntentDecision` dengan `intent`, `entities`, `confidence`; set `clarification_question` bila `UNKNOWN` atau confidence < 0.6 |
| FR-2 | **N2a Market** — snapshot pasar (indikator teknikal + berita) | Must | `MarketSnapshot` berisi `TickerSnapshot` (SMA/EMA/RSI/MACD/BB) + `NewsItem`; berjalan tanpa News API |
| FR-3 | **N2b Business** — valuasi bisnis (DCF) | Must | `BusinessValuation` (enterprise value, discount rate, cashflows) |
| FR-4 | **N2c Risk** — metrik risiko | Must | `RiskAssessment` (VaR 95/99, Sharpe, suggested weights) |
| FR-5 | **Fan-out paralel N2a/b/c** menulis ke `entities` tanpa konflik | Must | Reducer `operator.or_` mencegah `INVALID_CONCURRENT_GRAPH_UPDATE` |
| FR-6 | **N5 Optimizer** — solusi bobot alokasi ter-optimasi | Must | `AllocationPlan` (weights, cash, buffer); status solver `optimal`/`infeasible`/`fallback_equal`; hormati `max_per_asset`, `min_cash_buffer`, `sector_caps`, `forbidden_tickers`, `partial_tickers` |
| FR-7 | **N3 Legal (RAG)** — validasi rencana terhadap regulasi | Must | `LegalDecision` (`status`, `reasoning`, `citations`, `alternative_actions`); sitasi punya `span` terverifikasi ada di chunk |
| FR-8 | **Loop revisi legal** — jika `rejected`, kembali ke optimizer dengan feedback | Must | Kembali ke N5 selama `revision_count < 3`; ≥ 3 → `rejection_handler` → END |
| FR-9 | **N6 HITL** — pause wajib untuk approval manusia | Must | `interrupt()` mem-persist state; run lanjut hanya via `Command(resume=...)` |
| FR-10 | **Verifikasi PIN saat approve** dengan lockout | Must | PIN di-hash argon2; salah → attempt++ / lockout; benar → reset & resume graph |
| FR-11 | **N7 Execution** — eksekusi transaksi ke broker | Must | Hanya jalan jika `user_approval = approved`; menghasilkan `BrokerOrder[]` |
| FR-12 | **Reject flow** — tolak rencana | Must | `Command(resume={approval: rejected})` → run END tanpa eksekusi; status `rejected` di `audit_log` |
| FR-13 | **`POST /agent/run`** — jalankan pipeline | Must | Mengembalikan `audit_id`, `thread_id`, `intent`, `legal_status`, `allocation_plan`, dll; boleh return dalam keadaan paused di HITL |
| FR-14 | **`GET /approvals`** — daftar approval menunggu | Must | Hanya status `awaiting_approval`, terfilter `workspace_id` + `user_id` |
| FR-15 | **`GET /approvals/{audit_id}`** — detail rencana + sitasi | Must | Menampilkan `plan_json`, `legal_status`, `legal_citations` |
| FR-16 | **Manajemen PIN** (`/users`) — register PIN | Must | PIN tersimpan ter-hash; wajib ada sebelum approve |
| FR-17 | **Autentikasi** — verifikasi JWT Supabase per request | Must | `get_current_user` memvalidasi bearer token HS256 |
| FR-18 | **Legal docs** — upload & kelola dokumen regulasi (RAG corpus) | Should | Dokumen ter-index untuk retrieval (Pinecone + BM25 fusion) |
| FR-19 | **Chat** (`/chat`) — antarmuka percakapan | Should | Melanjutkan thread; menyalurkan permintaan ke pipeline |
| FR-20 | **Notifikasi WhatsApp** — approval/notif via WhatsApp | Could | Webhook terverifikasi signature; deep link ke approval |
| FR-21 | **Dashboard, transaksi, aset, berita, audit UI** | Should | Route protected menampilkan data terkait per workspace |

## 8. Persyaratan Non-Fungsional (Non-Functional Requirements)

- **Performa:** Target run analisis→rencana < 60 detik; tiap node ter-instrument via Prometheus (`@track_node_duration`).
- **Skalabilitas:** Fan-out paralel N2a/b/c; checkpointer Postgres mendukung banyak thread/run konkuren.
- **Keamanan & Privasi:**
  - Auth JWT Supabase (HS256) di setiap request; RLS Postgres (`0007_rls_policies.sql`) membatasi akses per user/workspace.
  - PIN di-hash argon2; lockout setelah percobaan gagal.
  - Data finansial adalah PII sensitif — akses terbatas per `user_id`/`workspace_id`.
- **Keandalan/Ketersediaan:**
  - HITL pause **hanya bertahan lintas request dengan PostgresSaver**; MemorySaver hanya untuk dev/test (state hilang saat restart).
  - `audit_id` immutable sepanjang run — jangan di-regenerate.
- **Kepatuhan (Compliance):** Legal gate wajib sebelum HITL; sitasi pasal/ayat terverifikasi; jejak audit lengkap di `audit_log`.
- **Observability:** Prometheus (:9090) + Grafana (:3001); durasi tiap node; `audit_log` sebagai trace bisnis.
- **Kompatibilitas:** Web app (Next.js 16 App Router, React 19, Tailwind v4); backend FastAPI/Python (uv).
- **Boots-without-keys:** App harus boot tanpa Gemini/Pinecone/News/WhatsApp/`SUPABASE_DB_URL` — client lazy, error hanya saat fitur dipakai. **Properti ini wajib dipertahankan.**
- **Aksesibilitas:** Ikuti praktik Shadcn UI/WCAG untuk komponen frontend. *(Perlu ditentukan: target level WCAG.)*

## 9. Desain & Pengalaman Pengguna (UX / Design)

- **Alur utama:** Chatbot/permintaan → tampilkan rencana alokasi + status legal + sitasi → layar approval (input PIN) → konfirmasi eksekusi / hasil transaksi.
- **Route frontend (protected):** `dashboard`, `approvals`, `audit`, `transactions`, `assets`, `chatbot`, `legal-docs`, `news`, `settings`. **Auth:** `login`, `signup`.
- **Middleware auth:** refresh sesi Supabase tiap request; unauth → `/login`; sudah login di `/login|/signup` → `/dashboard`. Prefix protected di-hardcode di `middleware.ts` (tambah route baru di sana).
- **State kosong/loading/error:** rencana belum ada, run sedang berjalan (paused di HITL), legal `rejected` dengan alternatif, PIN salah/terkunci.
- **Prinsip:** transparansi (selalu tampilkan dasar legal), *safety-first* (PIN + konfirmasi eksplisit sebelum eksekusi).

## 10. Ketergantungan & Integrasi (Dependencies & Integrations)

- **Supabase** (wajib): Auth, Postgres, RLS. URL/anon/JWT **required**.
- **Google Gemini** (opsional, lazy): chat + embeddings untuk narasi node & RAG.
- **Pinecone** (opsional, lazy): vector store RAG regulasi (`astalink-regulations`).
- **News API** (opsional): N2a berjalan tanpanya.
- **WhatsApp Business API (Meta Cloud)** (opsional): notifikasi & approval.
- **LangGraph PostgresSaver** (`SUPABASE_DB_URL`, opsional tapi wajib untuk HITL lintas-request).
- **Broker eksekusi** (N7): integrasi transaksi — *Perlu ditentukan: broker/partner riil & kontrak API.*
- **Data:** migrasi SQL bernomor (`backend/migrations/0001–0009`); Drizzle hanya mengelola tabel `regulation_documents`.

## 11. Persyaratan Teknis (Technical Considerations)

- **Arsitektur:** Monorepo — Next.js frontend + FastAPI/LangGraph backend + Supabase + Prometheus/Grafana; orkestrasi Docker Compose (`make dev`/`make prod`).
- **Pipeline LangGraph:**
  ```
  N1 intent ─┬─> N2a market ─┐
             ├─> N2b business ├─> N5 optimizer ─> N3 legal ──(approved/partial)─> N6 HITL ──(approved)─> N7 execute
             └─> N2c risk ────┘                        │                              └─(rejected)─> END
                                                        └─(rejected, <3)─> N5 optimizer
                                                        └─(rejected, ≥3)─> rejection_handler
  ```
- **State bersama (`AgentState`, `TypedDict total=False`):** `audit_id`, `messages`, `intent`, `entities` (reducer `operator.or_`), `allocation_plan`, `revision_count`, `legal_status`, `legal_citations`, `user_approval`, `transactions`, `errors`. Field baru yang ditulis node paralel **wajib** punya anotasi reducer.
- **Konvensi node:** tiap agent = package (`node.py` + `schemas.py` + helper), didekorasi `@track_node_duration("nX_name")`; narasi via Gemini dengan constraint **tidak mengarang angka** di luar data terkomputasi.
- **Kontrak API (v1, prefix `/api/v1`):**
  - `POST /agent/run` → jalankan pipeline (bisa paused di HITL).
  - `GET /approvals?workspace_id=` → daftar menunggu approval.
  - `GET /approvals/{audit_id}` → detail rencana + sitasi.
  - `POST /approvals/{audit_id}/approve` (butuh PIN) → resume graph → eksekusi.
  - `POST /approvals/{audit_id}/reject` → resume graph → END.
  - `/chat`, `/legal`, `/market`, `/users` (PIN), `/whatsapp`, `/health`.
  - `/docs` (Swagger) hanya saat `DEBUG=true`; `/metrics` untuk Prometheus.
- **Batasan teknis:**
  - `MAX_REVISIONS = 3` (loop legal) di `graph.py`.
  - `ta-lib` **tidak** di `pyproject.toml` (butuh C lib `libta-lib`; di-install via Dockerfile) — jangan tambahkan ke `pyproject.toml`.
  - Tidak ada linter/formatter backend — ikuti gaya yang ada; `pytest` `asyncio_mode="auto"`.
  - Frontend: TypeScript strict, React Compiler aktif; tidak ada test runner (hanya `tsc --noEmit` + eslint).

## 12. Rilis & Rencana Peluncuran (Rollout & Release Plan)

- **Fase (sesuai penomoran kode):**
  - Phase 1–2: Legal agent + graph wiring.
  - Phase 3: Node riil (intent, legal, market, business, risk).
  - Phase 4: Optimizer riil (menggantikan stub).
  - Phase 5: HITL riil (`interrupt()`).
  - Phase 6: Execution riil ke broker (saat ini area integrasi/stub).
- **Strategi rilis:** Demo hackathon → alpha internal (MemorySaver → PostgresSaver) → beta terbatas dengan broker sandbox → produksi via nginx (`make prod`).
- **Rencana rollback:** Karena HITL wajib, tidak ada eksekusi tanpa approval — rollback keputusan = reject flow. Untuk deploy, gunakan versi image sebelumnya via Compose; migrasi SQL bersifat aditif & bernomor.
- **Feature flag:** Fitur eksternal (WhatsApp/News/Pinecone) otomatis "off" bila key kosong (boots-without-keys) — berfungsi sebagai flag alami.

## 13. Timeline & Milestone

> **Asumsi:** Tanggal indikatif — perlu disesuaikan dengan jadwal tim.

| Milestone | Deliverable | Target Tanggal | PIC |
|-----------|-------------|----------------|-----|
| M1 | Pipeline end-to-end dengan node riil (N1–N5) | ✅ Selesai | Backend |
| M2 | Legal RAG + loop revisi + HITL pause (PostgresSaver) | ✅ Selesai | Backend |
| M3 | Integrasi broker N7 (sandbox) + PIN/approval UI | 🟡 Sebagian — sandbox buy-only; broker riil (Phase 8) tertunda | Backend/Frontend |
| M4 | Observability (Grafana) + audit trail read API & UI | ✅ Selesai | DevOps/Frontend |
| M5 | Beta terbatas + hardening keamanan/compliance | ⬜ Belum | Semua |

## 14. Risiko & Mitigasi (Risks & Mitigations)

| Risiko | Dampak | Kemungkinan | Mitigasi |
|--------|--------|-------------|----------|
| Halusinasi angka oleh LLM dalam narasi | H | M | Prompt constraint "no invented numbers"; narasi hanya dari data terkomputasi; grader legal cek `span` |
| State HITL hilang saat restart (MemorySaver di prod) | H | M | Wajib PostgresSaver (`SUPABASE_DB_URL`) di non-dev; guard konfigurasi |
| Sitasi hukum salah/tidak terverifikasi | H | M | Grader memverifikasi `span` ⊂ chunk; fusion Pinecone+BM25; `chunk_id` deterministik |
| Eksekusi transaksi tanpa approval | H (kritis) | L | HITL `interrupt()` wajib; N7 hanya jalan bila `user_approval=approved` + PIN valid |
| Loop revisi legal tak berujung | M | L | `MAX_REVISIONS=3` → `rejection_handler` |
| Konflik penulisan state paralel | M | M | Reducer `operator.or_` pada `entities`; wajib anotasi untuk field paralel baru |
| Kepatuhan lisensi manajer investasi | H | M | Posisikan sebagai decision-support/berlisensi; *Perlu ditentukan: legal review* |
| Ketergantungan `ta-lib` C library | M | L | Install via Dockerfile; jangan masuk `pyproject.toml` |
| Kebocoran data finansial lintas user | H | L | RLS Postgres + filter `user_id`/`workspace_id` di setiap query |

## 15. Pertanyaan Terbuka (Open Questions)

- [ ] Broker/partner eksekusi riil (N7) yang akan diintegrasikan dan kontrak API-nya?
- [ ] Status lisensi/kepatuhan regulator (OJK) untuk operasi produksi — decision-support vs advisory berlisensi?
- [ ] Target SLA & volume (jumlah run/hari, konkurensi) untuk sizing PostgresSaver?
- [ ] Target level aksesibilitas (WCAG) untuk frontend?
- [ ] Sumber data pasar/valuasi resmi (IDX, data vendor) dan lisensinya?
- [ ] Kebijakan retensi & audit `audit_log` (berapa lama, ekspor untuk regulator)?
- [ ] Model monetisasi (langganan, per-transaksi, B2B) — *Perlu ditentukan.*

## 16. Lampiran (Appendix)

**Glosarium:**
- **AI-CIO:** AI Chief Investment Officer — persona sistem sebagai penasihat investasi.
- **HITL:** Human-in-the-loop — jeda wajib untuk persetujuan manusia sebelum eksekusi.
- **RAG:** Retrieval-Augmented Generation — validasi legal atas korpus regulasi yang di-index.
- **`audit_id`:** Kunci trace immutable, dibuat di N1, mengalir ke semua node & tabel `audit_log`.
- **Checkpointer:** Mekanisme LangGraph mem-persist state (PostgresSaver/MemorySaver) — kunci HITL.
- **Pasal/Ayat:** Referensi unit regulasi Indonesia yang disitasi legal agent.

**Referensi kode:**
- Pipeline: `backend/app/agents/graph.py`, `state.py`
- Node: `backend/app/agents/{intent,market,business,risk,optimizer,legal,hitl,execution}/`
- API: `backend/app/api/v1/{agent,approvals,pin,chat,legal,market,whatsapp,health}.py`
- Config: `backend/app/core/{config,checkpointer,security,pin}.py`
- Migrasi: `backend/migrations/0001–0009`
- Frontend: `frontend/app/(protected)/*`, `frontend/lib/api-client.ts`, `middleware.ts`

**Riwayat perubahan:**
- v1.0 (2026-07-02): Draft awal, di-reverse-engineer dari kode saat ini.
