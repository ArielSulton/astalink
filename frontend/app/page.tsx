import Link from "next/link";
import { ArrowRight, Brain, ShieldCheck, UserCheck } from "lucide-react";

const IDX_TICKERS = [
  { sym: "BBCA", px: "9.875", ch: "+1.8%", up: true },
  { sym: "TLKM", px: "3.420", ch: "+0.6%", up: true },
  { sym: "BBRI", px: "4.890", ch: "−0.4%", up: false },
  { sym: "ASII", px: "5.200", ch: "+2.1%", up: true },
  { sym: "BMRI", px: "6.375", ch: "+1.2%", up: true },
  { sym: "GOTO", px: "58", ch: "−1.7%", up: false },
  { sym: "BYAN", px: "17.500", ch: "+3.2%", up: true },
  { sym: "ANTM", px: "1.645", ch: "+0.9%", up: true },
  { sym: "MDKA", px: "2.710", ch: "−0.8%", up: false },
  { sym: "INDF", px: "6.900", ch: "+1.4%", up: true },
  { sym: "UNVR", px: "2.980", ch: "−1.1%", up: false },
  { sym: "ICBP", px: "9.450", ch: "+0.7%", up: true },
] as const;

const PIPELINE_STEPS = [
  {
    step: "01",
    icon: Brain,
    title: "Analisis Multi-Agen",
    body: "LangGraph AI pipeline memindai fundamental, teknikal, sentimen berita, dan risiko portofolio secara paralel — dalam hitungan detik.",
    accent: "text-blue-400",
    iconBg: "bg-blue-500/10 border-blue-500/20",
  },
  {
    step: "02",
    icon: ShieldCheck,
    title: "Verifikasi OJK Otomatis",
    body: "Setiap rekomendasi divalidasi terhadap regulasi IDX dan OJK secara otomatis. Tidak ada celah kepatuhan, tidak ada risiko hukum.",
    accent: "text-emerald-400",
    iconBg: "bg-emerald-500/10 border-emerald-500/20",
  },
  {
    step: "03",
    icon: UserCheck,
    title: "Kamu yang Memutuskan",
    body: "Tidak ada transaksi tanpa PIN dan konfirmasimu. Human-in-the-loop bukan tambahan — ini inti arsitektur Astalink.",
    accent: "text-violet-400",
    iconBg: "bg-violet-500/10 border-violet-500/20",
  },
] as const;

const CARD_CHECKS = [
  ["Analisis Fundamental", "Kuat"],
  ["Indikator Teknikal", "Uptrend"],
  ["OJK Compliance", "Terverifikasi"],
] as const;

const TRUST_CHIPS = [
  { label: "AI Multi-Agen", cls: "border-blue-500/25 bg-blue-500/[0.07] text-blue-400" },
  { label: "OJK Verified",  cls: "border-emerald-500/25 bg-emerald-500/[0.07] text-emerald-400" },
  { label: "Human-in-Loop", cls: "border-violet-500/25 bg-violet-500/[0.07] text-violet-400" },
  { label: "PIN Konfirmasi", cls: "border-amber-500/25 bg-amber-500/[0.07] text-amber-400" },
] as const;

const STATS = [
  { val: "5",    unit: "Node",      label: "AI Pipeline"    },
  { val: "4+",   unit: "Indikator", label: "Teknikal"       },
  { val: "100%", unit: "Kontrol",   label: "di Tanganmu"    },
  { val: "0",    unit: "Transaksi", label: "Tanpa Izinmu"   },
] as const;

