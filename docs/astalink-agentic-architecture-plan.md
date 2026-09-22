# AstaLink Context-Aware Financial Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengembangkan graph AstaLink menjadi financial coach yang memahami konteks keputusan, bertanya hanya ketika diperlukan, dan memanggil specialist secara selektif tanpa mengganti deterministic engines yang sudah kuat.

**Architecture:** Pertahankan deterministic ingress router dan POS Automation sebagai ingestion plane di luar advisory graph. Setelah pesan dipastikan bukan transaksi, tambahkan `DecisionContext`, temporal financial memory, dan coach/supervisor sebelum routing advisory yang ada. Coach memilih aksi melalui policy yang dapat diuji; market, business, risk, optimizer, dan compliance diperlakukan sebagai tools/subgraphs. Migrasi dilakukan bertahap dengan graph lama sebagai fallback sampai setiap fase lulus scenario tests dan POS regression tests.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, LangChain, Pydantic, Supabase/PostgreSQL, pytest, Gemini-compatible chat model, Next.js frontend yang sudah ada.

**Spec:** `docs/astalink-vision-positioning.md`

## Global Constraints

- AstaLink tetap advisory-only; chat tidak boleh mengeksekusi order.
- Semua input milik flow POS selalu dirutekan sebelum coach: business selection, transaction confirmation, teks transaksi, foto struk, dan audio transaksi. Kontrol composition gate yang flow-specific tetap menjadi input advisory dan tidak boleh salah diarahkan ke POS.
- Checkpoint POS dan advisory tetap memakai thread id terpisah.
- Coach hanya boleh membaca transaksi berstatus `confirmed`; ia tidak memiliki write path ke `business_transactions`.
- Transaksi pending, ditolak, atau dibatalkan tidak boleh masuk decision context maupun temporal memory sebagai fakta.
- Setiap angka finansial harus memiliki provenance: workspace data, user statement, verified evidence, estimate, atau explicit default.
- Unknown tidak boleh diubah menjadi fakta atau profil moderat secara diam-diam.
- Satu respons coaching hanya boleh meminta satu informasi yang paling menentukan.
- Hard financial constraints tetap deterministic dan tidak dapat dioverride LLM.
- Specialist failure harus terdegradasi secara eksplisit tanpa menghapus decision context.
- Semua perubahan database wajib memiliki RLS sesuai kepemilikan workspace.
- Jalur lama tetap tersedia sebagai fallback selama rollout.
- Tidak menambah dependency baru kecuali kebutuhan tidak dapat dipenuhi stack saat ini.
- Setiap implementation task dimulai dengan failing test dan berakhir dengan test suite relevan yang lulus. Task 0 adalah characterization-test exception: test harus lulus pada arsitektur lama untuk mengunci boundary sebelum perubahan.

## Review Focus

- Teks transaksi, struk, audio, dan jawaban konfirmasi POS harus tetap masuk POS Automation tanpa pernah diproses coach; kontrol advisory yang flow-specific harus tetap menyelesaikan flow advisory yang benar.
- Rujukan nominal yang ambigu harus memakai transaksi yang benar atau meminta klarifikasi, tidak memilih nominal secara acak.
- Fakta lama yang bertentangan dengan koreksi terbaru harus disupersede, bukan tetap memengaruhi keputusan.
- Data readiness yang hilang harus mencegah rekomendasi presisi, bukan diam-diam memakai profil moderat.
- Resume setelah interrupt harus mempertahankan decision episode dan tidak menjalankan specialist dua kali.

---

# Bagian A — Deskripsi Arsitektur Tujuan

## A1. Prinsip Desain

Arsitektur tujuan adalah **supervisor-led graph**, bukan sekumpulan autonomous agents yang saling berbicara tanpa kontrol. Satu coach/supervisor memiliki tanggung jawab atas percakapan dan next action. Specialist tidak mengambil alih hubungan dengan pengguna; mereka mengembalikan analisis terstruktur kepada coach.

Graph tetap diperlukan karena AstaLink membutuhkan:

- state eksplisit;
- jalur yang dapat diaudit;
- pause dan resume untuk pertanyaan pengguna;
- deterministic gates;
- pembatasan tool;
- recovery yang dapat diuji;
- pemisahan antara rekomendasi dan eksekusi.

Multi-agent digunakan hanya ketika pembagian domain memberi manfaat nyata. Menambah agent tanpa memperbaiki state, memory, dan decision policy hanya menghasilkan pipeline yang lebih mahal.

## A2. Bentuk Graph

Graph memiliki boundary luar yang tidak boleh dipindahkan ke supervisor:

```text
Channel input
     |
     v
Deterministic ingress router
  +--+-----------------------+
  |                          |
  v                          v
POS Automation         Advisory graph START
  |                          |
  v                          v
capture / confirm       coach/supervisor
  |
  v
confirmed transaction ledger -- read-only --> financial context
```

`START` pada diagram berikut berarti awal **advisory graph**, bukan awal semua pesan dari web atau WhatsApp. Pending business selection, pending transaction confirmation, foto struk, audio transaksi, dan teks yang terdeteksi sebagai transaksi harus selesai dirutekan sebelum titik ini.

```text
START
  │
  ▼
Load conversation + workspace + temporal memory
  │
  ▼
Build / update DecisionContext
  │
  ▼
Classify domain intent
  │
  ▼
Coach Policy ─────────────────────────────────────────┐
  │                                                   │
  ├─ ASK_ONE_QUESTION → Coach Reply → INTERRUPT ──────┤
  │                                                   │
  ├─ DISCUSS → Q&A tool ──────────────────────────────┤
  │                                                   │
  ├─ ANALYZE → Readiness Gate                         │
  │                  │                                │
  │                  ├─ NOT_READY → Coach Reply ──────┤
  │                  ├─ NEEDS_INFO → ASK ─────────────┤
  │                  └─ READY                         │
  │                       │                           │
  │                       ▼                           │
  │             Selective specialist fan-out          │
  │             Market / Business / Risk / Critic     │
  │                       │                           │
  │                       ▼                           │
  │              Deterministic optimizer              │
  │                       │                           │
  │                       ▼                           │
  │              Regulatory evidence check            │
  │                                                   │
  └─ RECORD_CONTEXT → persist memory ─────────────────┘
                              │
                              ▼
                      Coach Response Composer
                              │
                              ▼
                             END
```

