import { Fragment } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Brain, Users, Zap, Lock, CreditCard, Check as CheckIcon, X as XIcon } from "lucide-react";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { PricingCards } from "@/components/pricing/pricing-cards";

const PRICING_TIER_NAMES = ["Gratis", "Pro", "Enterprise"] as const;

const COMPARISON_FEATURES = [
  { category: "Analisis AI", features: [
    { key: "multiAgent", label: "Pipeline multi-agen (fundamental, teknikal, sentimen, risiko)", tiers: [false, true, true] },
    { key: "fundamental", label: "Analisis fundamental mendalam (rasio keuangan, valuation)", tiers: [false, true, true] },
    { key: "technical", label: "Indikator teknikal (RSI, MACD, MA, Bollinger, dll)", tiers: [true, true, true] },
    { key: "sentiment", label: "Analisis sentimen berita & media sosial", tiers: [false, true, true] },
    { key: "risk", label: "Risk profiling & portfolio optimization", tiers: [false, true, true] },
  ]},
  { category: "Kepatuhan & Regulasi", features: [
    { key: "ojk", label: "Verifikasi OJK & IDX compliance otomatis", tiers: [true, true, true] },
    { key: "customReg", label: "Custom regulasi & whitelist institusi", tiers: [false, false, true] },
    { key: "audit", label: "Audit trail & compliance logging", tiers: [false, false, true] },
  ]},
  { category: "Data & Notifikasi", features: [
    { key: "realtime", label: "Data pasar real-time", tiers: [false, true, true] },
    { key: "alerts", label: "Alert harga, volume, & teknikal custom", tiers: [false, true, true] },
    { key: "notif", label: "Notifikasi (Email + WhatsApp)", tiers: [true, true, true] },
    { key: "watchlist", label: "Watchlist tak terbatas", tiers: [false, true, true] },
  ]},
  { category: "Tools & Ekspor", features: [
    { key: "backtest", label: "Backtesting strategi (5 tahun data)", tiers: [false, true, true] },
    { key: "export", label: "Ekspor laporan PDF/Excel", tiers: [false, true, true] },
    { key: "api", label: "API access", tiers: [false, true, true] },
    { key: "webhook", label: "Webhook & integrasi broker", tiers: [false, false, true] },
  ]},
  { category: "Support & Akun", features: [
    { key: "history", label: "Riwayat chat AI", tiers: [true, true, true] },
    { key: "priority", label: "Prioritas support", tiers: [false, true, true] },
    { key: "dedicated", label: "Dedicated account manager", tiers: [false, false, true] },
    { key: "sla", label: "SLA 99.9%", tiers: [false, false, true] },
    { key: "seats", label: "Multi-user workspace", tiers: [false, false, true] },
    { key: "training", label: "Training & onboarding", tiers: [false, false, true] },
  ]},
] as const;

const FAQ = [
  {
    q: "Apakah bisa upgrade/downgrade kapan saja?",
    a: "Ya, Anda bisa mengubah paket kapan saja. Upgrade berlaku segera, downgrade berlaku di awal siklus billing berikutnya. Tidak ada biaya tambahan untuk perubahan paket.",
  },
  {
    q: "Apakah ada percobaan gratis untuk paket Pro?",
    a: "Ya, paket Pro menawarkan uji coba 14 hari gratis tanpa kartu kredit. Selama uji coba, Anda mendapat akses penuh ke semua fitur Pro. Bisa dibatalkan kapan saja.",
  },
  {
    q: "Bagaimana cara pembayaran?",
    a: "Menerima transfer bank (BCA, BRI, Mandiri, BNI), e-wallet (GoPay, OVO, DANA, ShopeePay), dan kartu kredit/debit via payment gateway terpercaya. Faktur pajak tersedia untuk Enterprise.",
  },
  {
    q: "Apakah data saya aman?",
    a: "Ya. Data terenkripsi AES-256 saat transit dan at-rest. Server di AWS Jakarta region (data residency Indonesia). SOC 2 Type II certified. Tidak menjual data ke pihak ketiga.",
  },
  {
    q: "Apa beda Gratis vs Pro untuk verifikasi OJK?",
    a: "Kedua paket mendapat verifikasi OJK otomatis yang sama. Beda utamanya: Gratis terbatas 3 saham & riwayat 7 hari, Pro tak terbatas + analisis fundamental + backtesting + notifikasi real-time.",
  },
  {
    q: "Bisa custom paket Enterprise untuk tim kecil?",
    a: "Tentu. Enterprise dimulai dari 5 seats. Jika tim Anda <5 orang tapi butuh fitur Enterprise (white-label, API unlimited, dll), hubungi kami untuk penawaran custom.",
  },
] as const;

const TRUST_INDICATORS = [
  { label: "Teregulasi OJK", icon: ShieldCheck },
  { label: "Data Terenkripsi", icon: Lock },
  { label: "Real-time IDX", icon: Zap },
  { label: "AI Multi-Agen", icon: Brain },
  { label: "Human-in-the-Loop", icon: Users },
  { label: "Zero Hidden Fees", icon: CreditCard },
] as const;

