# AstaLink Proposal 2 — GForm Narrative Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the complete written answers for all 32 required fields of the Digdaya x Hackathon 2026 "2nd Submission" Google Form for team MUMET's project *AstaLink: AI Chief Investment Officer*, delivered as three files — `.md`, `.docx`, and `.pdf`.

**Architecture:** A single hand-authored master Markdown file (`proposal_2_answers.md`) holds the final narrative for every form field, in formal Bahasa Indonesia. A small Python build script (`build_docx.py`, using the already-installed `python-docx`) renders that content into a styled `.docx`. LibreOffice headless converts the `.docx` into the final `.pdf` (guaranteeing the PDF matches the DOCX exactly). No new dependencies are installed — `python-docx 1.2.0`, `markdown 3.9`, and `libreoffice`/`soffice` are confirmed present; `pandoc` is **not** available and must not be used.

**Tech Stack:** Markdown · Python 3 + `python-docx` · LibreOffice headless (`soffice --convert-to pdf`).

**Source-of-truth inputs (already read during planning):**
- `docs/proposal_2/reference/gform/{1..10}.jpeg` — the 32 form questions (transcribed in Appendix A).
- `docs/proposal_2/reference/notion/{1..4}.png` — Draft Proposal 2 (problem/sub-problem, "What", problem validation interview *questions*, CJM, problem–solution mapping, ecosystem alignment, solution approach, current status = Prototype).
- `docs/proposal_2/reference/team_information.txt` — team name & composition.
- `docs/proposal_2/reference/proposal_1.pdf` — the 1st submission (18 pages), the baseline for "Progress Since the 1st Submission".
- Live codebase inventory (FastAPI + LangGraph 8-node pipeline, hybrid legal RAG, HITL with PIN, Supabase + RLS, Docker/Grafana/Prometheus, Next.js frontend) — grounds every codebase-derived answer and the honest progress narrative.

**Authoring rules (apply to ALL narrative):**
1. Language: formal Bahasa Indonesia, ringkas, langsung ke inti (mirroring proposal 1's register and the panitia's *Ketentuan Penulisan*).
2. Avoid excessive untranslated jargon; when a technical term is used, give a one-clause gloss.
3. Be **honest** about current build state. Claim only what the codebase actually contains; frame not-yet-built items (regulation ingest, agentic chat UI, real broker, DeepEval slow suite) as the forward roadmap, never as done.
4. **User interview is NOT yet conducted.** Anywhere an answer would rest on primary user interviews/surveys (chiefly *Evidence of Demand*, and the interview portion of *Problem Validation*), leave the primary-research portion explicitly empty with the marker `[Riset primer — wawancara & shadowing pengguna: dijadwalkan, belum dilaksanakan]`. Secondary/desk data (SNLIK, BPS, SID) MAY still be cited.
5. `ID Tim` is unknown (blank in `team_information.txt`). Output the placeholder `[ISI ID TIM SESUAI DATA PENDAFTARAN]` and flag it for the user at the end. Do not invent an ID.

---

## File Structure

| File | Responsibility |
|---|---|
| `docs/proposal_2/output/proposal_2_answers.md` | Master narrative — all 32 answers, the canonical deliverable. Edited by humans. |
| `docs/proposal_2/output/build_docx.py` | Build script: parses the master `.md` and emits the `.docx`. One responsibility: MD→DOCX rendering. |
| `docs/proposal_2/output/AstaLink_Proposal_2.docx` | Generated DOCX (do not hand-edit; regenerate from `.md`). |
| `docs/proposal_2/output/AstaLink_Proposal_2.pdf` | Generated PDF (from DOCX via LibreOffice). Final form attachment. |

The `.md` is the single source of truth; `.docx` and `.pdf` are derived artifacts. Changing an answer = edit `.md`, rerun the two build steps.

---

## Task 1: Scaffold the master answers Markdown

**Files:**
- Create: `docs/proposal_2/output/proposal_2_answers.md`

- [ ] **Step 1: Write the master Markdown file with ALL final answers**

Create `docs/proposal_2/output/proposal_2_answers.md` with the exact content below. This is the finished narrative — execution is transcription, not authorship.

````markdown
# AstaLink: AI Chief Investment Officer — 2nd Submission

**Digdaya x Hackathon 2026 — Pusat Inovasi Digital Indonesia 2026**

---

## 1. ID Tim

[ISI ID TIM SESUAI DATA PENDAFTARAN]

## 2. Nama Tim

MUMET

## 3. Proposal Title

AstaLink: AI Chief Investment Officer

## 4. Team Composition

Tim MUMET — Politeknik Elektronika Negeri Surabaya (PENS), Program Studi Sains Data Terapan:

1. **Sabrina Humaira** — Team Leader, Project Lead & AI Strategy. Memimpin arah produk, strategi AI, dan koordinasi tim.
2. **Bistiana Syafina Ridho** — Frontend & Product Designer. Merancang antarmuka dan pengalaman pengguna (dashboard web & alur persetujuan).
3. **Kriza Fauzi Nafi'ubadah** — AI & Data Engineer. Membangun pipeline AI multi-agen, RAG, dan rekayasa data.
4. **Mohammad Ariel Sulton** — Backend Engineer. Membangun layanan backend, integrasi, keamanan, dan infrastruktur.

Empat mahasiswa Sains Data Terapan dengan keahlian saling melengkapi di bidang AI/data engineering, backend, serta frontend dan product design — relevan untuk merancang dan mengimplementasikan solusi AstaLink yang kuat secara teknologi sekaligus praktis digunakan.

## 5. Executive Summary

AstaLink adalah platform **AI Chief Investment Officer (AI-CIO) semi-otonom** yang membantu individu dan pelaku UMKM mengelola serta mengoptimalkan aset keuangan secara efisien tanpa menuntut keahlian investasi mendalam.

**Masalah utama** yang kami selesaikan adalah *analysis paralysis* dan **aset menganggur (idle assets)**: banyak pemilik dana memiliki arus kas stabil namun gagal menumbuhkan asetnya karena keterbatasan waktu, literasi pasar modal yang rendah, dan kompleksitas regulasi.