## A3. DecisionContext

`DecisionContext` merepresentasikan satu keputusan aktif, bukan keseluruhan identitas pengguna. Contohnya adalah keputusan tentang Rp10 juta yang baru masuk.

Minimal field yang dibutuhkan:

```python
class DecisionContext(BaseModel):
    episode_id: str
    stage: DecisionStage
    user_goal: str | None
    amount: EvidenceValue[float] | None
    money_source: EvidenceValue[str] | None
    money_owner: EvidenceValue[str] | None
    purpose: EvidenceValue[str] | None
    needed_by: EvidenceValue[datetime] | None
    candidate_options: list[str]
    decisive_unknowns: list[UnknownField]
    understanding: str
    confidence: float
```

Nilai finansial memakai evidence wrapper agar model tidak dapat menyamakan user statement, database fact, dan inference.

## A4. Financial Memory

Memory dibagi menjadi tiga lapisan:

1. **Conversation memory:** turn terbaru untuk koherensi bahasa.
2. **Decision memory:** state dari keputusan aktif, termasuk pertanyaan yang sedang menunggu jawaban.
3. **Temporal financial memory:** fakta, preferensi, tujuan, dan observasi perilaku lintas waktu.

Temporal memory bersifat append-only. Koreksi membuat observasi baru yang menyupersede observasi lama; riwayat tidak dihapus. Setiap record membawa `observed_at`, `effective_from`, `confidence`, `source`, dan `supersedes_id`.

Habit tidak disimpan sebagai label permanen seperti `user_is_impulsive = true`. Habit disimpan sebagai observasi terbatas waktu, misalnya “dalam 90 hari terakhir, tiga dari empat surplus ditarik kembali dalam tujuh hari”. Coach boleh memakai observasi itu dengan menyebut periode dan uncertainty.

## A5. Coach/Supervisor

Coach melakukan judgment berikut:

- merangkum apa yang sedang diputuskan;
- membedakan known, inferred, dan unknown;
- memilih satu decisive unknown;
- memilih action: `ASK`, `DISCUSS`, `ANALYZE`, `RECORD`, atau `STOP`;
- memilih specialist yang diperlukan;
- memastikan hasil tool relevan terhadap tujuan pengguna;
- menyusun jawaban akhir.

Coach tidak boleh:

- menghitung bobot portofolio sendiri;
- mengarang data pasar;
- mengubah hard veto;
- menyimpan inferensi sebagai verified fact;
- mengeksekusi transaksi.

## A6. Coaching Policy

Policy harus deterministic sejauh memungkinkan. LLM membentuk kandidat konteks; policy memutuskan jalur menggunakan field dan rule yang dapat diuji.

Urutan prioritas:

1. Koreksi atau konflik konteks.
2. Pending composition confirmation. Pending transaction tidak boleh mencapai policy karena sudah ditangani ingress router.
3. Missing decisive readiness information.
4. Hard veto atau kondisi tidak siap.
5. Informational discussion.
6. Specialist analysis.
7. Sandbox recommendation.

`ASK` hanya dipilih bila satu jawaban dapat mengubah jalur atau rekomendasi. Unknown yang tidak material dicatat sebagai limitation dan tidak menghambat seluruh percakapan.

## A7. Specialist Boundaries

| Komponen | Bentuk | Tanggung jawab |
| --- | --- | --- |
| POS Automation | Deterministic pre-router + capture subgraph | Mengekstrak, meminta konfirmasi, dan menyimpan transaksi sebelum advisory |
| Coach | LLM + deterministic policy | Memahami keputusan dan memilih next action |
| Context builder | Structured LLM + validator | Mengekstrak candidate facts dan provenance |
| Readiness | Deterministic | Dana darurat, utang, horizon, kepemilikan dana, kebutuhan likuiditas |
| Market | Tool/subgraph | Data harga, berita, indikator, dan tesis saham |
| Business | Tool/subgraph | Kebutuhan modal dan kualitas bisnis |
| Risk | Deterministic + narration | Risk metrics dan loss capacity |
| Critic | Rules lebih dahulu, LLM opsional | Menguji asumsi dan kontradiksi |
| Optimizer | Deterministic | Bobot dan constraint solving |
| Compliance | Retrieval + grader | Memeriksa dukungan regulasi yang relevan |
| Response composer | LLM dengan schema | Pemahaman, arah, uncertainty, dan next step |

POS Automation bukan tool yang bebas dipanggil coach. Satu-satunya arah data normal adalah `confirmed transaction ledger -> financial context`. Mutation ledger hanya dilakukan capture graph setelah konfirmasi pengguna.

## A8. Respons Akhir

Response composer menerima hasil terstruktur, bukan state mentah. Kontrak keluarannya:

```python
class CoachReply(BaseModel):
    understanding: str
    direction: str
    uncertainty: str | None
    question: str | None
    disclosure: str | None
```

Renderer menggabungkan field menjadi bahasa natural. `question` maksimal satu. Untuk laporan panjang, tabel dan detail tetap dapat dirender deterministically setelah pembuka coaching.

## A9. Failure Model

