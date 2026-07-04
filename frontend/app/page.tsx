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
    accent: "text-green-400",
    iconBg: "bg-[#22c55e]/10 border-[#22c55e]/30",
  },
  {
    step: "02",
    icon: ShieldCheck,
    title: "Verifikasi OJK Otomatis",
    body: "Setiap rekomendasi divalidasi terhadap regulasi IDX dan OJK secara otomatis. Tidak ada celah kepatuhan, tidak ada risiko hukum.",
    accent: "text-emerald-400",
    iconBg: "bg-emerald-500/10 border-emerald-500/25",
  },
  {
    step: "03",
    icon: UserCheck,
    title: "Kamu yang Memutuskan",
    body: "Tidak ada transaksi tanpa PIN dan konfirmasimu. Human-in-the-loop bukan tambahan — ini inti arsitektur Astalink.",
    accent: "text-stone-300",
    iconBg: "bg-stone-400/10 border-stone-400/20",
  },
] as const;

const CARD_CHECKS = [
  ["Analisis Fundamental", "Kuat"],
  ["Indikator Teknikal", "Uptrend"],
  ["OJK Compliance", "Terverifikasi"],
] as const;

const TRUST_CHIPS = [
  { label: "AI Multi-Agen", cls: "border-[#22c55e]/40 bg-[#22c55e]/[0.08] text-green-400" },
  { label: "OJK Verified", cls: "border-[#22c55e]/40 bg-[#22c55e]/[0.08] text-green-400" },
  { label: "Human-in-Loop", cls: "border-[#22c55e]/40 bg-[#22c55e]/[0.08] text-green-400" },
  { label: "PIN Konfirmasi", cls: "border-[#22c55e]/40 bg-[#22c55e]/[0.08] text-green-400" },
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

      {/* ─── Nav — floating pill, chrome hitam ─── */}
      <nav className="fixed top-4 inset-x-0 z-50 px-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-2 rounded-full border border-sidebar-border bg-sidebar/85 backdrop-blur-xl py-2 pl-4 pr-2 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)]">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="w-6 h-6 rounded-md bg-sidebar-primary/15 border border-sidebar-primary/30 flex items-center justify-center">
              <span className="text-sidebar-primary text-[8px] font-black font-mono leading-none">A</span>
            </div>
            <span className="text-sidebar-foreground font-bold text-sm tracking-tight">Astalink</span>
            <span className="text-sidebar-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
          </Link>

          {/* Center links — pill hover */}
          <div className="hidden md:flex items-center gap-1">
            {[
              { href: "#fitur", label: "Fitur" },
              { href: "#statistik", label: "Statistik" },
              { href: "#mulai", label: "Mulai" },
            ].map(({ href, label }) => (
              <a
                key={href}
                href={href}
                className="px-3.5 py-1.5 rounded-full text-sm font-medium text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors duration-150"
              >
                {label}
              </a>
            ))}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            <Link
              href="/login"
              className="hidden sm:block px-3.5 py-1.5 rounded-full text-sm font-medium text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors duration-150"
            >
              Login
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-primary-foreground font-semibold text-xs hover:bg-primary/90 transition-all duration-200"
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
        <div className="pointer-events-none absolute -top-24 left-1/4 w-[700px] h-[500px] rounded-full bg-chart-2/[0.07] blur-[130px]" />
        <div className="pointer-events-none absolute top-32 right-8 w-[350px] h-[350px] rounded-full bg-emerald-500/[0.05] blur-[100px]" />

        <div className="relative mx-auto max-w-6xl">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-16 lg:gap-10 items-center">

            {/* Left: Copy */}
            <div className="max-w-[560px]">
              {/* Eyebrow */}
              <div className="flex flex-wrap items-center gap-2.5 mb-8">
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/[0.07] text-emerald-400 text-[11px] font-semibold uppercase tracking-[0.15em]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Teregulasi OJK
                </span>
                <span className="text-muted-foreground/60 text-[11px] font-mono">× IDX Compliance</span>
              </div>

              {/* Headline */}
              <h1 className="font-heading text-[2.6rem] md:text-[3.4rem] lg:text-[3.8rem] font-bold leading-[1.07] tracking-tight mb-6">
                <span
                  className="block bg-clip-text text-transparent pb-2"
                  style={{
                    backgroundImage:
                      "linear-gradient(130deg, oklch(0.723 0.219 149.579) 0%, oklch(0.871 0.15 154.449) 100%)",
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
                  className="inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-full bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-all duration-300"
                >
                  Mulai Gratis
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center px-8 py-3.5 rounded-full border border-border bg-secondary text-foreground font-semibold text-sm hover:bg-accent hover:border-foreground/20 transition-all duration-200"
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
              <div className="pointer-events-none absolute inset-0 rounded-3xl bg-chart-2/[0.11] blur-[80px]" />

              <div className="relative w-full max-w-[390px]">

                {/* Floating: Portfolio performance */}
                <div className="absolute z-20 -bottom-4 -right-3 px-3.5 py-2.5 rounded-xl border border-border bg-background shadow-[0_12px_32px_-8px_rgba(0,0,0,0.18)]">
                  <div className="text-muted-foreground/70 text-[10px] font-mono mb-1 uppercase tracking-wider">Portfolio hari ini</div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-emerald-400 font-mono font-bold text-sm">+2.4%</span>
                    <span className="text-muted-foreground/60 text-[10px] font-mono">↑ Rp 4.2jt</span>
                  </div>
                </div>

                {/* Main card — panel hitam, echo chrome navbar */}
                <div className="relative rounded-2xl border border-white/[0.08] bg-sidebar shadow-[0_40px_100px_-30px_rgba(10,14,12,0.45)] overflow-hidden">

                  {/* Card header */}
                  <div className="px-5 py-4 border-b border-white/[0.07] flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-[#22c55e]/15 border border-[#22c55e]/30 flex items-center justify-center">
                        <span className="text-[#22c55e] text-[9px] font-black font-mono">AI</span>
                      </div>
                      <div>
                        <div className="text-[#fafafa] font-semibold text-[13px] leading-none">Rekomendasi AI</div>
                        <div className="text-[#a1a1aa] text-[10px] mt-0.5 font-mono">LangGraph Pipeline</div>
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
                          <span className="text-[#fafafa] font-mono font-bold text-[1.35rem] tracking-tight leading-none">
                            BBCA
                          </span>
                        </div>
                        <div className="text-[#a1a1aa] text-xs">500 lot · Bank Central Asia</div>
                        <div className="font-mono text-sm mt-0.5">
                          <span className="text-[#fafafa] font-semibold">Rp 9.875</span>
                          <span className="text-[#a1a1aa] text-xs ml-1">/saham</span>
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
                            <span className="text-[#a1a1aa] text-xs">{label}</span>
                          </div>
                          <span className="text-emerald-400 text-xs font-medium">{val}</span>
                        </div>
                      ))}
                    </div>

                    {/* Return */}
                    <div className="flex items-center justify-between py-1.5 border-t border-white/[0.06]">
                      <span className="text-[#a1a1aa] text-xs">Estimasi return (90 hari)</span>
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
                        className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-[#a1a1aa] text-xs font-semibold hover:bg-white/[0.06] transition-colors cursor-default"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none">
                          <path d="M4 4l6 6M10 4l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                        Tolak
                      </button>
                    </div>

                    <p className="text-[#a1a1aa]/60 text-[10px] text-center font-mono">
                      Transaksi memerlukan konfirmasi PIN
                    </p>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ─── Ticker Band — strip terminal hitam ─── */}
      <div className="border-y border-sidebar-border bg-sidebar py-3 overflow-hidden">
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
              className="flex items-center gap-2.5 px-6 shrink-0 border-r border-white/[0.07]"
            >
              <span className="text-[#fafafa]/80 font-mono font-semibold text-[11px]">{sym}</span>
              <span className="text-[#a1a1aa] font-mono text-[11px]">{px}</span>
              <span className={`font-mono text-[11px] font-semibold ${up ? "text-emerald-400" : "text-red-400"}`}>
                {ch}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ─── Pipeline ─── */}
      <section id="fitur" className="relative py-28 px-6 overflow-hidden scroll-mt-24">
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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {PIPELINE_STEPS.map(({ step, icon: Icon, title, body, accent, iconBg }, i) => (
              <div key={step}>
                <div className="flex items-center gap-3 mb-5">
                  <div className={`w-10 h-10 rounded-xl border flex items-center justify-center shrink-0 ${iconBg}`}>
                    <Icon className={`w-[18px] h-[18px] ${accent}`} />
                  </div>
                  <span className={`font-mono text-xs font-bold opacity-40 ${accent}`}>{step}</span>
                  {/* Connector: segmen per-step, menjembatani gap grid (-mr-10 = gap-10) hingga ikon berikutnya */}
                  {i < PIPELINE_STEPS.length - 1 && (
                    <span
                      aria-hidden
                      className={`hidden md:block h-px flex-1 -mr-10 bg-gradient-to-r ${
                        i === 0
                          ? "from-green-500/40 to-emerald-500/40"
                          : "from-emerald-500/40 to-stone-400/40"
                      }`}
                    />
                  )}
                </div>
                <h3 className="text-foreground font-semibold text-[0.9375rem] leading-snug mb-3">{title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Stats Strip ─── */}
      <section id="statistik" className="border-t border-border scroll-mt-24">
        <div className="mx-auto max-w-5xl px-6 grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-border">
          {STATS.map(({ val, unit, label }) => (
            <div key={label} className="px-8 py-10 text-center">
              <div className="font-mono text-[2.4rem] font-bold text-foreground leading-none mb-1">
                {val}
              </div>
              <div className="text-chart-2 text-xs font-semibold mb-0.5">{unit}</div>
              <div className="text-muted-foreground/70 text-[11px] uppercase tracking-wider">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section id="mulai" className="relative py-28 px-6 text-center overflow-hidden border-t border-border scroll-mt-24">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_55%_at_50%_50%,oklch(0.723_0.219_149.579/0.07)_0%,transparent_100%)]" />
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
            className="inline-flex items-center justify-center gap-2.5 px-10 py-4 rounded-full bg-primary text-primary-foreground font-semibold text-base hover:bg-primary/90 transition-all duration-300"
          >
            Buat Akun Gratis
            <ArrowRight className="w-5 h-5" />
          </Link>
          <p className="text-muted-foreground/60 text-xs mt-6 font-mono tracking-wide">
            Teregulasi OJK · Data Terenkripsi · Tidak Ada Iklan
          </p>
        </div>
      </section>

      {/* ─── Footer — chrome hitam, senada navbar ─── */}
      <footer className="border-t border-sidebar-border bg-sidebar">
        <div className="mx-auto max-w-6xl px-6 py-14 grid gap-10 md:grid-cols-[1.6fr_1fr_1fr]">
          {/* Brand */}
          <div className="space-y-4 max-w-xs">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-sidebar-primary/15 border border-sidebar-primary/30 flex items-center justify-center">
                <span className="text-sidebar-primary text-[9px] font-black font-mono">A</span>
              </div>
              <span className="text-sidebar-foreground font-bold text-sm tracking-tight">Astalink</span>
              <span className="text-sidebar-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
            </div>
            <p className="text-sidebar-foreground/50 text-sm leading-relaxed">
              Platform investasi saham IDX dengan AI multi-agen, kepatuhan OJK otomatis,
              dan kontrol penuh di tanganmu.
            </p>
            <p className="text-sidebar-foreground/35 text-[10px] font-mono tracking-wide">
              Teregulasi OJK · IDX Compliance
            </p>
          </div>

          {/* Menu */}
          <div>
            <p className="text-sidebar-foreground/40 text-[10px] font-black font-mono uppercase tracking-[0.18em] mb-4">
              Menu
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/dashboard" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Dashboard</Link></li>
              <li><Link href="/chatbot" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">AI Chatbot</Link></li>
              <li><Link href="/news" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Market News</Link></li>
              <li><Link href="/legal-docs" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Legal Docs</Link></li>
            </ul>
          </div>

          {/* Akun */}
          <div>
            <p className="text-sidebar-foreground/40 text-[10px] font-black font-mono uppercase tracking-[0.18em] mb-4">
              Akun
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/login" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Login</Link></li>
              <li><Link href="/signup" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Buat Akun Gratis</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-sidebar-border">
          <div className="mx-auto max-w-6xl px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-3">
            <p className="text-sidebar-foreground/40 text-xs">
              © 2026 Astalink AI. Digdaya × Hackathon 2026.
            </p>
            <p className="text-sidebar-foreground/35 text-[10px] leading-relaxed text-center md:text-right max-w-md">
              Investasi saham mengandung risiko. Kinerja masa lalu tidak menjamin hasil di masa depan.
            </p>
          </div>
        </div>
      </footer>

    </div>
  );
}