export const metadata = {
  title: "Harga | AstaLink AI",
  description: "Pilih paket yang tepat untuk analisis portofolio saham IDX dengan AI multi-agen, verifikasi OJK otomatis, dan kontrol penuh di tangan Anda. Mulai dari gratis.",
};

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* ─── Nav — floating pill ─── */}
      <nav className="fixed top-4 inset-x-0 z-50 px-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 rounded-full border border-sidebar-border bg-sidebar/85 backdrop-blur-xl py-2 pl-4 pr-2 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)]">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="w-6 h-6 flex items-center justify-center">
              <Image src="/astalink.png" alt="Astalink" width={24} height={24} className="w-6 h-6 object-contain" />
            </div>
            <span className="text-sidebar-foreground font-bold text-sm tracking-tight">Astalink</span>
            <span className="text-sidebar-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {[
              { href: "/#fitur", label: "Fitur" },
              { href: "/#statistik", label: "Statistik" },
              { href: "/pricing", label: "Harga", active: true },
              { href: "/#mulai", label: "Mulai" },
            ].map(({ href, label, active }) => (
              <Link
                key={href}
                href={href}
                className={`px-3.5 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-1">
            <Link
              href="/login"
              className="hidden sm:block px-3.5 py-1.5 rounded-full text-sm font-medium text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors duration-150"
            >
              Masuk
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
        <div className="pointer-events-none absolute -top-24 left-1/4 w-[700px] h-[500px] rounded-full bg-chart-2/[0.07] blur-[130px]" />
        <div className="pointer-events-none absolute top-32 right-8 w-[350px] h-[350px] rounded-full bg-chart-2/[0.05] blur-[100px]" />

        <div className="relative mx-auto max-w-5xl text-center">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-chart-2/30 bg-chart-2/[0.07] text-chart-2 text-[11px] font-semibold uppercase tracking-[0.15em] mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-chart-2 animate-pulse" />
            Transparan · Tanpa Kontrak · Batalkan Kapan Saja
          </div>

          <h1 className="font-heading text-[2.6rem] md:text-[3.4rem] lg:text-[3.8rem] font-bold leading-[1.07] tracking-tight mb-6">
            <span className="block bg-clip-text text-transparent pb-2" style={{
              backgroundImage: "linear-gradient(130deg, oklch(0.723 0.219 149.579) 0%, oklch(0.871 0.15 154.449) 100%)",
            }}>
              Harga yang adil untuk
            </span>
            <span className="block">investasi yang lebih cerdas.</span>
          </h1>

          <p className="text-muted-foreground text-base md:text-[1.0625rem] leading-relaxed mb-10 max-w-[600px] mx-auto">
            Pilih paket yang cocok dengan kebutuhan investasi Anda. Semua paket termasuk verifikasi OJK otomatis
            dan kontrol penuh dengan konfirmasi PIN sebelum transaksi.
          </p>
        </div>
      </section>

      {/* ─── Trust Indicators ─── */}
      <section className="border-y border-border py-6 px-6">
        <div className="mx-auto max-w-7xl flex flex-wrap items-center justify-center gap-8 md:gap-12">
          {TRUST_INDICATORS.map(({ label, icon: Icon }) => (
            <div key={label} className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="w-7 h-7 rounded-lg bg-muted border border-border flex items-center justify-center">
                <Icon className="w-4 h-4" />
              </div>
              <span className="font-medium text-foreground">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Pricing Cards ─── */}
      <section id="pricing" className="relative py-20 px-6 overflow-hidden scroll-mt-24">
        <div className="absolute inset-0 bg-grid-pattern opacity-25" />
        <div className="relative mx-auto max-w-7xl z-10">
          <PricingCards />
        </div>
      </section>

      {/* ─── Detailed Comparison ─── */}
      <section className="relative py-20 px-6 overflow-hidden scroll-mt-24 border-y border-border">
        <div className="absolute inset-0 bg-grid-pattern opacity-20" />
        <div className="relative mx-auto max-w-7xl z-10">
          <div className="text-center mb-16">
            <p className="text-muted-foreground/50 text-[11px] font-mono uppercase tracking-[0.2em] mb-4">
              Perbandingan Detail
            </p>
            <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              Fitur lengkap tiap paket
            </h2>
            <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto leading-relaxed">
              Bandingkan fitur secara detail untuk menemukan paket terbaik bagi Anda.
            </p>
          </div>

          <Table>
            <TableHeader className="sticky top-0 z-10 bg-background/95 backdrop-blur">
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  Fitur
                </TableHead>
                {PRICING_TIER_NAMES.map((name) => (
                  <TableHead key={name} className="text-center">
                    <span className="text-[10px] font-bold font-mono uppercase tracking-wider text-foreground">
                      {name}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {COMPARISON_FEATURES.map(({ category, features }) => (
                <Fragment key={category}>
                  <TableRow className="hover:bg-transparent">
                    <TableCell
                      colSpan={4}
                      className="bg-muted/50 py-3 font-medium text-foreground text-sm uppercase tracking-wider whitespace-normal"
                    >
                      {category}
                    </TableCell>
                  </TableRow>
                  {features.map(({ key, label, tiers }) => (
                    <TableRow key={key}>
                      <TableCell className="py-4 text-sm text-foreground whitespace-normal">{label}</TableCell>
                      {tiers.map((included, i) => (
                        <TableCell key={i} className="text-center">
                          <div className="flex items-center justify-center">
                            {included ? (
                              <CheckIcon className="w-5 h-5 text-chart-2" />
                            ) : (
                              <XIcon className="w-5 h-5 text-muted-foreground/30" />
                            )}
                          </div>
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section className="relative py-20 px-6 overflow-hidden scroll-mt-24">
        <div className="absolute inset-0 bg-grid-pattern opacity-20" />
        <div className="relative mx-auto max-w-3xl z-10">
          <div className="text-center mb-16">
            <p className="text-muted-foreground/50 text-[11px] font-mono uppercase tracking-[0.2em] mb-4">
              Pertanyaan Umum
            </p>
            <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              Semua yang perlu Anda ketahui
            </h2>
          </div>

          <Accordion multiple className="space-y-4">
            {FAQ.map(({ q, a }, i) => (
              <AccordionItem
                key={i}
                value={i}
                className="bg-card border border-border rounded-xl overflow-hidden px-6 not-last:border-b"
              >
                <AccordionTrigger className="py-6 text-sm font-medium text-foreground hover:no-underline [&_svg]:size-5">
                  {q}
                </AccordionTrigger>
                <AccordionContent className="text-muted-foreground text-sm leading-relaxed border-t border-border">
                  <div className="pt-4">{a}</div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="relative py-28 px-6 text-center overflow-hidden border-t border-border scroll-mt-24">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_55%_at_50%_50%,oklch(0.723_0.219_149.579/0.07)_0%,transparent_100%)]" />
        <div className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-20" />

        <div className="relative max-w-lg mx-auto z-10">
          <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-5">
            Siap memulai investasi lebih cerdas?
          </h2>
          <p className="text-muted-foreground text-base mb-10 leading-relaxed">
            Gabung ribuan investor Indonesia yang sudah menggunakan AstaLink untuk analisis portofolio berbasis AI.
            Mulai gratis, upgrade kapan saja.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center gap-2.5 px-10 py-4 rounded-full bg-primary text-primary-foreground font-semibold text-base hover:bg-primary/90 transition-all duration-300"
            >
              Mulai Gratis Sekarang
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center justify-center px-10 py-4 rounded-full border border-border bg-secondary text-foreground font-semibold text-base hover:bg-accent hover:border-foreground/20 transition-all duration-200"
            >
              Sudah Punya Akun? Masuk
            </Link>
          </div>
          <p className="text-muted-foreground/60 text-xs mt-6 font-mono tracking-wide">
            Teregulasi OJK · Data Terenkripsi · Tidak Ada Iklan · Batalkan Kapan Saja
          </p>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-sidebar-border bg-sidebar">
        <div className="mx-auto max-w-6xl px-6 py-14 grid gap-10 md:grid-cols-[1.6fr_1fr_1fr]">
          <div className="space-y-4 max-w-xs">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 flex items-center justify-center">
                <Image src="/astalink.png" alt="Astalink" width={28} height={28} className="w-7 h-7 object-contain" />
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

          <div>
            <p className="text-sidebar-foreground/40 text-[10px] font-black font-mono uppercase tracking-[0.18em] mb-4">
              Produk
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/#fitur" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Fitur</Link></li>
              <li><Link href="/pricing" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Harga</Link></li>
              <li><Link href="/dashboard" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Dashboard</Link></li>
              <li><Link href="/chatbot" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Chatbot AI</Link></li>
              <li><Link href="/news" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Berita Pasar</Link></li>
              <li><Link href="/legal-docs" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Dokumen Legal</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-sidebar-foreground/40 text-[10px] font-black font-mono uppercase tracking-[0.18em] mb-4">
              Perusahaan
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/about" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Tentang Kami</Link></li>
              <li><Link href="/blog" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Blog</Link></li>
              <li><Link href="/careers" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Karir</Link></li>
              <li><Link href="/contact" className="text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors">Kontak</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-sidebar-border">
          <div className="mx-auto max-w-6xl px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-3">
            <p className="text-sidebar-foreground/40 text-xs">
              © 2026 Astalink AI. Digdaya × Hackathon 2026.
            </p>
            <div className="flex items-center gap-6 text-xs text-sidebar-foreground/40">
              <Link href="/privacy" className="hover:text-sidebar-foreground transition-colors">Kebijakan Privasi</Link>
              <Link href="/terms" className="hover:text-sidebar-foreground transition-colors">Ketentuan Layanan</Link>
              <Link href="/compliance" className="hover:text-sidebar-foreground transition-colors">Kepatuhan</Link>
            </div>
            <p className="text-sidebar-foreground/35 text-[10px] leading-relaxed text-center md:text-right max-w-md">
              Investasi saham mengandung risiko. Kinerja masa lalu tidak menjamin hasil di masa depan.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}