- **Context model gagal:** gunakan context terakhir, tandai tidak diperbarui, dan jangan menulis memory baru.
- **Transaction detector tidak yakin:** jangan menyimpan candidate transaction sebagai memory. Gunakan capture clarification atau biarkan sebagai advisory tanpa mengklaim transaksi telah tercatat.
- **Pending POS flow:** deflect semua pesan nonjawaban ke prompt POS yang sedang menunggu; jangan membuat decision episode baru.
- **Memory store gagal:** lanjutkan turn memakai in-memory state; log dan tampilkan analisis tanpa mengklaim sudah mengingat.
- **Market data gagal:** jangan memakai expected return default seolah data aktual; tampilkan eksplorasi tanpa rekomendasi presisi.
- **Specialist gagal:** coach menyebut bagian analisis yang tidak tersedia dan tetap memakai hasil lain yang independen.
- **Compliance retrieval kosong:** status menjadi `unavailable`, bukan `rejected`; jangan mengulang optimizer dengan input identik.
- **Conflict:** prioritaskan verified recent fact, lalu explicit user correction, lalu claimed fact, lalu inference.

## A10. Batas Tahap Pertama

Versi pertama tidak perlu:

- agent-to-agent free-form conversation;
- autonomous long-running planning;
- vector memory untuk seluruh chat;
- predictive behavioral scoring kompleks;
- perubahan broker execution flow;
- rekomendasi lintas seluruh instrumen keuangan.

Fokus pertama adalah keputusan kas, bisnis, dan saham yang sudah berada dalam scope AstaLink.

---

# Bagian B — Rencana Implementasi

Rencana dibagi menjadi empat fase, dimulai dari Fase 0 untuk mengunci kompatibilitas POS Automation. Setiap fase dapat dirilis dan dirollback secara terpisah. Jangan menjalankan fase berikutnya sebelum acceptance tests fase sebelumnya lulus.

## Peta File

**File baru:**

- `backend/app/agents/coach/__init__.py` — package coach.
- `backend/app/agents/coach/schemas.py` — kontrak decision context dan coach action.
- `backend/app/agents/coach/context_builder.py` — ekstraksi konteks terstruktur.
- `backend/app/agents/coach/policy.py` — pemilihan next action deterministic.
- `backend/app/agents/coach/node.py` — adapter LangGraph.
- `backend/app/agents/coach/reply.py` — response composition.
- `backend/app/agents/memory/repository.py` — persistence decision episode dan observations.
- `backend/app/agents/readiness.py` — readiness gate personal.
- `backend/migrations/0018_financial_coach_memory.sql` — skema memory dan RLS.
- `backend/tests/test_coach_schemas.py`.
- `backend/tests/test_coach_context_builder.py`.
- `backend/tests/test_coach_policy.py`.
- `backend/tests/test_coach_graph.py`.
- `backend/tests/test_financial_memory.py`.
- `backend/tests/test_readiness.py`.
- `backend/tests/test_pos_advisory_boundary.py`.
- `backend/tests/test_coach_scenarios.py`.

**File yang dimodifikasi:**

- `backend/app/agents/state.py` — field coach dan reducers.
- `backend/app/agents/graph.py` — supervisor-led routing.
- `backend/app/agents/intent/node.py` — intent menjadi signal; hapus silent ticker selection.
- `backend/app/agents/allocation/schemas.py` — readiness/provenance output.
- `backend/app/agents/allocation/engine.py` — block/cap hasil berdasarkan readiness.
- `backend/app/agents/allocation/constraints.py` — notes menjadi output yang terlihat.
- `backend/app/agents/optimizer/node.py` — provenance untuk fallback assumptions.
- `backend/app/agents/legal/schemas.py` dan `legal/node.py` — status `unavailable`.
- `backend/app/agents/report.py` — coaching preface dan assumption disclosure.
- `backend/app/api/v1/chat.py` — decision episode lifecycle setelah POS pre-routing.
- `backend/app/api/v1/whatsapp.py` — memakai coach graph hanya pada advisory fallthrough; urutan POS tidak diubah.
- test yang sudah ada untuk graph, intent, allocation, legal, report, chat, WhatsApp, dan transaction capture.

## Fase 0 — Kunci Boundary POS Automation

### Task 0: Contract Tests untuk Ingestion Plane dan Advisory Plane

**Files:**
- Create: `backend/tests/test_pos_advisory_boundary.py`
- Reference: `backend/app/api/v1/chat.py:141-279`
- Reference: `backend/app/api/v1/whatsapp.py:208-409`
- Test: `backend/tests/test_transaction_capture_graph.py`
- Test: `backend/tests/test_whatsapp_transaction_capture_routing.py`

**Interfaces:**
- Consumes: channel input, pending transaction checkpoint, `looks_like_transaction`, dan `capture_graph`.
- Produces: invariant bahwa hanya advisory fallthrough yang boleh memanggil coach graph.

- [ ] **Step 1: Tulis characterization tests sebelum production code berubah**

```python
def test_web_receipt_invokes_capture_never_advisory(client, mock_capture, mock_advisory):
    response = post_receipt(client, amount=125_000)
    assert response.status_code == 200
    mock_capture.assert_called_once()
    mock_advisory.assert_not_called()

def test_confirmed_income_can_be_read_by_next_advisory_turn(client, confirmed_income):
    response = post_text(client, "Dari uang tadi, saham mana?")
    assert response.status_code == 200
    assert advisory_snapshot(response).recent_transactions[0].amount == 125_000

def test_cancelled_transaction_is_absent_from_confirmed_snapshot(client, pending_transaction):
    post_text(client, "tidak")
    assert load_snapshot(pending_transaction.workspace_id).recent_transactions == []
```

- [ ] **Step 2: Tambahkan parity cases untuk WhatsApp**

Kasus wajib: text transaction, image receipt, audio transaction, business selection, `txn_ya`, `txn_tidak`, serta plain `ya/tidak` ketika composition gate dan transaction confirmation sama-sama pending.

- [ ] **Step 3: Jalankan boundary tests pada graph lama**

Run: `cd backend; python -m pytest tests/test_pos_advisory_boundary.py tests/test_transaction_capture_graph.py tests/test_whatsapp_transaction_capture_routing.py -q`
Expected: PASS sebelum supervisor dibuat. Jika gagal, sesuaikan test dengan kontrak POS yang benar sebelum menyentuh supervisor; jangan memindahkan production routing ke coach.