**Pendekatan solusi:** AstaLink mengorkestrasi AI multi-agen (LangGraph) yang menjalankan riset pasar, analisis bisnis, dan penilaian risiko secara paralel, lalu menyusun alokasi aset melalui mesin optimisasi yang **patuh regulasi** — divalidasi terhadap dokumen OJK menggunakan Retrieval-Augmented Generation (RAG). Setiap rekomendasi wajib melewati gerbang **Human-in-the-Loop (HITL)**: pengguna adalah pemegang kendali final yang menyetujui eksekusi lewat persetujuan ber-PIN. Interaksi dilakukan melalui WhatsApp (zero-friction) dan dashboard web.

**Dampak utama yang ditargetkan:** meningkatkan inklusi dan literasi investasi, mengaktifkan aset menganggur menjadi produktif, dan memperkuat ketahanan finansial pelaku UMKM — sejalan dengan tema penguatan ketahanan dan inovasi keuangan serta pertumbuhan ekonomi digital Indonesia.

## 6. Problem Statement

**Penguatan Ketahanan dan Inovasi Keuangan.**

Secara spesifik: rendahnya kemampuan individu dan pelaku UMKM untuk menumbuhkan dan melindungi aset mereka secara mandiri, akibat tingginya hambatan waktu, literasi, dan kepatuhan regulasi dalam berinvestasi.

## 7. Primary Sub-Problem Statement

Sub-problem utama: **Memperluas Investor Ritel** melalui tiga kebutuhan yang saling terkait:

1. **Asisten Keuangan Pribadi** — pengguna membutuhkan pendamping yang membantu memantau dan menata kondisi keuangan pribadi/bisnis secara konsisten, tanpa harus membuka banyak aplikasi atau menyita waktu.
2. **Penasihat Investasi Keuangan** — pengguna membutuhkan analisis pasar, perbandingan opsi investasi, dan strategi alokasi yang dapat dipahami tanpa keahlian finansial mendalam.
3. **Rekomendasi Produk Keuangan dan Analisis Risiko** — pengguna membutuhkan rekomendasi produk yang relevan beserta ringkasan kelebihan, kekurangan, dan profil risikonya agar dapat mengambil keputusan dengan rasa aman.

## 8. Problem Validation

**Masalah inti:** *analysis paralysis* dan **aset menganggur (idle assets)**. Di era arus informasi ekonomi yang sangat cepat, mengelola aset agar benar-benar produktif menuntut waktu dan kemampuan analisis yang tidak sedikit — mengikuti berita makroekonomi, membaca tren pasar, hingga memahami regulasi (pajak, aturan OJK).

**Akar masalah:**
- **Hambatan waktu & literasi** — mayoritas individu dan pelaku UMKM tidak punya cukup waktu maupun keahlian untuk melakukan riset investasi secara konsisten; literasi pasar modal nasional hanya ±17,78%, jauh di bawah inklusi keuangan (±80,51%).
- **Kompleksitas & risiko regulasi** — instrumen investasi yang legal menuntut pemahaman aturan yang kerap menjadi hambatan dan sumber kekhawatiran salah langkah.
- **Pencampuran keuangan pribadi & bisnis** — pada pelaku UMKM, hal ini menjadi salah satu penyebab kegagalan finansial, sehingga keputusan investasi makin sulit dipisahkan dari arus kas operasional.

Akibatnya, dana berhenti pada instrumen berimbal hasil rendah dan tergerus inflasi — kerugian peluang (*opportunity cost*) yang besar secara akumulatif.

[Riset primer — wawancara & shadowing pengguna: dijadwalkan, belum dilaksanakan. Panduan pertanyaan untuk investor sekaligus pelaku UMKM telah disusun dan siap dijalankan pada iterasi berikutnya.]

## 9. Problem–Solution Mapping

Pemetaan eksplisit **Masalah → Mekanisme Solusi (Fitur/Output) → Outcome**:

| Masalah (dari Problem Validation) | Mekanisme Solusi (Fitur AstaLink) | Outcome / Impact |
|---|---|---|
| Tidak punya waktu memantau pasar | Agen pasar (riset harga, indikator teknikal, sentimen berita) berjalan otomatis & disajikan ringkas via WhatsApp | Beban kognitif turun; keputusan lebih cepat lewat *curated alerts* |
| Literasi investasi rendah | Agen penasihat menyusun strategi alokasi + ringkasan kelebihan/kekurangan dalam bahasa yang mudah dipahami | Pengguna memahami dan percaya diri tanpa harus jadi ahli |
| Kekhawatiran melanggar regulasi | Agen legal memvalidasi rekomendasi terhadap dokumen OJK (RAG) sebelum dieksekusi | Rekomendasi tersaring kepatuhan; risiko hukum diminimalkan |
| Risiko salah alokasi / portofolio tidak optimal | Mesin optimisasi alokasi (MVO + optimizer berbatas) dengan analisis risiko (VaR) | Alokasi efisien sesuai profil risiko |
| Takut kehilangan kendali atas aset | Gerbang Human-in-the-Loop: eksekusi hanya jalan setelah persetujuan ber-PIN | Kendali 100% di tangan pengguna; kepercayaan terjaga |

## 10. Ecosystem Alignment

AstaLink dirancang untuk **selaras dengan regulasi dan memperkuat ekosistem**, bukan menggantikan otoritas atau lembaga jasa keuangan:

- **Regulator (OJK/BI):** Setiap rekomendasi disaring melalui RAG atas dokumen regulasi sebelum sampai ke pengguna, sehingga keluaran sistem berorientasi kepatuhan. Misi kami — meningkatkan inklusi dan literasi investasi — sejalan dengan agenda nasional penguatan ketahanan keuangan.
- **Perusahaan Sekuritas & penyedia Open Finance API:** AstaLink memposisikan diri sebagai lapisan asisten cerdas di atas infrastruktur eksekusi yang sudah berizin; eksekusi transaksi berjalan melalui mitra resmi, bukan menampung dana pengguna secara langsung.
- **Pengguna sebagai pengambil keputusan:** Prinsip HITL memastikan AI tidak pernah memindahkan dana tanpa otorisasi manual, menjaga batas tanggung jawab yang jelas.

Tidak ada pelanggaran regulasi karena sistem bersifat *advisory* dengan persetujuan akhir manusia; AstaLink berperan komplementer terhadap stakeholder, memperluas akses investor ritel ke layanan yang sebelumnya hanya terjangkau secara institusional.

## 11. Solution Approach & Mechanism

