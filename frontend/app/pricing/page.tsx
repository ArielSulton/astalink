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

const PRICING_TIER_NAMES = ["Gratis", "Pro", "Partner"] as const;

const COMPARISON_FEATURES = [
  { category: "Akses & Analisis", features: [
    { key: "chat", label: "Chat literasi keuangan via WhatsApp & Web", tiers: [true, true, true] },
    { key: "allocation", label: "Analisis alokasi modal personal", tiers: [false, true, true] },
    { key: "legal", label: "Cek kepatuhan OJK otomatis, tersitasi", tiers: [false, true, true] },
    { key: "sandbox", label: "Portofolio sandbox", tiers: [true, true, true] },
  ]},
  { category: "Dashboard & Kontrol", features: [
    { key: "audit", label: "Audit trail & persetujuan PIN", tiers: [false, true, true] },
    { key: "dashboard", label: "Dashboard holdings, approvals, transaksi, & berita", tiers: [false, true, true] },
    { key: "credits", label: "Kredit chat lebih banyak", tiers: [false, true, true] },
  ]},
  { category: "Kemitraan", features: [
    { key: "api", label: "Akses REST API untuk integrasi partner", tiers: [false, false, true] },
    { key: "whiteLabel", label: "White-label (branding sendiri)", tiers: [false, false, true] },
    { key: "subAccounts", label: "Manajemen multi sub-akun anggota", tiers: [false, false, true] },
    { key: "aggregate", label: "Laporan agregat & account manager", tiers: [false, false, true] },
  ]},
] as const;

const FAQ = [
  {
    q: "Apa yang didapat dari paket Gratis?",
    a: "Paket Gratis mencakup 20 chat ringan per bulan untuk literasi keuangan via WhatsApp dan Web, serta demo portofolio sandbox dengan data contoh.",
  },
  {
    q: "Apa yang membedakan paket Pro?",
    a: "Pro menyediakan 100 kredit chat per bulan, analisis alokasi modal, cek kepatuhan OJK tersitasi, audit trail, persetujuan PIN, dan dashboard lengkap.",
  },
  {
    q: "Untuk siapa paket Komunitas & Partner?",
    a: "Paket ini ditujukan untuk komunitas atau partner yang memerlukan integrasi REST API, branding sendiri, dan pengelolaan sub-akun anggota.",
  },
  {
    q: "Berapa kapasitas paket Partner?",
    a: "Paket Partner mencakup biaya dasar Rp1 juta ditambah Rp28 ribu per anggota, hingga 500 anggota per komunitas.",
  },
  {
    q: "Apakah paket Partner mencakup semua fitur Pro?",
    a: "Ya. Paket Partner mencakup seluruh fitur Pro, lalu menambahkan kapabilitas integrasi dan pengelolaan komunitas.",
  },
] as const;

const TRUST_INDICATORS = [
  { label: "Cek Regulasi", icon: ShieldCheck },
  { label: "Kontrol PIN", icon: Lock },
  { label: "Portofolio Sandbox", icon: Zap },
  { label: "AI Multi-Agen", icon: Brain },
  { label: "Human-in-the-Loop", icon: Users },
  { label: "Harga Transparan", icon: CreditCard },
] as const;

export const metadata = {
  title: "Harga | AstaLink AI",
  description: "Pilih paket AstaLink untuk literasi keuangan, analisis alokasi modal, dan kebutuhan komunitas Anda.",
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
              Tiga tier, satu jalur
            </span>
            <span className="block">monetisasi yang jelas.</span>
          </h1>

          <p className="text-muted-foreground text-base md:text-[1.0625rem] leading-relaxed mb-10 max-w-[600px] mx-auto">
            Mulai dari literasi keuangan dasar, lanjutkan ke analisis alokasi modal, atau kelola kebutuhan komunitas
            dengan akses partner.
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
            Mulai dengan paket Gratis untuk mengenal AstaLink, atau pilih Pro untuk analisis dan kontrol yang lebih lengkap.
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
            WhatsApp & Web · Portofolio Sandbox · Audit Trail di Pro
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
              Platform analisis alokasi modal dengan AI multi-agen, cek regulasi berbasis dokumen,
              dan kontrol penuh di tanganmu.
            </p>
            <p className="text-sidebar-foreground/35 text-[10px] font-mono tracking-wide">
              Analisis AI · Cek Regulasi
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