- [ ] **Step 4: Commit contract tests**

```bash
git add backend/tests/test_pos_advisory_boundary.py
git commit -m "test(pos): lock transaction and advisory routing boundary"
```

## Fase 1 — Correctness Sebelum Supervisor

### Task 1: Surface Personal Readiness dan Missing Constraint

**Files:**
- Create: `backend/app/agents/readiness.py`
- Modify: `backend/app/agents/allocation/schemas.py:167`
- Modify: `backend/app/agents/allocation/engine.py:52`
- Modify: `backend/app/agents/report.py:54`
- Test: `backend/tests/test_readiness.py`
- Test: `backend/tests/test_allocation_engine.py`

**Interfaces:**
- Consumes: `InvestorProfile`, decision amount, dan `ConstraintResult`.
- Produces: `evaluate_readiness(profile, amount) -> ReadinessResult`.

- [ ] **Step 1: Tulis failing tests untuk profil kosong dan profil siap**

```python
def test_missing_decisive_fields_blocks_precise_allocation():
    result = evaluate_readiness(InvestorProfile(), amount=10_000_000)
    assert result.status == ReadinessStatus.NEEDS_INFO
    assert result.next_question.field == "monthly_expenses"

def test_complete_safe_profile_is_ready():
    profile = InvestorProfile(
        monthly_expenses=5_000_000,
        emergency_fund=30_000_000,
        capital_is_borrowed=False,
        horizon_months=60,
        net_worth=300_000_000,
    )
    assert evaluate_readiness(profile, 10_000_000).status == ReadinessStatus.READY
```

- [ ] **Step 2: Jalankan tests dan verifikasi kegagalan**

Run: `cd backend; python -m pytest tests/test_readiness.py tests/test_allocation_engine.py -q`
Expected: FAIL karena `readiness.py` dan status belum ada.

- [ ] **Step 3: Implementasikan schema dan gate minimal**

```python
class ReadinessStatus(StrEnum):
    READY = "ready"
    NEEDS_INFO = "needs_info"
    NOT_READY = "not_ready"

class ReadinessResult(BaseModel):
    status: ReadinessStatus
    blocking_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    next_question: IntakeQuestion | None = None
```

`evaluate_readiness` harus memprioritaskan pengeluaran bulanan, dana darurat, asal modal, horizon, lalu net worth. `run_layer0` tidak boleh menghasilkan split presisi ketika status `NEEDS_INFO`.

- [ ] **Step 4: Tampilkan readiness notes pada report**

Tambahkan section `Kesiapan Dana` yang membedakan blocker, warning, dan data lengkap. Jangan memakai kata “lolos” untuk readiness.

- [ ] **Step 5: Jalankan test fase ini**

Run: `cd backend; python -m pytest tests/test_readiness.py tests/test_allocation_engine.py tests/test_allocation_constraints.py tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 6: Commit task**

```bash
git add backend/app/agents/readiness.py backend/app/agents/allocation backend/app/agents/report.py backend/tests
git commit -m "feat(coach): enforce personal readiness before allocation"
```

### Task 2: Hilangkan Silent Defaults dan Tambahkan Assumption Provenance

**Files:**
- Modify: `backend/app/agents/intent/node.py:42,269-301`
- Modify: `backend/app/agents/optimizer/node.py:38-101`
- Modify: `backend/app/agents/allocation/schemas.py`
- Test: `backend/tests/test_intent_classifier.py`
- Test: `backend/tests/test_optimizer_node.py`

**Interfaces:**
- Produces: `entities.analysis_universe_source` dan `allocation_plan.assumptions`.

- [ ] **Step 1: Tulis failing tests**

```python
def test_generic_allocation_does_not_silently_choose_blue_chips():
    update = run_intent("Dana 10 juta enaknya masuk saham apa?")
    assert update["entities"].get("tickers") in (None, [])
    assert update["entities"].get("needs_universe_choice") is True

def test_optimizer_labels_market_fallbacks():
    plan = optimizer_node(state_without_price_history)["allocation_plan"]
    assert "historical_return_unavailable" in plan["assumptions"]
```

- [ ] **Step 2: Jalankan tests dan pastikan gagal**

Run: `cd backend; python -m pytest tests/test_intent_classifier.py tests/test_optimizer_node.py -q`.

- [ ] **Step 3: Hapus penyisipan `DEFAULT_ALLOCATION_TICKERS` dari intent path**

Pertahankan default watchlist pada halaman market, tetapi jangan mengubahnya menjadi rekomendasi personal. Generic request menghasilkan kebutuhan memilih universe atau mode eksplorasi yang dilabeli.

- [ ] **Step 4: Tambahkan provenance pada optimizer**

```python
class AllocationPlan(BaseModel):
    # existing fields
    assumptions: list[str] = Field(default_factory=list)
    data_quality: str = "actual"
```

Jika `_DEFAULT_EXPECTED_RETURN` atau `_DEFAULT_VARIANCE` terpakai, set `data_quality="estimated"` dan cap confidence downstream.

- [ ] **Step 5: Jalankan regression tests**

Run: `cd backend; python -m pytest tests/test_intent_classifier.py tests/test_optimizer_node.py tests/test_market_node.py tests/test_chat_agent.py -q`
Expected: PASS.

- [ ] **Step 6: Commit task**

```bash
git add backend/app/agents/intent backend/app/agents/optimizer backend/app/agents/allocation/schemas.py backend/tests
git commit -m "fix(ai): expose allocation assumptions and remove silent stock defaults"
```

## Fase 2 — Decision Context dan Coach/Supervisor

### Task 3: Tambahkan DecisionContext ke Shared State

**Files:**
- Create: `backend/app/agents/coach/__init__.py`
- Create: `backend/app/agents/coach/schemas.py`
- Modify: `backend/app/agents/state.py:59-96`
- Test: `backend/tests/test_coach_schemas.py`

**Interfaces:**
- Produces: `EvidenceValue`, `DecisionContext`, `CoachAction`, dan `CoachDecision`.

- [ ] **Step 1: Tulis schema contract tests**

```python
def test_inference_cannot_claim_verified_evidence():
    with pytest.raises(ValidationError):
        EvidenceValue(value=10_000_000, evidence="verified", source="llm_inference")

