# Visi, Positioning, dan Arah Arsitektur AstaLink

- **Status:** dokumen arah produk dan arsitektur
- **Tanggal:** 20 September 2026
- **Cakupan:** visi produk, target pengguna, positioning, prinsip pengalaman, serta perbandingan arsitektur AI saat ini dan arsitektur yang dituju

## Ringkasan Eksekutif

AstaLink ditujukan sebagai jembatan menuju investasi yang bertanggung jawab. Produk ini membantu calon investor memahami apakah uang yang mereka miliki sudah layak dialokasikan ke investasi, apa prioritas yang lebih penting, dan bagaimana mengeksplorasi pilihan investasi melalui sandbox tanpa mengambil alih keputusan pengguna.

AstaLink bukan aplikasi yang sekadar menjawab “saham apa yang harus dibeli”. Nilai utamanya berada satu tahap sebelum itu: memahami asal, fungsi, batas, dan tujuan uang pengguna. Setelah konteks tersebut cukup jelas, AstaLink dapat mengarahkan pengguna ke simulasi investasi, mempertahankan dana sebagai kas, atau menunjukkan bahwa kebutuhan bisnis maupun kewajiban lain masih lebih penting.

Pemilik UMKM atau owner-operator merupakan use case yang kuat karena mereka menghadapi keputusan alokasi yang kompleks antara kas, operasional, pengembangan usaha, dan investasi. Namun, mereka bukan satu-satunya pasar AstaLink. Target yang lebih tepat ditentukan oleh kondisi keputusan finansial, bukan label pekerjaan.

Arsitektur AI saat ini sudah kuat sebagai pipeline rekomendasi yang aman, dapat diaudit, dan terkendali. Kelemahannya adalah percakapan masih menjadi pintu masuk menuju graph yang relatif tetap. Arsitektur tujuan tetap menggunakan graph, tetapi menambahkan satu coach/supervisor sebagai pengendali keputusan, shared financial context yang bersifat temporal, serta specialist agents yang dipanggil secara selektif. Kalkulasi dan guardrail tetap deterministik.

## 1. Masalah yang Ingin Diselesaikan

Calon investor sering kali tidak berhenti karena tidak mengetahui nama saham. Mereka berhenti karena belum mampu menjawab pertanyaan yang lebih mendasar:

- Apakah uang ini benar-benar boleh diinvestasikan?
- Apakah uang ini masih dibutuhkan dalam waktu dekat?
- Apakah dana darurat dan kewajiban penting sudah aman?
- Apakah lebih masuk akal menambah modal bisnis, menyimpan kas, membayar utang, atau mulai berinvestasi?
- Jika sudah siap, instrumen dan tingkat risiko seperti apa yang sesuai?

Aplikasi investasi umumnya mulai bekerja setelah pengguna memutuskan untuk berinvestasi. AstaLink bekerja pada masa transisi sebelum keputusan itu, lalu membawa pengguna ke sandbox ketika investasi sudah menjadi pilihan yang masuk akal.

## 2. Tujuan Produk

Tujuan utama AstaLink adalah:

> Membantu calon investor ritel mengambil langkah pertama menuju investasi dengan memahami kondisi, prioritas, dan kesiapan finansialnya terlebih dahulu.

Tujuan tersebut memiliki tiga konsekuensi:

1. **Pemahaman mendahului rekomendasi.** AstaLink harus dapat menjelaskan kembali apa yang dipahaminya tentang situasi pengguna.
2. **Arah mendahului pertanyaan.** Jika data yang tersedia sudah cukup untuk memberi arah awal, AstaLink menyampaikannya sebelum meminta informasi tambahan.
3. **Pertanyaan harus menentukan keputusan.** AstaLink hanya bertanya ketika jawabannya dapat mengubah arah keputusan atau tingkat keyakinan secara material.

## 3. Target Pengguna

### 3.1 Target utama

Target utama adalah calon investor ritel yang sedang menghadapi keputusan pertama atau keputusan baru tentang uang yang dapat dialokasikan, tetapi belum yakin apakah uang tersebut sudah layak masuk ke pasar modal.

Karakteristik situasionalnya antara lain:

- memiliki dana yang tampak seperti surplus;
- belum yakin apakah dana tersebut benar-benar bebas digunakan;
- memiliki pemahaman investasi terbatas atau terfragmentasi;
- membutuhkan bantuan menyusun prioritas, bukan sekadar daftar saham;
- ingin mencoba konsekuensi keputusan tanpa langsung mengeksekusinya.

### 3.2 Beachhead persona

Owner-operator, pemilik usaha kecil, pekerja mandiri, dan orang dengan penghasilan tidak tetap merupakan beachhead persona yang relevan. Mereka sering menghadapi pertanyaan seperti:

> “Pendapatan yang baru masuk ini sebaiknya ditahan, diputar kembali, atau mulai dimasukkan ke investasi?”

Persona ini membantu AstaLink menunjukkan kedalaman pemahaman konteks. Namun, label UMKM tidak boleh menjadi batas permanen produk.

### 3.3 Pengguna yang berdekatan

Produk yang sama dapat bermanfaat bagi:

- freelancer dan pekerja mandiri;
- profesional dengan usaha sampingan;
- kreator dengan pendapatan tidak tetap;
- karyawan yang baru memiliki surplus pertama;
- investor pemula yang perlu meninjau ulang kesiapan dan prioritasnya.

### 3.4 Batas klaim pasar

Keberadaan pengusaha yang juga menjadi investor dapat dibuktikan dari data pasar. Akan tetapi, ukuran tepat irisan “pemilik usaha, mempunyai surplus, belum berinvestasi, membutuhkan bantuan keputusan, dan bersedia menggunakan AI” belum tersedia dari satu dataset yang representatif.

Karena itu, AstaLink tidak boleh mengklaim ukuran pasar dengan mengalikan jumlah UMKM, tingkat literasi, dan jumlah investor dari populasi yang berbeda. Ukuran beachhead perlu divalidasi melalui riset pengguna dan funnel akuisisi aktual.

## 4. Positioning

### 4.1 Positioning utama

> AstaLink adalah financial coach dan investment sandbox yang membantu calon investor memahami kesiapan serta prioritas keuangannya sebelum mengeksplorasi keputusan investasi.

### 4.2 Peran sandbox

Sandbox bukan sekadar fitur simulasi saham. Ia adalah lingkungan aman setelah readiness check. Pengguna dapat:

- membandingkan kemungkinan alokasi;
- melihat trade-off antara kas, bisnis, dan saham;
- memahami dampak risiko;
- menguji tesis tanpa eksekusi otomatis;
- belajar dari alasan di balik rekomendasi.

### 4.3 Peran alokasi bisnis

Alokasi bisnis bukan produk kedua yang berdiri terpisah. Ia merupakan salah satu konteks keputusan yang harus dipahami sebelum menyarankan investasi.

AstaLink tidak diposisikan sebagai ERP, pembukuan lengkap, atau penasihat ekspansi bisnis. Catatan transaksi dan profil bisnis digunakan sejauh diperlukan untuk menjawab pertanyaan alokasi modal dan kesiapan investasi.

### 4.4 Hal yang bukan AstaLink

AstaLink bukan:

- mesin sinyal beli/jual;
- broker yang mengeksekusi keputusan secara otomatis;
- penasihat yang menjanjikan imbal hasil;
- aplikasi pembukuan bisnis lengkap;
- pengganti penasihat keuangan berizin;
- chatbot generik yang selalu menjawab dengan template edukasi.

## 5. Prinsip Pengalaman Pengguna

### 5.1 Pola respons utama

Untuk percakapan yang ambigu atau sensitif, respons ideal mengikuti urutan:

1. **Pemahaman:** sebutkan apa yang dipahami dari konteks pengguna.
2. **Arah:** berikan arah awal berdasarkan data yang sudah ada.
3. **Ketidakpastian:** jelaskan satu hal yang belum diketahui dan dampaknya.
4. **Pertanyaan penentu:** tanyakan satu hal saja jika memang diperlukan.
5. **Aksi:** jalankan analisis atau sandbox setelah konteks mencukupi.

Contoh:

> “Aku memahami Rp10 juta ini berasal dari pemasukan bisnis terakhir dan kamu sedang mempertimbangkan saham. Arah awalnya, dana operasional jangan langsung dianggap sebagai surplus. Dana ini masih dibutuhkan untuk operasional dalam beberapa bulan ke depan, atau sudah benar-benar bebas dialokasikan?”

### 5.2 Unknown adalah informasi

Ketidaktahuan tidak boleh disembunyikan dengan default. Sistem harus membedakan:

- fakta terverifikasi;
- pernyataan pengguna;
- estimasi sistem;
- asumsi eksplisit;
- informasi yang belum diketahui.

### 5.3 Kebiasaan bukan identitas permanen

Pola perilaku pengguna harus memiliki dimensi waktu. Observasi lama tidak boleh selamanya mendefinisikan pengguna jika perilaku dan kondisi finansialnya sudah berubah.

Setiap inferensi kebiasaan idealnya memiliki:

- rentang waktu observasi;
- sumber data;
- tingkat keyakinan;
- bukti pendukung;
- kemungkinan digantikan oleh pola yang lebih baru.

### 5.4 Keputusan tetap milik pengguna