AstaLink bekerja sebagai pipeline AI multi-agen ujung-ke-ujung (diorkestrasi LangGraph):

1. **Input & Intent** — Pengguna mengirim permintaan lewat WhatsApp atau dashboard web (mis. "optimalkan dana menganggur saya"). Agen *intent* menafsirkan maksud; bila keyakinan rendah, sistem meminta klarifikasi.
2. **Analisis Paralel** — Tiga agen berjalan bersamaan: **agen pasar** (harga & indikator teknikal via data pasar + sentimen berita), **agen bisnis** (analisis arus kas/valuasi, mis. DCF dari data finansial), dan **agen risiko** (optimisasi rata-rata–varians dan Value-at-Risk).
3. **Optimisasi Alokasi** — Hasil ketiga agen digabung menjadi rencana alokasi melalui *solver* optimisasi berbatas (mempertimbangkan batas sektor dan instrumen terlarang), dengan relaksasi progresif bila kendala terlalu ketat.
4. **Validasi Legal (RAG)** — Agen legal melakukan pencarian hibrida (dense + sparse) atas dokumen regulasi, lalu menilai kepatuhan rencana beserta sitasi. Bila ditolak, rencana dikembalikan untuk revisi (maksimal beberapa siklus).
5. **Human-in-the-Loop** — Rencana yang lolos dikirim ke pengguna untuk persetujuan; graph benar-benar *suspend* hingga pengguna menyetujui/menolak lewat dashboard dengan PIN.
6. **Eksekusi & Jejak Audit** — Setelah disetujui, eksekusi dijalankan (saat ini melalui broker sandbox; integrasi broker riil adalah langkah berikutnya) dengan idempotensi, dan seluruh langkah tercatat pada *audit log* untuk transparansi.

Model bisnis (BMC) dirangkum pada bagian *Value Proposition*, *Model Revenue/Funding*, *Cost Structure*, dan *Partnership & Distribution* di bawah.

## 12. Impact Scale & Targets

**Skala dampak:** Pasar yang dituju adalah investor ritel muda dan pelaku UMKM di Indonesia — segmen yang besar dan tumbuh cepat (jumlah Single Investor Identification mencapai ±8,98 juta pada 2026), namun mayoritas berliterasi pasar modal rendah (±4,9% pada segmen muda).

**Target dampak:**
- **Aktivasi aset menganggur** menjadi instrumen produktif yang legal dan aman, menekan kerugian peluang akibat inflasi.
- **Demokratisasi strategi kelas institusi** ke investor individu dengan biaya jauh lebih rendah dibanding manajer investasi konvensional.
- **Penguatan ketahanan finansial UMKM** dengan memisahkan dan mengoptimalkan keuangan pribadi dan bisnis.
- **Peningkatan literasi praktis** melalui ringkasan keputusan yang edukatif pada setiap rekomendasi.

## 13. Impact Measurement

Keberhasilan diukur secara kuantitatif melalui dua lapis metrik:

**Metrik produk/dampak pengguna (KPI):**
- Jumlah aset menganggur yang teraktivasi (nilai dana yang dialokasikan ulang).
- Tingkat adopsi & retensi (pengguna aktif mingguan, rasio rekomendasi yang disetujui).
- Waktu rata-rata dari permintaan hingga keputusan (efisiensi waktu pengguna).
- Tingkat penyelesaian alur HITL (approval funnel: rekomendasi → ditinjau → disetujui).

**Metrik sistem & kualitas AI (terinstrumentasi):** Backend mengekspor metrik Prometheus dan divisualisasikan pada tiga dashboard Grafana — *pipeline-health* (latensi p50/p95 & error per node), *ai-quality* (tingkat halusinasi & faithfulness, dievaluasi dengan DeepEval), dan *business-funnel* (jumlah approval/penolakan/revisi). Ini memungkinkan pengukuran akurasi, kepatuhan, dan keandalan secara berkelanjutan.

## 14. System & Public Value Proposition

Bagi sistem yang lebih luas, AstaLink memberi nilai:
- **Inklusi & literasi keuangan** — menutup jurang antara akses (inklusi ±80,51%) dan pemahaman (literasi ±66,46%; pasar modal ±17,78%) dengan asisten yang mengedukasi sambil bertindak.
- **Ketahanan ekonomi mikro** — UMKM yang lebih sehat secara finansial memperkuat fondasi ekonomi nasional.
- **Pendalaman pasar modal** — memperluas basis investor ritel yang teredukasi dan patuh, mendukung likuiditas dan stabilitas pasar.
- **Kepatuhan sebagai default** — menormalkan investasi yang tersaring regulasi, menurunkan risiko praktik ilegal/penipuan investasi di masyarakat.

## 15. Solution Originality

Yang benar-benar baru dari AstaLink dibanding solusi yang sudah ada:
- **Composer** adalah dashboard web sentris tanpa antarmuka chat harian — pengguna harus masuk ke platform untuk memantau/mengubah strategi.
- **Vise** adalah alat B2B untuk penasihat keuangan; investor akhir tidak bisa memakainya mandiri, apalagi via WhatsApp.
- **Pionex** adalah bursa kripto ber-AI namun terbatas pada aset kripto dan terkunci di aplikasinya sendiri.
- **Betterment** adalah robo-advisor pasif.

AstaLink berbeda sebagai **asisten proaktif yang hidup di WhatsApp**: membeli/mengelola aset dan bertanya kondisi pasar disederhanakan dalam satu kanal percakapan, dengan **diskusi dan eksekusi strategi lewat persetujuan real-time (HITL)** — bukan robo-advisor pasif dan bukan sekadar dashboard. Kombinasi kanal universal + orkestrasi multi-agen patuh-regulasi + kendali manusia inilah keunikan utamanya.

## 16. Technological / Method Innovation