def test_coach_decision_allows_at_most_one_question():
    with pytest.raises(ValidationError):
        CoachDecision(action="ask", questions=["Satu?", "Dua?"])
```

- [ ] **Step 2: Jalankan test untuk memastikan gagal**

Run: `cd backend; python -m pytest tests/test_coach_schemas.py -q`.

- [ ] **Step 3: Implementasikan schema**

```python
class CoachAction(StrEnum):
    ASK = "ask"
    DISCUSS = "discuss"
    ANALYZE = "analyze"
    RECORD = "record"
    STOP = "stop"

class DecisionStage(StrEnum):
    UNDERSTANDING = "understanding"
    READINESS = "readiness"
    EXPLORATION = "exploration"
    RECOMMENDATION = "recommendation"
    COMPLETE = "complete"
```

Tambahkan validator provenance dan validator maksimal satu pertanyaan.

- [ ] **Step 4: Tambahkan field state**

```python
decision_context: dict[str, Any] | None
coach_decision: dict[str, Any] | None
memory_observations: list[dict[str, Any]]
```

Pastikan `new_state()` memberi nilai awal eksplisit agar data turn sebelumnya tidak bocor.

- [ ] **Step 5: Jalankan tests**

Run: `cd backend; python -m pytest tests/test_coach_schemas.py tests/test_state.py -q`
Expected: PASS.

- [ ] **Step 6: Commit task**

```bash
git add backend/app/agents/coach backend/app/agents/state.py backend/tests
git commit -m "feat(coach): define decision context contracts"
```

### Task 4: Persist Decision Episodes dan Temporal Observations

**Files:**
- Create: `backend/migrations/0018_financial_coach_memory.sql`
- Create: `backend/app/agents/memory/__init__.py`
- Create: `backend/app/agents/memory/repository.py`
- Modify: `backend/tests/test_migrations.py`
- Test: `backend/tests/test_financial_memory.py`

**Interfaces:**
- Produces: `load_active_episode`, `save_episode`, `append_observation`, `load_relevant_observations`, dan `supersede_observation`.

- [ ] **Step 1: Tulis migration dan repository failing tests**

```python
def test_newer_user_correction_supersedes_old_inference():
    old = repo.append_observation(ws, key="habit.surplus_use", value="spent",
                                  evidence="inferred", confidence=0.6)
    new = repo.append_observation(ws, key="habit.surplus_use", value="saved",
                                  evidence="claimed", confidence=0.9,
                                  supersedes_id=old.id)
    assert repo.load_relevant_observations(ws, ["habit.surplus_use"]) == [new]
```

- [ ] **Step 2: Tambahkan tabel**

```sql
create table public.decision_episodes (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  thread_id text not null,
  status text not null check (status in ('active','complete','cancelled')),
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.financial_observations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  key text not null,
  value jsonb not null,
  evidence text not null,
  confidence double precision not null check (confidence between 0 and 1),
  source text not null,
  observed_at timestamptz not null default now(),
  effective_from timestamptz,
  supersedes_id uuid references public.financial_observations(id),
  metadata jsonb not null default '{}'::jsonb
);
```

Tambahkan index `(workspace_id, thread_id, status)` dan `(workspace_id, key, observed_at desc)`, RLS select/insert/update berbasis owner workspace, serta trigger `updated_at` untuk episode.

- [ ] **Step 3: Implementasikan repository best-effort**

Read failure mengembalikan empty context dan error marker; write failure tidak boleh mengubah fakta menjadi tersimpan. Repository tidak boleh melakukan reasoning.

- [ ] **Step 4: Jalankan migration dan repository tests**

Run: `cd backend; python -m pytest tests/test_migrations.py tests/test_financial_memory.py -q`
Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add backend/migrations/0018_financial_coach_memory.sql backend/app/agents/memory backend/tests
git commit -m "feat(memory): persist decision episodes and temporal observations"
```

### Task 5: Bangun Context Builder dengan Provenance Validation

**Files:**
- Create: `backend/app/agents/coach/context_builder.py`
- Modify: `backend/app/agents/context_snapshot.py`
- Test: `backend/tests/test_coach_context_builder.py`

**Interfaces:**
- Consumes: message terbaru, history, `WorkspaceSnapshot`, active episode, observations.
- Produces: `build_decision_context(...) -> ContextBuildResult`.

- [ ] **Step 1: Tulis failing tests untuk nominal, konflik, dan unsupported fact**

```python
def test_resolves_recent_income_but_keeps_purpose_unknown():
    result = build_with_snapshot("Dari uang tadi, saham mana?", income=4_100_000)
    assert result.context.amount.value == 4_100_000
    assert result.context.amount.source == "workspace_transaction"
    assert "purpose" in result.context.decisive_unknown_fields

def test_rejects_number_not_present_in_sources():
    result = build_with_model_output(amount=9_999_999, available_numbers=[4_100_000])
    assert result.context.amount is None
    assert "unsupported_amount" in result.validation_errors
```

- [ ] **Step 2: Jalankan tests dan pastikan gagal**

Run: `cd backend; python -m pytest tests/test_coach_context_builder.py -q`.

- [ ] **Step 3: Implementasikan structured extraction**

Prompt harus meminta candidate facts beserta exact source reference. Validator setelah LLM memastikan nominal, tanggal, ticker, dan nama bisnis terdapat pada message, history, snapshot, atau memory input.

- [ ] **Step 4: Implementasikan conflict precedence**

Urutan: recent verified fact → explicit current-turn correction → recent claimed fact → estimate → inference. Conflict yang tidak dapat diselesaikan menjadi `decisive_unknown`, bukan dipilih acak.