AstaLink memberi pemahaman, simulasi, rekomendasi, dan konsekuensi. Ia tidak mengeksekusi transaksi langsung dari percakapan dan tidak menyamarkan rekomendasi sebagai keputusan final.

## 6. Arsitektur AI Saat Ini

Arsitektur saat ini bersifat graph-oriented dan sebagian besar mengikuti alur:

```text
Pesan pengguna
      ↓
Intent classifier
      ↓
 ┌────┴────────────────┐
Q&A               Permintaan alokasi
                         ↓
                  Layer 0 allocation
                         ↓
             Market + Business + Risk
                         ↓
                     Optimizer
                         ↓
                Legal/compliance check
                         ↓
                      Report
```

Kekuatan utamanya:

- state dan jalur keputusan eksplisit;
- evidence tagging pada profil bisnis;
- hard constraint dan veto deterministik;
- specialist nodes untuk market, business, risk, optimizer, dan legal;
- checkpoint, audit trail, serta approval gate;
- tidak melakukan eksekusi otomatis;
- lebih mudah diuji dan direproduksi dibanding satu agent bebas.

Kelemahan utamanya:

- intent pertama terlalu menentukan seluruh jalur;
- konteks terutama membantu klasifikasi, belum menjadi model keputusan;
- low-confidence reply sudah dinamis, tetapi graph tetap berhenti;
- tidak ada coach yang memilih antara merefleksikan, bertanya, menjelaskan, atau menganalisis;
- profil pengguna bersifat snapshot, bukan temporal;
- jawaban intake melalui chat belum menjadi pembaruan profil terstruktur;
- beberapa default dapat menghasilkan personalisasi semu;
- personal readiness belum seketat business-data completeness;
- legal validation terlalu mudah dibaca sebagai validasi keseluruhan rekomendasi.

## 7. Arsitektur AI yang Dituju

Arsitektur tujuan tetap menggunakan graph. Perubahan utamanya adalah pusat kendali berpindah dari intent router statis ke coach/supervisor yang bekerja di atas shared financial context.

```text
Pesan + conversation history + financial memory
                         ↓
                Financial Context Builder
                         ↓
                  Coach/Supervisor
             ┌───────────┼───────────┐
             ↓           ↓           ↓
       Refleksikan   Tanya 1 hal   Panggil tool/
       pemahaman     penentu       specialist
             └───────────┼───────────┘
                         ↓
                 Readiness/Safety Gate
                         ↓
            Market + Business + Risk tools
                         ↓
                Optimizer deterministik
                         ↓
              Regulatory evidence check
                         ↓
                 Coach response composer
```

### 7.1 Coach/supervisor

Coach adalah pemilik percakapan dan keputusan routing. Ia tidak menghitung portofolio sendiri. Tugasnya:

- membentuk pemahaman situasi;
- mendeteksi tahap keputusan pengguna;
- memilih informasi yang benar-benar menentukan;
- memutuskan apakah perlu bertanya atau memanggil specialist;
- menilai apakah hasil specialist cukup untuk menjawab;
- menyampaikan hasil sesuai tingkat pemahaman pengguna.

### 7.2 Specialist agents dan tools

Specialist dipanggil secara selektif:

- market analyst untuk data dan tesis saham;
- business analyst untuk kebutuhan dan kelayakan bisnis;
- risk specialist untuk risiko portofolio dan kapasitas kerugian;
- critic/devil’s advocate untuk menguji asumsi;
- compliance checker untuk dukungan regulasi;
- transaction capture untuk mencatat peristiwa keuangan.

### 7.3 Komponen deterministik

Komponen berikut tetap berupa kode deterministik:

- emergency-fund checks;
- debt and liquidity constraints;
- evidence completeness;
- concentration limits;
- covariance dan risk metrics;
- optimizer;
- permission, ownership, dan execution gates.

Prinsipnya:

> Gunakan agent untuk judgment dan pemilihan langkah; gunakan kode deterministik untuk calculation dan enforcement.

## 8. Perbandingan Arsitektur Lama dan Baru