Pendekatan teknis/metodologi unik:
- **Orkestrasi AI Multi-Agen (LangGraph):** delapan node terspesialisasi (intent → pasar/bisnis/risiko paralel → optimizer → legal → HITL → eksekusi) dengan loop revisi otomatis ketika validasi legal menolak rencana.
- **Hybrid RAG untuk kepatuhan:** retrieval gabungan *dense* (embedding) + *sparse* (BM25) dengan *Reciprocal Rank Fusion*, ditambah *citation grader* agar keputusan legal berbasis sumber, bukan halusinasi.
- **Optimisasi alokasi berbatas regulasi:** *solver* konveks dengan relaksasi progresif yang menyerap kendala dari sitasi legal (mis. instrumen terlarang) — menyatukan keuangan kuantitatif dengan kepatuhan.
- **Human-in-the-Loop sebagai interupsi nyata:** graph benar-benar suspend (`interrupt`) dan baru lanjut setelah otorisasi ber-PIN — gerbang keamanan, bukan sekadar konsep UX.
- **LLM Gemini** untuk penalaran dan narasi pada setiap agen.

## 17. Creativity in Implementation

- **Distribusi (zero-friction):** kanal utama adalah WhatsApp — tidak perlu mengunduh aplikasi baru atau mempelajari terminal rumit; pengguna berinteraksi semudah membalas pesan.
- **Engagement (curated alerts):** asisten hanya memberi notifikasi pada poin keputusan penting, bukan kebisingan pasar — menjaga relevansi dan kepercayaan.
- **Monetisasi (freemium):** tier Basic gratis untuk menurunkan hambatan adopsi, dengan tier Pro/Business berlangganan untuk fitur lanjutan — model yang menyeimbangkan pertumbuhan pengguna dan keberlanjutan.
- **Edukasi sebagai produk:** setiap rekomendasi disertai ringkasan kelebihan/kekurangan, menjadikan penggunaan sehari-hari sebagai sarana peningkatan literasi.

## 18. System Architecture

Arsitektur dirancang modular dan sistemik (terdeploy dalam kontainer Docker):

- **Frontend (Next.js):** dashboard web untuk persetujuan (approval inbox & detail dengan grafik alokasi dan sitasi legal), pengaturan PIN, jejak audit, dan riwayat transaksi; serta antarmuka percakapan (WhatsApp & web — antarmuka chat web pada roadmap berikutnya).
- **Backend (FastAPI):** layanan API untuk menjalankan agen, webhook WhatsApp, persetujuan/HITL, dan PIN; mengekspor metrik untuk observabilitas.
- **Lapisan AI (LangGraph + Gemini):** pipeline 8-node multi-agen dengan *checkpointer* persisten sehingga eksekusi dapat di-suspend (HITL) dan dilanjutkan.
- **Lapisan data (Supabase/PostgreSQL):** tabel `workspaces`, `audit_log`, `allocation_plans`, `transactions`, `pin_codes`, `regulation_documents`, serta tabel WhatsApp & checkpoint LangGraph — seluruhnya dengan Row-Level Security.
- **Pengetahuan/RAG (Pinecone + BM25):** indeks dokumen regulasi untuk validasi legal.
- **Observabilitas (Prometheus + Grafana + DeepEval):** pemantauan latensi, error, dan kualitas AI.

Eksekusi transaksi dikunci di balik HITL ber-PIN; pemisahan tabel Auth dan Fitur memperkuat keamanan data.

## 19. Data & Feasibility

Sistem memproses tiga kategori data utama:
1. **Input pengguna** — perintah teks via WhatsApp/web, beserta data autentikasi dan profil yang tersimpan di PostgreSQL (Supabase).
2. **Data regulasi** — dokumen hukum perpajakan dan aturan OJK (PDF) yang diindeks ke vector database (Pinecone) sebagai *ground truth* untuk kepatuhan via RAG.
3. **Data pasar & berita finansial** — ditarik real-time dari sumber pasar (mis. data harga publik) dan API berita untuk sentimen; data finansial bisnis dapat diunggah (mis. CSV) untuk analisis valuasi.

**Kelayakan:** Kombinasi ini andal — data regulasi menjadi acuan kepatuhan absolut, sedangkan data pasar menjaga rekomendasi selalu relevan dengan kondisi terkini. *Catatan transparansi:* kode pipeline RAG sudah siap; pengindeksan korpus regulasi nyata ke Pinecone/BM25 adalah langkah implementasi berikutnya pada roadmap.

## 20. Security & Compliance

Keamanan dan kepatuhan dibangun berlapis:
- **Autentikasi:** JWT Supabase diverifikasi backend pada setiap rute terproteksi.
- **Isolasi data:** Row-Level Security pada seluruh tabel aplikasi (scoping kepemilikan workspace); pemisahan tabel Auth dan Fitur.
- **Persetujuan ber-PIN:** PIN di-hash dengan Argon2, dengan mekanisme penguncian (lockout) setelah lima percobaan gagal.
- **Human-in-the-Loop:** eksekusi transaksi mustahil terjadi tanpa otorisasi manual ber-PIN — mencegah AI memindahkan dana tanpa izin.
- **Integritas webhook:** payload WhatsApp diverifikasi HMAC-SHA256 dan diproses idempoten.
- **Kepatuhan:** validasi legal berbasis RAG atas dokumen OJK menyaring rekomendasi sebelum sampai ke pengguna.
- **Rahasia & deployment:** kredensial dikelola via variabel lingkungan (gitignored), deployment HTTPS melalui Traefik/Dokploy.

## 21. Implementation Readiness (MVP)

**Scope MVP:** alur ujung-ke-ujung "permintaan → analisis multi-agen → validasi legal → persetujuan HITL ber-PIN → eksekusi (sandbox) → jejak audit", dapat diakses via WhatsApp dan dashboard web, untuk workspace personal maupun bisnis.

**Status pembangunan saat ini (sudah berjalan):** pipeline 8-node LangGraph lengkap; mesin pasar/bisnis/risiko/optimizer; RAG legal hibrida + citation grader; HITL `interrupt` nyata + persetujuan ber-PIN; webhook WhatsApp; skema database + RLS (9 migrasi); UI persetujuan, audit, transaksi, dan PIN; Docker Compose dev/prod; monitoring Prometheus + Grafana; 37 berkas uji.

**Target penyelesaian MVP (roadmap berikutnya):** pengindeksan korpus regulasi ke Pinecone/BM25; antarmuka chat agentik di web; pengayaan dashboard portofolio; suite evaluasi DeepEval (20 prompt berlabel) + gate CI; serta integrasi broker riil menggantikan broker sandbox.

## 22. Value Proposition