- [ ] **Step 5: Jalankan tests**

Run: `cd backend; python -m pytest tests/test_coach_context_builder.py tests/test_context_snapshot.py tests/test_gemini_client.py -q`
Expected: PASS.

- [ ] **Step 6: Commit task**

```bash
git add backend/app/agents/coach/context_builder.py backend/app/agents/context_snapshot.py backend/tests
git commit -m "feat(coach): build evidence-aware decision context"
```

### Task 6: Implementasikan Coaching Policy

**Files:**
- Create: `backend/app/agents/coach/policy.py`
- Test: `backend/tests/test_coach_policy.py`

**Interfaces:**
- Consumes: `DecisionContext`, intent decision, readiness result, pending interrupts.
- Produces: `choose_next_action(...) -> CoachDecision`.

- [ ] **Step 1: Tulis policy matrix tests**

```python
@pytest.mark.parametrize((case, expected), [
    ("pending_confirmation", CoachAction.STOP),
    ("missing_liquidity_horizon", CoachAction.ASK),
    ("general_question", CoachAction.DISCUSS),
    ("ready_allocation", CoachAction.ANALYZE),
])
def test_policy_matrix(case, expected):
    assert choose_case(case).action == expected
```

Tambahkan assertion bahwa `ASK` selalu memiliki understanding, direction, dan tepat satu question.

- [ ] **Step 2: Jalankan test dan pastikan gagal**

Run: `cd backend; python -m pytest tests/test_coach_policy.py -q`.

- [ ] **Step 3: Implementasikan pure policy function**

Policy tidak memanggil LLM atau database. Ia hanya memutuskan action dan required specialists berdasarkan input terstruktur.

- [ ] **Step 4: Tambahkan specialist selection tests**

Kasus business-vs-stock harus memilih `business`, `market`, dan `risk`; stock explanation hanya memilih `market`; hard readiness veto tidak memanggil specialist apa pun.

- [ ] **Step 5: Jalankan tests dan commit**

Run: `cd backend; python -m pytest tests/test_coach_policy.py -q`
Expected: PASS.

```bash
git add backend/app/agents/coach/policy.py backend/tests/test_coach_policy.py
git commit -m "feat(coach): add deterministic coaching policy"
```

### Task 7: Integrasikan Supervisor ke LangGraph di Balik Feature Flag

**Files:**
- Create: `backend/app/agents/coach/node.py`
- Modify: `backend/app/agents/graph.py:36-178`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/v1/chat.py:266-322`
- Modify: `backend/app/api/v1/whatsapp.py:391-414`
- Test: `backend/tests/test_coach_graph.py`
- Test: `backend/tests/test_graph_wiring.py`
- Test: `backend/tests/test_pos_advisory_boundary.py`
- Test: `backend/tests/test_whatsapp_transaction_capture_routing.py`

**Interfaces:**
- Consumes: hanya advisory fallthrough setelah POS routing selesai.
- Produces nodes `coach_context`, `coach_policy`, `coach_ask` dan router `_route_after_coach`.
- Feature flag: `FINANCIAL_COACH_GRAPH_ENABLED=false` secara default pada awal rollout.

- [ ] **Step 1: Tulis graph routing tests**

```python
def test_missing_decisive_context_ends_with_one_question():
    final = invoke_coach_graph("Dari uang tadi, saham mana?", incomplete_profile)
    assert final["coach_decision"]["action"] == "ask"
    assert count_questions(final["messages"][-1].content) == 1
    assert final.get("allocation_plan") is None

def test_ready_context_routes_to_existing_layer0():
    assert route_for(ready_stock_context) == "l0_allocation"

def test_receipt_and_pending_transaction_never_reach_coach():
    assert ingress_route(receipt_message) == "transaction_capture"
    assert ingress_route(transaction_confirmation) == "transaction_resume"
```

- [ ] **Step 2: Jalankan tests dan verifikasi gagal**

Run: `cd backend; python -m pytest tests/test_coach_graph.py tests/test_graph_wiring.py -q`.

- [ ] **Step 3: Tambahkan supervisor nodes sebelum routing advisory lama**

Ketika flag mati, gunakan graph lama tanpa perubahan perilaku. Ketika flag hidup, jalur advisory menjadi `START → coach_context → n1_intent → coach_policy` lalu menuju node lama yang relevan. Jangan memindahkan pending transaction handling, photo/audio handling, `has_transaction_shape`, atau `looks_like_transaction` ke dalam graph ini. Web dan WhatsApp harus memilih advisory graph hanya pada fallthrough yang sekarang memanggil `graph.invoke`.

- [ ] **Step 4: Persist episode sebelum interrupt dan setelah completion**

Gunakan `_thread_id` dan `_workspace_id` yang sudah ada. Resume harus membaca episode yang sama dan idempotency test memastikan specialist tidak dijalankan dua kali.

- [ ] **Step 5: Jalankan graph, checkpoint, dan chat tests**

Run: `cd backend; python -m pytest tests/test_coach_graph.py tests/test_graph_wiring.py tests/test_checkpointer.py tests/test_chat.py tests/test_pos_advisory_boundary.py tests/test_whatsapp_transaction_capture_routing.py -q`
Expected: PASS pada flag on dan off.

- [ ] **Step 6: Commit task**

```bash
git add backend/app/agents/coach backend/app/agents/graph.py backend/app/core/config.py backend/app/api/v1/chat.py backend/app/api/v1/whatsapp.py backend/tests
git commit -m "feat(graph): add feature-flagged coach supervisor"
```

## Fase 3 — Conversational Learning dan Specialist Semantics

### Task 8: Simpan Jawaban Chat sebagai Claimed Context

**Files:**
- Create: `backend/app/agents/coach/profile_updates.py`
- Modify: `backend/app/agents/coach/node.py`
- Modify: `backend/app/agents/allocation/node.py:108-161`
- Test: `backend/tests/test_coach_profile_updates.py`

**Interfaces:**
- Produces: `propose_profile_updates(context) -> list[ProfileUpdate]` dan `apply_allowed_updates(...)`.

- [ ] **Step 1: Tulis allowlist dan evidence tests**

```python
def test_chat_answer_is_stored_as_claimed_not_verified():
    updates = extract_updates("Dana ini tidak dipakai sampai 5 tahun lagi")
    assert updates[0].field == "horizon_months"
    assert updates[0].evidence == "claimed"