| Aspek | Arsitektur saat ini | Arsitektur yang dituju |
| --- | --- | --- |
| Pengendali alur | Intent classifier dan conditional edges | Coach/supervisor dan coaching policy |
| Bentuk graph | Sebagian besar pipeline satu arah | Graph dinamis dengan ask, pause, resume, dan tool loop |
| Konteks | Chat terakhir dan snapshot workspace | Decision context dan financial memory temporal |
| Peran intent | Menentukan jalur utama | Menjadi salah satu sinyal untuk supervisor |
| Missing data | Dapat berakhir pada dead-end atau default | Dipilah menjadi decisive dan non-decisive unknowns |
| Pertanyaan | Berdasarkan low confidence atau intake completeness | Maksimal satu pertanyaan yang dapat mengubah keputusan |
| Kebiasaan | Tidak dimodelkan secara temporal | Observasi bertanggal dengan confidence dan supersession |
| Specialist | Hampir selalu mengikuti pipeline tetap | Dipanggil hanya ketika relevan |
| Kalkulasi | Deterministik, sudah kuat | Dipertahankan dan diperjelas provenance-nya |
| Safety | Veto, legal check, dan approval | Readiness sebelum analisis, lalu risk dan compliance |
| Respons | Report atau jawaban langsung | Pemahaman, arah, uncertainty, lalu aksi |
| Default | Beberapa asumsi tersembunyi | Dihapus, diblokir, atau dilabeli sebagai skenario eksplorasi |
| Legal | Terlihat sebagai kelulusan rekomendasi | Regulatory evidence check dengan cakupan yang eksplisit |

## 9. Strategi Migrasi

Arsitektur baru tidak memerlukan rewrite total. Komponen market, business, risk, optimizer, legal retrieval, checkpoint, audit, dan transaction capture dapat dipertahankan.

Migrasi dilakukan bertahap:

1. memperbaiki readiness dan asumsi tersembunyi;
2. menambahkan `DecisionContext` dan coach/supervisor sebelum routing lama;
3. membuat intake percakapan dapat memperbarui state terstruktur;
4. menambahkan memory temporal dan supersession;
5. mengubah specialist nodes menjadi tools/subgraphs yang dipanggil selektif;
6. memperbaiki semantik compliance dan respons akhir;
7. mengevaluasi kualitas coaching dengan conversation scenarios.

Setiap tahap harus menghasilkan aplikasi yang tetap dapat digunakan dan diuji. Graph lama menjadi fallback selama jalur baru belum stabil.

## 10. Ukuran Keberhasilan

### 10.1 Kualitas pemahaman

- rujukan seperti “uang tadi” diselesaikan ke transaksi yang benar;
- AI mampu menyatakan asal dan fungsi uang tanpa mengarang;
- koreksi pengguna memperbarui pemahaman, bukan diperdebatkan;
- observasi lama tidak mengalahkan fakta baru yang lebih kuat.

### 10.2 Kualitas keputusan

- tidak ada rekomendasi alokasi ketika readiness field yang menentukan belum diketahui;
- jumlah pertanyaan yang tidak diperlukan menurun;
- setiap rekomendasi menyebut asumsi dan ketidakpastian material;
- default atau estimasi selalu dapat dibedakan dari data aktual.

### 10.3 Kualitas pengalaman

- respons membuka dengan pemahaman yang relevan, bukan disclaimer generik;
- satu turn hanya menanyakan satu keputusan utama;
- pengguna dapat melanjutkan percakapan tanpa mengulang data yang sudah tersedia;
- respons penolakan tetap membahas konteks yang sedang berlangsung.

### 10.4 Kualitas sistem

- setiap keputusan dapat ditelusuri ke data dan tool yang digunakan;
- specialist failure tidak menghapus konteks percakapan;
- retry hanya dilakukan jika dapat mengubah hasil;
- latency dan biaya diukur per jalur, bukan hanya per request.

## 11. Hipotesis yang Masih Perlu Divalidasi

- Calon investor menghargai readiness coaching sebelum sandbox.
- Owner-operator merupakan beachhead yang dapat dijangkau secara efisien.
- Satu pertanyaan penentu meningkatkan completion dibanding formulir panjang.
- Penjelasan “belum siap berinvestasi” meningkatkan kepercayaan, bukan abandonment.
- Pengguna bersedia membagikan konteks keuangan yang cukup untuk personalisasi.
- Setelah readiness tercapai, sandbox meningkatkan niat dan kualitas keputusan investasi.

Hipotesis tersebut tidak boleh ditulis sebagai fakta bisnis sampai didukung riset pengguna atau data penggunaan.

## 12. Keputusan Arsitektural Utama

1. AstaLink tetap graph-oriented.
2. Graph dipimpin satu coach/supervisor, bukan kumpulan agent otonom yang setara.
3. Specialist agents dipanggil secara selektif.
4. Kalkulasi dan enforcement tetap deterministik.
5. Shared state diperluas menjadi decision context dan temporal financial memory.
6. Unknown tidak diisi dengan default tanpa label.
7. Readiness mendahului rekomendasi investasi.
8. Compliance tidak dipresentasikan sebagai jaminan suitability atau keamanan.
9. UMKM adalah use case utama, bukan batas pasar permanen.
10. Arsitektur lama dimigrasikan secara inkremental, bukan diganti sekaligus.
