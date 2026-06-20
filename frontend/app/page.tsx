import Link from "next/link";
import { Shield, TrendingUp, UserCheck } from "lucide-react";

const FEATURES = [
  {
    icon: TrendingUp,
    title: "Analisis Multi-Dimensi",
    desc: "AI menganalisis data pasar real-time, fundamental bisnis, dan risiko portofolio secara bersamaan untuk rekomendasi alokasi yang optimal.",
  },
  {
    icon: Shield,
    title: "Kepatuhan Hukum Otomatis",
    desc: "Setiap alokasi diverifikasi terhadap regulasi IDX dan OJK secara otomatis sebelum diteruskan — tidak ada celah kepatuhan.",
  },
  {
    icon: UserCheck,
    title: "Kontrol di Tangan Anda",
    desc: "Tidak ada transaksi tanpa PIN konfirmasi Anda. Human-in-the-loop bawaan memastikan Anda selalu yang memutuskan terakhir.",
  },
] as const;

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* ── Dark Hero ── */}
      <section className="bg-[#0a0b0d] px-6 py-28 text-center">
        <div className="mx-auto max-w-2xl">
          <p className="text-[#0052ff] text-[11px] font-semibold uppercase tracking-[0.2em] mb-5">
            Astalink AI
          </p>
          <h1 className="text-white text-5xl font-normal leading-[1.05] tracking-tight mb-6">
            Investasi Saham IDX
            <br />
            dengan Kecerdasan AI
          </h1>
          <p className="text-[#a8acb3] text-lg leading-relaxed mb-10 max-w-lg mx-auto">
            Analisis pasar otomatis, kepatuhan hukum bawaan, dan persetujuan
            pengguna sebelum setiap transaksi.
          </p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/signup"
              className="px-8 py-3 rounded-full bg-[#0052ff] text-white font-semibold text-sm hover:bg-[#003ecc] transition-colors"
            >
              Mulai Sekarang
            </Link>
            <Link
              href="/login"
              className="px-8 py-3 rounded-full border border-white/20 text-white font-semibold text-sm hover:border-white/50 transition-colors"
            >
              Login
            </Link>
          </div>
        </div>
      </section>

      {/* ── Feature Grid ── */}
      <section className="bg-white px-6 py-24">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-[#0a0b0d] text-3xl font-normal text-center tracking-tight mb-12">
            Cara Kerja Astalink
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="rounded-2xl border border-[#dee1e6] p-8"
              >
                <div className="w-10 h-10 rounded-full bg-[#eef0f3] flex items-center justify-center mb-5">
                  <Icon className="h-5 w-5 text-[#0052ff]" />
                </div>
                <h3 className="text-[#0a0b0d] font-semibold text-base mb-2">
                  {title}
                </h3>
                <p className="text-[#5b616e] text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats Band (light gray) ── */}
      <section className="bg-[#f7f7f7] px-6 py-16">
        <div className="mx-auto max-w-3xl grid grid-cols-3 gap-8 text-center">
          {[
            { value: "5", label: "Node AI Pipeline" },
            { value: "4", label: "Indikator Teknikal" },
            { value: "100%", label: "Kontrol Pengguna" },
          ].map(({ value, label }) => (
            <div key={label}>
              <div className="font-mono text-4xl font-medium text-[#0a0b0d]">
                {value}
              </div>
              <div className="text-[#5b616e] text-sm mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Dark CTA Band ── */}
      <section className="bg-[#0a0b0d] px-6 py-24 text-center">
        <h2 className="text-white text-4xl font-normal tracking-tight mb-6">
          Siap investasi lebih cerdas?
        </h2>
        <p className="text-[#a8acb3] text-base mb-8">
          Buat akun gratis dan mulai analisis portofolio pertama Anda dalam menit.
        </p>
        <Link
          href="/signup"
          className="inline-block px-10 py-4 rounded-full bg-[#0052ff] text-white font-semibold text-base hover:bg-[#003ecc] transition-colors"
        >
          Buat Akun Gratis
        </Link>
      </section>
    </div>
  );
}