def test_unrequested_field_cannot_be_overwritten():
    assert apply_allowed_updates(existing, malicious_updates).net_worth == existing.net_worth

def test_transaction_message_without_pending_coach_question_is_not_profile_update():
    updates = extract_updates("jual kopi 125 ribu", pending_field=None)
    assert updates == []

def test_cancelled_or_pending_transaction_is_not_memory_source():
    assert propose_profile_updates(context_from_unconfirmed_transaction) == []
```

- [ ] **Step 2: Implementasikan update allowlist**

Hanya field yang sedang ditanyakan oleh coach atau dikoreksi eksplisit boleh berubah. Extractor wajib menerima `pending_field`; tanpa pending field, pesan bernominal tidak boleh dianggap sebagai jawaban profil. Verified value tidak boleh ditimpa claimed value tanpa menyimpan conflict observation.

- [ ] **Step 3: Hubungkan update ke resume path**

Setelah jawaban terhadap coach diterima: update decision episode, append observation, perbarui investor/business profile bila field termasuk schema, lalu jalankan ulang readiness dan policy. Data dari POS hanya boleh masuk sebagai konteks melalui snapshot transaksi `confirmed`; pending, rejected, dan cancelled transaction dilarang menjadi memory observation.

- [ ] **Step 4: Jalankan tests**

Run: `cd backend; python -m pytest tests/test_coach_profile_updates.py tests/test_composition_gate_resume.py tests/test_transaction_capture_resume.py tests/test_pos_advisory_boundary.py -q`
Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add backend/app/agents/coach backend/app/agents/allocation/node.py backend/tests
git commit -m "feat(coach): learn claimed financial context from chat"
```

### Task 9: Perbaiki Compliance Semantics dan Retry

**Files:**
- Modify: `backend/app/agents/legal/schemas.py`
- Modify: `backend/app/agents/legal/node.py:149-188`
- Modify: `backend/app/agents/graph.py:113-124`
- Modify: `backend/app/agents/report.py`
- Test: `backend/tests/test_legal_node.py`
- Test: `backend/tests/test_graph_wiring.py`

**Interfaces:**
- Produces status `approved`, `partial`, `rejected`, atau `unavailable`.

- [ ] **Step 1: Tulis failing test untuk empty retrieval**

```python
def test_empty_retrieval_is_unavailable_and_does_not_reoptimize():
    final = invoke_with_empty_legal_retrieval()
    assert final["legal_status"] == "unavailable"
    assert final["revision_count"] == 1
```

- [ ] **Step 2: Implementasikan status dan route**

`unavailable` berakhir pada report dengan disclosure “pemeriksaan regulasi tidak tersedia”. Hanya rejection yang memiliki feedback konkret dan dapat mengubah constraint yang boleh kembali ke optimizer.

- [ ] **Step 3: Ubah copy report**

Gunakan “pemeriksaan bukti regulasi” dan jelaskan bahwa status tersebut bukan penilaian suitability, keamanan, atau potensi imbal hasil.

- [ ] **Step 4: Jalankan tests**

Run: `cd backend; python -m pytest tests/test_legal_node.py tests/test_legal_grader.py tests/test_graph_wiring.py tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add backend/app/agents/legal backend/app/agents/graph.py backend/app/agents/report.py backend/tests
git commit -m "fix(compliance): distinguish unavailable evidence from rejection"
```

### Task 10: Tambahkan Coach Response Composer

**Files:**
- Create: `backend/app/agents/coach/reply.py`
- Modify: `backend/app/agents/chat_agent.py`
- Modify: `backend/app/agents/report.py`
- Test: `backend/tests/test_coach_reply.py`
- Test: `backend/tests/test_chat_agent.py`

**Interfaces:**
- Consumes: `DecisionContext`, `CoachDecision`, readiness, specialist outputs, dan report.
- Produces: `compose_coach_reply(...) -> CoachReply` dan rendered string.

- [ ] **Step 1: Tulis reply contract tests**

```python
def test_uncertain_reply_reflects_before_asking():
    reply = compose_case("business_income_missing_horizon")
    assert reply.understanding
    assert reply.direction
    assert reply.question.count("?") == 1

def test_reply_never_claims_estimate_as_workspace_fact():
    reply = compose_with_estimated_market_data()
    assert "perkiraan" in reply.render().lower()
```

- [ ] **Step 2: Implementasikan structured composer**

LLM menghasilkan `CoachReply`; validator memastikan question count, allowed numbers, dan disclosure. Jika LLM gagal, renderer deterministik memakai field context dan policy, bukan fallback generik yang menghapus topik.

- [ ] **Step 3: Letakkan coaching preface sebelum report**

Report detail lama tetap dipakai. Coach menambahkan pemahaman, arah, dan uncertainty di atas report, bukan menulis ulang seluruh kalkulasi.

- [ ] **Step 4: Jalankan tests**

Run: `cd backend; python -m pytest tests/test_coach_reply.py tests/test_chat_agent.py tests/test_reply_writer.py tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add backend/app/agents/coach/reply.py backend/app/agents/chat_agent.py backend/app/agents/report.py backend/tests
git commit -m "feat(coach): compose context-first financial guidance"
```

### Task 11: Tambahkan End-to-End Conversation Scenarios dan Metrics

**Files:**
- Create: `backend/tests/test_coach_scenarios.py`
- Modify: `backend/app/core/metrics.py`
- Modify: `grafana/dashboards/ai-quality.json`
- Test: `backend/tests/test_metrics.py`
- Test: `backend/tests/test_pos_advisory_boundary.py`
- Test: `backend/tests/test_whatsapp_transaction_capture_routing.py`