Nilai utama yang diterima pengguna: **"Family Office 24/7 di saku Anda."**
- **Efisiensi waktu & aksesibilitas:** kelola portofolio cukup lewat WhatsApp, secepat membalas pesan — tanpa terminal rumit.
- **Kepatuhan otomatis:** filter regulasi real-time menekan risiko hukum yang kerap menghambat investor.
- **Demokratisasi strategi:** akses strategi kelas institusi dengan biaya jauh lebih rendah dari manajer investasi konvensional.
- **Kendali & ketenangan:** disiplin emosional terjaga (AI menyaring kebisingan pasar) sementara keputusan akhir 100% di tangan pengguna lewat HITL.

## 23. Model Revenue / Funding

Model pendapatan **freemium berbasis langganan**:
- **Basic (Gratis):** limit analitik aset dan otorisasi transaksi manual standar — menurunkan hambatan adopsi.
- **Pro/Business (Langganan, ±Rp149.000/bulan):** AI tanpa batas, perencanaan multi-agen penuh, koneksi Open Finance, dan filter perpajakan.

Sumber pendapatan utama adalah langganan tier Pro/Business; ke depan terbuka peluang kemitraan B2B dan pendanaan untuk akselerasi R&D dan ekspansi.

## 24. Cost Structure & Sustainability

**Komponen biaya utama:**
- Server hosting & infrastruktur kontainer (Docker/Dokploy).
- Biaya per panggilan API LLM (Gemini) dan API Meta/WhatsApp serta data pasar/berita.
- Pemeliharaan keamanan & pembaruan vector database regulasi.
- Legalitas dan keamanan siber.

**Keberlanjutan finansial:** marjin tier Pro/Business menutup biaya variabel (API/LLM) per pengguna, sementara tier Basic berfungsi sebagai corong akuisisi. Efisiensi biaya dijaga lewat caching konteks dan arsitektur asinkron (FastAPI) agar biaya per permintaan tetap terkendali seiring skala.

## 25. Scalability

AstaLink dirancang untuk tumbuh ke skala lebih besar:
- **Arsitektur kontainer & modular:** backend FastAPI dan komponen pendukung dapat diskalakan secara independen (horizontal) di balik Docker.
- **Pipeline asinkron:** penanganan webhook dan eksekusi agen bersifat non-blok, cocok untuk lonjakan trafik percakapan.
- **State persisten via checkpointer:** eksekusi panjang (termasuk jeda HITL) dapat dilanjutkan lintas instance.
- **Observabilitas bawaan:** Prometheus/Grafana memungkinkan deteksi bottleneck dan penskalaan berbasis metrik.
- **Ekspansi cakupan:** dari aset/instrumen awal ke kelas aset lain dan integrasi mitra Open Finance tambahan tanpa mengubah inti orkestrasi.

## 26. Partnership & Distribution

**Strategi distribusi:**
- **Kanal utama WhatsApp** untuk jangkauan massal zero-friction.
- **Komunitas pengusaha/UMKM** dan **platform B2B** sebagai jalur akuisisi tersegmentasi.

**Peran mitra (Key Partners):**
- **Penyedia Open Finance API & perusahaan sekuritas** — infrastruktur eksekusi transaksi yang berizin.
- **Penyedia cloud/LLM** — kapasitas komputasi dan model AI.
- **Mitra regulasi/komunitas literasi** — memperkuat kredibilitas dan jangkauan edukasi.

Mitra memungkinkan AstaLink fokus pada lapisan kecerdasan (orkestrasi AI patuh-regulasi) sembari menyandar pada infrastruktur keuangan yang sudah ada.

## 27. Problem–Market Fit

Masalah ini penting bagi target pengguna karena menyentuh langsung ketahanan finansial mereka. Investor saham Indonesia tumbuh pesat (±8,98 juta SID pada 2026), namun mayoritas adalah investor muda dengan literasi pasar modal sangat rendah (±4,9%). Banyak di antaranya juga pemilik bisnis — dan ±90% bisnis gagal karena kesalahan finansial, terutama mencampur keuangan pribadi & bisnis serta arus kas yang buruk.

Artinya ada **kebutuhan akut sekaligus pasar besar**: orang punya dana dan niat berinvestasi, tetapi tidak punya waktu, literasi, dan rasa aman regulasi untuk melakukannya. AstaLink mengisi celah ini secara tepat dengan asisten yang mengedukasi, menyaring kepatuhan, dan menjaga kendali tetap di tangan pengguna.

## 28. Evidence of Demand

**Bukti sekunder (desk research):**
- **SNLIK OJK & BPS (2025):** inklusi keuangan nasional ±80,51% namun literasi keuangan hanya ±66,46% — banyak masyarakat punya rekening/dana tetapi belum paham mengembangkannya. Literasi pasar modal bahkan hanya ±17,78%.
- **Pertumbuhan SID:** ±8,98 juta investor (2026) didominasi investor muda berliterasi rendah (±4,9%) — basis pengguna potensial yang besar dan kurang terlayani.
- **Kegagalan UMKM:** ±90% bisnis gagal akibat kesalahan finansial (mencampur keuangan pribadi & bisnis, cash flow buruk) — menegaskan kebutuhan asisten keuangan terpadu.

**Bukti primer (wawancara & survei pengguna):**
[Riset primer — wawancara & shadowing pengguna: dijadwalkan, belum dilaksanakan. Instrumen wawancara untuk investor sekaligus pelaku UMKM serta untuk investor telah disusun dan siap dijalankan; hasil akan dilengkapi pada iterasi berikutnya.]

## 29. Target Market

Target market utama (spesifik):
- **Solopreneur, freelancer, dan pendiri startup/UMKM** kelas menengah yang ingin mengelola aset pribadi sekaligus kas bisnis.
- **Pekerja profesional & investor ritel muda** dengan arus kas stabil namun waktu dan literasi investasi terbatas.

Karakteristik bersama: memiliki dana yang belum dioptimalkan (*idle assets*), terbiasa dengan WhatsApp, dan membutuhkan pendampingan yang patuh regulasi serta mudah dipakai sehari-hari.

## 30. Adoption Readiness

Solusi mudah diadopsi:
- **Tanpa aplikasi baru:** interaksi utama lewat WhatsApp yang sudah dipakai sehari-hari — hambatan onboarding minimal.
- **Kurva belajar rendah:** percakapan natural; sistem meminta klarifikasi bila perlu, dan setiap rekomendasi disertai ringkasan yang mudah dipahami.
- **Kepercayaan terjaga sejak awal:** prinsip HITL dan persetujuan ber-PIN memastikan pengguna tidak pernah kehilangan kendali — menurunkan keraguan untuk mencoba.
- **Tier gratis (Basic):** memungkinkan pengguna mencoba nilai inti tanpa komitmen biaya.