function Checkmark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 10 10" fill="none">
      <path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">

      {/* ─── Nav ─── */}
      <nav className="fixed top-0 inset-x-0 z-50 h-14 border-b border-white/[0.06] bg-background/80 backdrop-blur-xl">
        <div className="mx-auto max-w-6xl px-6 h-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-primary/15 border border-primary/25 flex items-center justify-center">
              <span className="text-primary text-[8px] font-black font-mono leading-none">A</span>
            </div>
            <span className="text-foreground font-bold text-sm tracking-tight">Astalink</span>
            <span className="text-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="hidden sm:block text-muted-foreground hover:text-foreground text-sm font-medium transition-colors duration-150"
            >
              Login
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 hover:shadow-[0_0_20px_oklch(0.538_0.243_264/0.4)] transition-all duration-200"
            >
              Mulai Gratis
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Ambient orbs */}
        <div className="pointer-events-none absolute -top-24 left-1/4 w-[700px] h-[500px] rounded-full bg-primary/[0.07] blur-[130px]" />
        <div className="pointer-events-none absolute top-32 right-8 w-[350px] h-[350px] rounded-full bg-emerald-500/[0.05] blur-[100px]" />

        <div className="relative mx-auto max-w-6xl">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-16 lg:gap-10 items-center">

            {/* Left: Copy */}
            <div className="max-w-[560px]">
              {/* Eyebrow */}
              <div className="flex flex-wrap items-center gap-2.5 mb-8">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/[0.08] text-emerald-400 text-[11px] font-semibold uppercase tracking-[0.15em]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Teregulasi OJK
                </span>
                <span className="text-muted-foreground/40 text-[11px] font-mono">× IDX Compliance</span>
              </div>

              {/* Headline */}
              <h1 className="font-heading text-[2.6rem] md:text-[3.4rem] lg:text-[3.8rem] font-bold leading-[1.07] tracking-tight mb-6">
                <span
                  className="block bg-clip-text text-transparent pb-2"
                  style={{
                    backgroundImage:
                      "linear-gradient(130deg, oklch(0.538 0.243 264) 0%, oklch(0.72 0.13 210) 100%)",
                  }}
                >
                  AI yang menganalisis.
                </span>
                <span className="block">Kamu yang memutuskan.</span>
              </h1>

              <p className="text-muted-foreground text-base md:text-[1.0625rem] leading-relaxed mb-10 max-w-[480px]">
                Sistem AI multi-agen memindai pasar IDX, memverifikasi kepatuhan OJK,
                dan menunggu konfirmasimu — sebelum satu pun transaksi terjadi.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row gap-3 mb-10">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 hover:shadow-[0_0_30px_oklch(0.538_0.243_264/0.45)] transition-all duration-300"
                >
                  Mulai Gratis
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center px-8 py-3.5 rounded-full border border-white/[0.1] bg-white/[0.04] text-foreground font-semibold text-sm hover:bg-white/[0.07] hover:border-white/[0.16] transition-all duration-200"
                >
                  Masuk ke Akun
                </Link>
              </div>

              {/* Trust chips */}
              <div className="flex flex-wrap gap-2">
                {TRUST_CHIPS.map(({ label, cls }) => (
                  <span key={label} className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium ${cls}`}>
                    <Checkmark className="w-2.5 h-2.5" />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: Approval Card Mock */}
            <div className="relative flex justify-center lg:justify-start">
              {/* Card glow */}
              <div className="pointer-events-none absolute inset-0 rounded-3xl bg-primary/[0.11] blur-[80px]" />

              <div className="relative w-full max-w-[390px]">

                {/* Floating: Portfolio performance */}
                <div className="absolute z-20 -bottom-4 -right-3 px-3.5 py-2.5 rounded-xl border border-white/[0.08] bg-background shadow-xl">
                  <div className="text-muted-foreground/50 text-[10px] font-mono mb-1 uppercase tracking-wider">Portfolio hari ini</div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-emerald-400 font-mono font-bold text-sm">+2.4%</span>
                    <span className="text-muted-foreground/40 text-[10px] font-mono">↑ Rp 4.2jt</span>
                  </div>
                </div>

                {/* Main card */}
                <div className="relative rounded-2xl border border-white/[0.1] bg-card shadow-[0_40px_100px_-20px_rgba(0,0,0,0.75)] overflow-hidden">

                  {/* Card header */}
                  <div className="px-5 py-4 border-b border-white/[0.07] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center">
                        <span className="text-primary text-[9px] font-black font-mono">AI</span>
                      </div>
                      <div>
                        <div className="text-foreground font-semibold text-[13px] leading-none">Rekomendasi AI</div>
                        <div className="text-muted-foreground text-[10px] mt-0.5 font-mono">LangGraph Pipeline</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Aktif
                    </div>
                  </div>

                  <div className="p-5 space-y-4">
                    {/* Recommendation */}
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                            BUY
                          </span>
                          <span className="text-foreground font-mono font-bold text-[1.35rem] tracking-tight leading-none">
                            BBCA
                          </span>
                        </div>
                        <div className="text-muted-foreground text-xs">500 lot · Bank Central Asia</div>
                        <div className="font-mono text-sm mt-0.5">
                          <span className="text-foreground font-semibold">Rp 9.875</span>
                          <span className="text-muted-foreground text-xs ml-1">/saham</span>
                        </div>
                      </div>
                      {/* Sparkline */}
                      <svg width="68" height="36" viewBox="0 0 68 36" className="text-emerald-400 opacity-75 shrink-0 mt-1">
                        <polyline
                          points="0,30 12,24 24,27 36,16 48,19 58,10 68,7"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>

                    {/* Analysis checks */}
                    <div className="rounded-xl bg-white/[0.025] border border-white/[0.06] px-3.5 py-3 space-y-2.5">
                      {CARD_CHECKS.map(([label, val]) => (
                        <div key={label} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full bg-emerald-500/15 flex items-center justify-center shrink-0">
                              <Checkmark className="w-2.5 h-2.5 text-emerald-400" />
                            </div>
                            <span className="text-muted-foreground text-xs">{label}</span>
                          </div>
                          <span className="text-emerald-400 text-xs font-medium">{val}</span>
                        </div>
                      ))}
                    </div>

                    {/* Return */}
                    <div className="flex items-center justify-between py-1.5 border-t border-white/[0.06]">
                      <span className="text-muted-foreground text-xs">Estimasi return (90 hari)</span>
                      <span className="text-emerald-400 font-mono font-bold text-sm">+8.2%</span>
                    </div>

                    {/* Action buttons */}
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-semibold hover:bg-emerald-500/25 transition-colors cursor-default"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none">
                          <path d="M2.5 7l3 3L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        Setujui
                      </button>
                      <button
                        type="button"
                        className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-muted-foreground text-xs font-semibold hover:bg-white/[0.06] transition-colors cursor-default"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none">
                          <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                        Tolak
                      </button>
                    </div>

                    <p className="text-muted-foreground/40 text-[10px] text-center font-mono">
                      Transaksi memerlukan konfirmasi PIN
                    </p>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ─── Ticker Band ─── */}
      <div className="border-y border-white/[0.06] bg-white/[0.015] py-3 overflow-hidden">
        <div
          className="flex"
          style={{
            width: "max-content",
            animation: "marquee 42s linear infinite",
            willChange: "transform",
          }}
        >
          {[...IDX_TICKERS, ...IDX_TICKERS].map(({ sym, px, ch, up }, i) => (
            <div
              key={i}
              className="flex items-center gap-2.5 px-6 shrink-0 border-r border-white/[0.05]"
            >
              <span className="text-foreground/70 font-mono font-semibold text-[11px]">{sym}</span>
              <span className="text-muted-foreground font-mono text-[11px]">{px}</span>
              <span className={`font-mono text-[11px] font-semibold ${up ? "text-emerald-400" : "text-red-400"}`}>
                {ch}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ─── Pipeline ─── */}
      <section className="relative py-28 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-grid-pattern opacity-25" />
        <div className="relative mx-auto max-w-5xl z-10">
          <div className="text-center mb-16">
            <p className="text-muted-foreground/50 text-[11px] font-mono uppercase tracking-[0.2em] mb-4">
              Pipeline AI
            </p>
            <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              Tiga lapisan yang melindungi investasimu.
            </h2>
            <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto leading-relaxed">
              Setiap rekomendasi melewati analisis, verifikasi regulasi, dan konfirmasimu — baru kemudian dieksekusi.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative">
            {/* Desktop connector line */}
            <div className="hidden md:block absolute top-5 left-[calc(16.67%+28px)] right-[calc(16.67%+28px)] h-px bg-gradient-to-r from-blue-500/25 via-emerald-500/25 to-violet-500/25 pointer-events-none" />

            {PIPELINE_STEPS.map(({ step, icon: Icon, title, body, accent, iconBg }) => (
              <div key={step}>
                <div className="flex items-center gap-3 mb-5">
                  <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${iconBg}`}>
                    <Icon className={`w-[18px] h-[18px] ${accent}`} />
                  </div>
                  <span className={`font-mono text-xs font-bold opacity-40 ${accent}`}>{step}</span>
                </div>
                <h3 className="text-foreground font-semibold text-[0.9375rem] leading-snug mb-3">{title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Stats Strip ─── */}
      <section className="border-t border-white/[0.06]">
        <div className="mx-auto max-w-5xl px-6 grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-white/[0.06]">
          {STATS.map(({ val, unit, label }) => (
            <div key={label} className="px-8 py-10 text-center">
              <div className="font-mono text-[2.4rem] font-bold text-foreground leading-none mb-1 text-glow">
                {val}
              </div>
              <div className="text-primary text-xs font-semibold mb-0.5">{unit}</div>
              <div className="text-muted-foreground/50 text-[11px] uppercase tracking-wider">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="relative py-28 px-6 text-center overflow-hidden border-t border-white/[0.06]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_55%_at_50%_50%,oklch(0.538_0.243_264/0.09)_0%,transparent_100%)]" />
        <div className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-20" />

        <div className="relative max-w-lg mx-auto z-10">
          <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-5">
            Mulai investasi yang lebih cerdas.
          </h2>
          <p className="text-muted-foreground text-base mb-10 leading-relaxed">
            Buat akun gratis dan analisis portofolio IDX pertamamu dalam 2 menit.
            Tidak perlu kartu kredit.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center justify-center gap-2.5 px-10 py-4 rounded-full bg-primary text-primary-foreground font-semibold text-base hover:bg-primary/90 hover:shadow-[0_0_45px_oklch(0.538_0.243_264/0.5)] transition-all duration-300"
          >
            Buat Akun Gratis
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-muted-foreground/35 text-xs mt-6 font-mono tracking-wide">
            Teregulasi OJK · Data Terenkripsi · Tidak Ada Iklan
          </p>
        </div>
      </section>

    </div>
  );
}