**Interfaces:**
- Produces metrics `coach_action_total`, `coach_question_total`, `readiness_block_total`, `context_conflict_total`, `memory_write_failure_total`, `specialist_call_total`, dan `ingress_route_total{route="pos|advisory"}`.

- [ ] **Step 1: Tulis scenario fixtures**

Wajib mencakup:

```text
1. Catat pemasukan X → tanya “dari X saham mana?” → refleksi + horizon question.
2. User menjawab dana masih untuk payroll → no stock analysis.
3. User mengoreksi kebiasaan lama → recent correction supersedes inference.
4. Profil lengkap dan dana bebas → market/risk/optimizer berjalan sekali.
5. Tidak menyebut ticker → tidak ada silent blue-chip basket.
6. Market data gagal → tidak ada precise allocation dari hidden defaults.
7. Compliance retrieval kosong → report tetap jujur tanpa optimizer loop.
8. Resume setelah restart → episode dan pending question tetap sama.
9. Teks pemasukan bisnis → capture graph, coach tidak dipanggil.
10. Foto struk web/WhatsApp → capture graph, coach tidak dipanggil.
11. Audio transaksi WhatsApp → capture graph, coach tidak dipanggil.
12. Pending transaction + `txn_ya/txn_tidak` → resume POS thread yang sama.
13. Transaksi dibatalkan → tidak muncul pada snapshot atau temporal memory.
14. Transaksi X confirmed → turn advisory berikutnya boleh membaca X secara read-only.
15. Pending transaction dan composition gate bersamaan → button id menyelesaikan flow yang tepat.
```

- [ ] **Step 2: Jalankan scenarios pada graph baru**

Run: `cd backend; python -m pytest tests/test_coach_scenarios.py tests/test_pos_advisory_boundary.py tests/test_whatsapp_transaction_capture_routing.py -q`
Expected: FAIL sebelum seluruh integrasi selesai.

- [ ] **Step 3: Instrumentasikan action dan failure metrics**

Label hanya memakai enum bounded; jangan menaruh user id, nominal, message, atau business name di Prometheus labels.

- [ ] **Step 4: Perbarui dashboard AI quality**

Tambahkan panel action mix, ask rate, readiness blocks, specialist calls per completed analysis, memory failures, context conflicts, serta rasio ingress POS vs advisory. Jangan mengirim isi transaksi sebagai metric label.

- [ ] **Step 5: Jalankan full backend suite**

Run: `cd backend; python -m pytest -q`
Expected: seluruh suite PASS.

- [ ] **Step 6: Jalankan smoke test container**

Run: `docker compose exec backend python -m pytest tests/test_smoke.py tests/test_coach_scenarios.py tests/test_pos_advisory_boundary.py tests/test_whatsapp_transaction_capture_routing.py -q`
Expected: PASS dengan service dependencies aktif.

- [ ] **Step 7: Commit task**

```bash
git add backend/tests/test_coach_scenarios.py backend/tests/test_pos_advisory_boundary.py backend/app/core/metrics.py backend/tests/test_metrics.py grafana/dashboards/ai-quality.json
git commit -m "test(coach): add financial coaching scenarios and quality metrics"
```

## Rollout dan Rollback

1. Deploy dengan `FINANCIAL_COACH_GRAPH_ENABLED=false`.
2. Rekam baseline keberhasilan capture teks, foto, audio, business selection, confirmation, dan cancellation pada POS Automation.
3. Jalankan scenario suite, POS boundary suite, WhatsApp routing suite, dan smoke test pada environment deployment.
4. Aktifkan untuk internal/demo workspace melalui allowlist sebelum flag global.
5. Bandingkan ask rate, completion, latency, specialist calls, failure rate, serta POS capture success dengan graph lama.
6. Aktifkan bertahap untuk workspace tambahan.
7. Rollback cukup mematikan flag; data decision episode dan observations tetap tersimpan tetapi tidak dibaca graph lama, sedangkan POS thread tetap berjalan tanpa migrasi.

Kriteria menghentikan rollout:

- rekomendasi keluar tanpa readiness yang cukup;
- nominal atau sumber uang salah;
- teks transaksi, foto struk, audio, atau jawaban konfirmasi mencapai coach;
- POS capture success turun dibanding baseline;
- transaksi pending, ditolak, atau dibatalkan muncul sebagai financial memory;
- pertanyaan berulang setelah sudah dijawab;
- specialist dipanggil dua kali setelah resume;
- latency p95 atau error rate melampaui batas operasional yang disepakati sebelum rollout.

## Definition of Done

- Semua task dan scenario tests lulus.
- Tidak ada `TBD`, hidden default, atau unknown yang berubah menjadi fakta tanpa provenance.
- Graph baru dapat dimatikan tanpa migrasi balik.
- Decision episode bertahan lintas turn dan restart.
- Koreksi pengguna menyupersede inference lama.
- Missing decisive readiness menghasilkan satu pertanyaan, bukan rekomendasi.
- Existing market, business, risk, optimizer, transaction capture, dan execution safety tests tetap lulus.
- Web dan WhatsApp selalu merutekan POS sebelum advisory, baik saat feature flag mati maupun hidup.
- Coach tidak memiliki write path ke `business_transactions` dan hanya membaca transaksi confirmed.
- Pending, rejected, dan cancelled transaction tidak masuk decision context atau temporal memory sebagai fakta.
- Report membedakan readiness, market analysis, dan regulatory evidence.
- README diperbarui hanya setelah implementasi benar-benar selesai dan diverifikasi.

## Execution Boundary

Dokumen ini adalah rencana implementasi, bukan persetujuan untuk menjalankannya. Sebelum Task 0 dimulai, pengguna perlu meninjau kedua dokumen, mengoreksi keputusan produk yang tidak sesuai, dan memilih metode eksekusi.