## 31. Progress Since the 1st Submission

Pada submission pertama, AstaLink berada pada tahap **Proof of Concept transisional menuju prototipe** — sebagian besar masih berupa blueprint arsitektur dan rencana. Sejak itu, perkembangan utama dari sisi aplikasi adalah perubahan dari konsep menjadi **prototipe yang berjalan**:

- **Pipeline AI multi-agen kini benar-benar diimplementasikan** (LangGraph 8 node: intent → pasar/bisnis/risiko paralel → optimizer → legal → HITL → eksekusi), lengkap dengan loop revisi otomatis — sebelumnya hanya diagram konseptual.
- **Human-in-the-Loop menjadi mekanisme nyata:** graph benar-benar suspend (`interrupt`) dan dilanjutkan hanya setelah persetujuan ber-PIN — bukan lagi sekadar prinsip UX.
- **Validasi legal berbasis RAG hibrida** (Pinecone dense + BM25 sparse + Reciprocal Rank Fusion) dengan *citation grader* telah dibangun, mewujudkan janji "kepatuhan regulasi otomatis".
- **Mesin kuantitatif ditambahkan:** indikator teknikal pasar, DCF analisis bisnis, MVO & Value-at-Risk untuk risiko, serta optimizer alokasi konveks dengan relaksasi progresif dan kendala dari sitasi legal.
- **Keamanan diperkuat:** JWT Supabase + Row-Level Security pada seluruh tabel, PIN Argon2 dengan lockout, verifikasi HMAC webhook WhatsApp.
- **Antarmuka & infrastruktur:** dashboard persetujuan (grafik alokasi, sitasi legal), pengaturan PIN, jejak audit, dan riwayat transaksi; Docker Compose dev/prod dengan deployment Traefik/Dokploy; monitoring Prometheus + tiga dashboard Grafana; 9 migrasi skema database; serta 37 berkas uji dan gate kualitas CI.

**Fokus berikutnya (jujur, belum selesai):** pengindeksan korpus regulasi nyata ke Pinecone, antarmuka chat agentik di web, pengayaan dashboard portofolio, suite evaluasi DeepEval, dan integrasi broker riil menggantikan broker sandbox.

Ringkasnya: proposal 1 menjanjikan arsitektur; proposal 2 menunjukkan sistem yang sebagian besar **sudah berjalan end-to-end** sebagai prototipe.

## 32. Current Status

**Prototype.**

Alur inti telah berjalan end-to-end sebagai prototipe fungsional (pipeline multi-agen, validasi legal, HITL ber-PIN, eksekusi sandbox, jejak audit, monitoring), dengan beberapa item penyempurnaan menuju MVP penuh sebagaimana diuraikan pada *Implementation Readiness* dan *Progress Since the 1st Submission*.

## Attachment

- **Link Attachment (URL):** [ISI LINK DEMO / REPOSITORI / VIDEO JIKA ADA]
- **File Attachment:** Lampirkan berkas PDF proposal ini. *Aturan penamaan berkas:* `ID Tim - Judul Proposal` (mis. `<ID_TIM> - AstaLink AI Chief Investment Officer.pdf`), format PDF, maksimal 5 MB.
````

- [ ] **Step 2: Verify the file was created and answer count is complete**

Run: `grep -c '^## ' "docs/proposal_2/output/proposal_2_answers.md"`
Expected: `33` (32 numbered answer sections + the "Attachment" section; the document title uses a single `#`).

Run: `grep -E '^## [0-9]+\.' "docs/proposal_2/output/proposal_2_answers.md" | wc -l`
Expected: `32`

- [ ] **Step 3: Commit**

```bash
git add "docs/proposal_2/output/proposal_2_answers.md"
git commit -m "docs(proposal-2): master gform narrative answers (md)"
```

---

## Task 2: Build script — Markdown → DOCX

**Files:**
- Create: `docs/proposal_2/output/build_docx.py`

- [ ] **Step 1: Write the build script**

Create `docs/proposal_2/output/build_docx.py` with this exact content. It parses the master Markdown (headings, paragraphs, bullet lists, and the one GitHub-style table in section 9) and renders a clean A4 DOCX with readable fonts (per panitia: font mudah dibaca, 11–12pt, spasi 1–1.15).

```python
#!/usr/bin/env python3
"""Render proposal_2_answers.md into a styled DOCX (no pandoc needed)."""
import re
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = Path(__file__).resolve().parent
SRC = HERE / "proposal_2_answers.md"
OUT = HERE / "AstaLink_Proposal_2.docx"

ACCENT = RGBColor(0x1F, 0x4E, 0x79)  # dark blue, matches proposal 1


def strip_inline(text: str) -> list[tuple[str, bool, bool]]:
    """Split text into (chunk, is_bold, is_italic) runs, honoring **bold** and *italic*."""
    runs: list[tuple[str, bool, bool]] = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if not part:
            continue
        if i % 2 == 1:  # captured **bold** group
            runs.append((part, True, False))
            continue
        # non-bold segment: split on single-asterisk *italic*
        for j, sub in enumerate(
            re.split(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", part)
        ):
            if sub:
                runs.append((sub, False, j % 2 == 1))
    return runs or [(text, False, False)]


def add_para(doc, text, *, size=11, bold=False, color=None, space_after=6,
             align=None, style=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    for chunk, chunk_bold, chunk_italic in strip_inline(text):
        run = p.add_run(chunk)
        run.font.size = Pt(size)
        run.font.name = "Calibri"
        run.bold = bold or chunk_bold
        run.italic = chunk_italic
        if color is not None:
            run.font.color.rgb = color
    return p


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        return 1

    lines = SRC.read_text(encoding="utf-8").splitlines()
    doc = Document()

    # A4 + 1-inch margins
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(1))

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()

        if not line:
            i += 1
            continue

        # Table block (GitHub pipe table)
        if line.startswith("|"):
            block = []
            while i < n and lines[i].lstrip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = [
                [c.strip() for c in row.strip("|").split("|")]
                for row in block
                if not re.match(r"^\|[\s:|-]+\|?$", row)  # drop separator row
            ]
            if rows:
                table = doc.add_table(rows=len(rows), cols=len(rows[0]))
                table.style = "Light Grid Accent 1"
                for r, row in enumerate(rows):
                    for c, cell_text in enumerate(row):
                        cell = table.cell(r, c)
                        cell.text = ""
                        para = cell.paragraphs[0]
                        for chunk, chunk_bold, chunk_italic in strip_inline(cell_text):
                            run = para.add_run(chunk)
                            run.font.size = Pt(9.5)
                            run.font.name = "Calibri"
                            run.bold = chunk_bold or (r == 0)
                            run.italic = chunk_italic
                doc.add_paragraph().paragraph_format.space_after = Pt(6)
            continue

        # Headings
        if line.startswith("# "):
            add_para(doc, line[2:], size=18, bold=True, color=ACCENT,
                     space_after=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        elif line.startswith("## "):
            add_para(doc, line[3:], size=13, bold=True, color=ACCENT, space_after=4)
        elif line.startswith("### "):
            add_para(doc, line[4:], size=12, bold=True, color=ACCENT, space_after=4)
        elif line == "---":
            pass  # skip horizontal rules
        # Bullets
        elif re.match(r"^[-*] ", line):
            add_para(doc, line[2:], size=11, space_after=3, style="List Bullet")
        elif re.match(r"^\d+\. ", line):
            p = add_para(doc, line, size=11, space_after=3)
            p.paragraph_format.left_indent = Inches(0.25)
        else:
            add_para(doc, line, size=11)
        i += 1

    doc.save(OUT)
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Commit the script**

```bash
git add "docs/proposal_2/output/build_docx.py"
git commit -m "build(proposal-2): md-to-docx renderer using python-docx"
```

---

## Task 3: Generate the DOCX

**Files:**
- Generate: `docs/proposal_2/output/AstaLink_Proposal_2.docx`

- [ ] **Step 1: Run the build script**

Run:
```bash
cd "docs/proposal_2/output" && python3 build_docx.py
```
Expected output: `Wrote .../AstaLink_Proposal_2.docx` and exit code 0.

- [ ] **Step 2: Verify the DOCX exists and is non-trivial**

Run: `ls -la "docs/proposal_2/output/AstaLink_Proposal_2.docx"`
Expected: file exists, size > 15 KB.

- [ ] **Step 3: Verify DOCX text content survived (spot-check key strings)**

Run:
```bash
cd "docs/proposal_2/output" && python3 -c "
from docx import Document
d = Document('AstaLink_Proposal_2.docx')
text = '\n'.join(p.text for p in d.paragraphs)
for needle in ['AI Chief Investment Officer', 'MUMET', 'Human-in-the-Loop', 'Progress Since the 1st Submission', 'belum dilaksanakan']:
    assert needle in text, f'MISSING: {needle}'
print('OK: all key strings present; paragraphs =', len(d.paragraphs), '; tables =', len(d.tables))
"
```
Expected: `OK: all key strings present; paragraphs = <N>; tables = 1`

- [ ] **Step 4: Commit the DOCX**

```bash
git add "docs/proposal_2/output/AstaLink_Proposal_2.docx"
git commit -m "docs(proposal-2): generated DOCX deliverable"
```

---

## Task 4: Generate the PDF

**Files:**
- Generate: `docs/proposal_2/output/AstaLink_Proposal_2.pdf`

- [ ] **Step 1: Convert DOCX → PDF with LibreOffice headless**

Run:
```bash
cd "docs/proposal_2/output" && soffice --headless --convert-to pdf --outdir . AstaLink_Proposal_2.docx
```
Expected: `convert .../AstaLink_Proposal_2.docx -> .../AstaLink_Proposal_2.pdf using filter : writer_pdf_Export`

> If `soffice` reports a lock because another LibreOffice instance is open, retry with a throwaway profile:
> ```bash
> cd "docs/proposal_2/output" && soffice --headless -env:UserInstallation=file:///tmp/lo_proposal2 --convert-to pdf --outdir . AstaLink_Proposal_2.docx
> ```

- [ ] **Step 2: Verify the PDF exists and is under the 5 MB form limit**

Run:
```bash
ls -la "docs/proposal_2/output/AstaLink_Proposal_2.pdf"
python3 -c "import os; sz=os.path.getsize('docs/proposal_2/output/AstaLink_Proposal_2.pdf'); print(f'{sz/1024/1024:.2f} MB'); assert sz < 5*1024*1024, 'PDF exceeds 5MB form limit'; assert sz > 20000, 'PDF suspiciously small'; print('OK under 5MB')"
```
Expected: prints a size like `0.1x MB` then `OK under 5MB`.

- [ ] **Step 3: Verify PDF text is extractable and contains key sections**

Run:
```bash
cd "docs/proposal_2/output" && python3 -c "
import pypdf
r = pypdf.PdfReader('AstaLink_Proposal_2.pdf')
text = '\n'.join((pg.extract_text() or '') for pg in r.pages)
for needle in ['AstaLink', 'Executive Summary', 'Progress Since the 1st Submission', 'Prototype']:
    assert needle in text, f'MISSING in PDF: {needle}'
print('OK: PDF pages =', len(r.pages), '; key sections present')
"
```
Expected: `OK: PDF pages = <N>; key sections present`
(If `pypdf` import fails, substitute: `python3 -c "import pdfminer"` is not assumed — `pypdf` is a backend dependency and is available in `backend/.venv`; run this check from that venv if needed: `"../../../backend/.venv/bin/python"`.)

- [ ] **Step 4: Commit the PDF**

```bash
git add "docs/proposal_2/output/AstaLink_Proposal_2.pdf"
git commit -m "docs(proposal-2): generated PDF deliverable (form attachment)"
```

---

## Task 5: Final review & handoff notes

**Files:**
- Create: `docs/proposal_2/output/README.md`

- [ ] **Step 1: Cross-check every form field is answered**

Run:
```bash
cd "docs/proposal_2/output" && for q in "ID Tim" "Nama Tim" "Proposal Title" "Team Composition" "Executive Summary" "Problem Statement" "Primary Sub-Problem" "Problem Validation" "Problem–Solution Mapping" "Ecosystem Alignment" "Solution Approach" "Impact Scale" "Impact Measurement" "System & Public Value" "Solution Originality" "Technological / Method" "Creativity in Implementation" "System Architecture" "Data & Feasibility" "Security & Compliance" "Implementation Readiness" "Value Proposition" "Model Revenue" "Cost Structure" "Scalability" "Partnership & Distribution" "Problem–Market Fit" "Evidence of Demand" "Target Market" "Adoption Readiness" "Progress Since the 1st Submission" "Current Status"; do grep -q "$q" proposal_2_answers.md && echo "OK  $q" || echo "MISSING  $q"; done
```
Expected: all 32 lines start with `OK`.

- [ ] **Step 2: Write the README with manual-action checklist**

Create `docs/proposal_2/output/README.md`:

```markdown
# AstaLink — Proposal 2 (2nd Submission) Deliverables

Files in this folder answer all 32 required Google Form questions for team MUMET.

- `proposal_2_answers.md` — source of truth (edit this, then rebuild).
- `build_docx.py` — `python3 build_docx.py` regenerates the DOCX.
- `AstaLink_Proposal_2.docx` — generated; do not hand-edit.
- `AstaLink_Proposal_2.pdf` — generated; the file to attach to the form.

## Rebuild
```bash
python3 build_docx.py
soffice --headless --convert-to pdf --outdir . AstaLink_Proposal_2.docx
```

## ⚠️ Manual actions before submitting (placeholders to fill)
1. **ID Tim** — replace `[ISI ID TIM SESUAI DATA PENDAFTARAN]` with the registered team ID.
2. **Link Attachment** — replace `[ISI LINK DEMO / REPOSITORI / VIDEO JIKA ADA]` if you have a demo/repo link.
3. **Rename the PDF** to the form's required pattern before upload: `<ID Tim> - AstaLink AI Chief Investment Officer.pdf`.
4. **User interview** — the Problem Validation interview portion and the primary-research part of Evidence of Demand are intentionally left empty (`[Riset primer ... belum dilaksanakan]`). Fill these once user interviews/shadowing are completed.
```

- [ ] **Step 3: Commit and finish**

```bash
git add "docs/proposal_2/output/README.md"
git commit -m "docs(proposal-2): output README with rebuild + manual-action checklist"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** All 32 gform fields (Appendix A) have a dedicated `## N.` section in Task 1's master file; verified by the Task 5 cross-check loop. Output formats `.md` (Task 1), `.docx` (Tasks 2–3), `.pdf` (Task 4) all covered. The "what improved vs proposal 1" requirement is answered in §31 (Progress Since the 1st Submission), grounded in the real codebase inventory. User-interview content is left empty per instruction (§8 and §28 markers + README item 4).
- **Placeholder scan:** The only intentional placeholders are the unknowable `ID Tim`, optional `Link Attachment`, and the user-interview markers — each explicitly flagged in the README checklist. No "TBD/implement later" in narrative.
- **Type consistency:** File names are identical across all tasks (`proposal_2_answers.md`, `build_docx.py`, `AstaLink_Proposal_2.docx`, `AstaLink_Proposal_2.pdf`). The build script's table parser matches the single pipe-table authored in §9. Heading levels (`#`/`##`/`###`) used in the master file are exactly those handled by `build_docx.py`.

---

## Appendix A — The 32 form fields (transcribed from `gform/`)

| # | Field (label) | Prompt |
|---|---|---|
| 1 | ID Tim | Masukkan ID Tim sesuai data pendaftaran. |
| 2 | Nama Tim | Masukkan Nama Tim. |
| 3 | Proposal Title | Masukkan judul proposal. |
| 4 | Team Composition | Nama ketua & anggota, serta peran masing-masing. |
| 5 | Executive Summary | Versi terbaru solusi: problem utama, pendekatan solusi, dampak utama. |
| 6 | Problem Statement | Penulisan problem statement yang sesuai. |
| 7 | Primary Sub-Problem Statement | Sub-problem statement (boleh > 1). |
| 8 | Problem Validation | Masalah inti yang diselesaikan + akar masalahnya. |
| 9 | Problem–Solution Mapping | Hubungan eksplisit problem → mekanisme solusi → outcome. |
| 10 | Ecosystem Alignment | Interaksi dengan stakeholder dan regulasi. |
| 11 | Solution Approach & Mechanism | Cara solusi bekerja end-to-end. |
| 12 | Impact Scale & Targets | Dampak utama & skala dampaknya. |
| 13 | Impact Measurement | Pengukuran keberhasilan secara kuantitatif. |
| 14 | System & Public Value Proposition | Nilai terhadap sistem yang lebih luas. |
| 15 | Solution Originality | Apa yang benar-benar baru vs yang sudah ada. |
| 16 | Technological / Method Innovation | Pendekatan teknis/metodologi unik. |
| 17 | Creativity in Implementation | Kreativitas distribusi, monetisasi, atau engagement. |
| 18 | System Architecture | Desain arsitektur solusi secara sistemik. |
| 19 | Data & Feasibility | Data apa yang digunakan & dari mana sumbernya. |
| 20 | Security & Compliance | Penanganan keamanan data & kepatuhan. |
| 21 | Implementation Readiness (MVP) | Scope MVP & target pembangunannya. |
| 22 | Value Proposition | Nilai utama yang diterima pengguna. |
| 23 | Model Revenue / Funding | Cara menghasilkan revenue atau pendanaan. |
| 24 | Cost Structure & Sustainability | Komponen biaya utama & keberlanjutan finansial. |
| 25 | Scalability | Cara solusi berkembang ke skala lebih besar. |
| 26 | Partnership & Distribution | Strategi distribusi & peran mitra. |
| 27 | Problem–Market Fit | Mengapa masalah penting bagi target pengguna. |
| 28 | Evidence of Demand | Bukti solusi dibutuhkan (survey, interview, dll). |
| 29 | Target Market | Target market utama, spesifik. |
| 30 | Adoption Readiness | Seberapa mudah solusi diadopsi pengguna. |
| 31 | Progress Since the 1st Submission | Perkembangan utama sejak submission sebelumnya. |
| 32 | Current Status | Status solusi (idea/mockup/prototype/pilot). |
| + | Attachment | Link/file (PDF ≤ 5MB; nama: ID Team - Judul Proposal). |

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-01-proposal-2-gform-narrative.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
