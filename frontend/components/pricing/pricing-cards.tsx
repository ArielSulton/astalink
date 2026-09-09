import Link from "next/link";
import { Check as CheckIcon, X as XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type Feature = { name: string; included: boolean };

type Tier = {
  eyebrow: string;
  name?: string;
  quota?: string;
  price: string;
  priceSuffix?: string;
  features: readonly Feature[];
  cta: string;
  ctaVariant: "outline" | "default" | "secondary";
  ctaHref: string;
  popular?: boolean;
  note?: string;
};

const PRICING_TIERS: readonly Tier[] = [
  {
    eyebrow: "Basic",
    quota: "20 chat ringan/bulan",
    price: "Gratis",
    features: [
      { name: "Chat tanya-jawab literasi keuangan via WhatsApp & Web", included: true },
      { name: "Demo portofolio sandbox dengan data contoh", included: true },
      { name: "Analisis alokasi modal personal (upgrade ke Pro)", included: false },
      { name: "Audit trail dan persetujuan PIN", included: false },
    ],
    cta: "Coba Gratis",
    ctaVariant: "outline",
    ctaHref: "/signup",
  },
  {
    eyebrow: "Pro",
    quota: "100 kredit chat/bulan",
    price: "Rp 99.000",
    priceSuffix: "/ bulan",
    features: [
      { name: "Konsultasi AI-CIO 24/7 via WhatsApp & Web", included: true },
      { name: "Analisis alokasi modal: tunai, saham IDX, atau bisnis sendiri", included: true },
      { name: "Cek kepatuhan OJK otomatis, tersitasi", included: true },
      { name: "Portofolio sandbox, mencoba tanpa risiko nyata", included: true },
      { name: "Audit trail & persetujuan PIN di setiap rekomendasi", included: true },
      { name: "Dashboard lengkap: holdings, approvals, transaksi, & berita", included: true },
    ],
    cta: "Mulai dari Rp99.000/bulan",
    ctaVariant: "default",
    ctaHref: "/signup",
    popular: true,
  },
  {
    eyebrow: "Komunitas & Partner",
    price: "Rp 1 Jt",
    priceSuffix: "base + Rp 28rb/anggota",
    features: [
      { name: "Semua fitur Pro, ditambah:", included: true },
      { name: "Akses REST API untuk integrasi sistem partner", included: true },
      { name: "White-label (branding sendiri)", included: true },
      { name: "Manajemen multi sub-akun anggota", included: true },
      { name: "Laporan agregat & dedicated account manager", included: true },
    ],
    cta: "Ajukan Kemitraan",
    ctaVariant: "outline",
    ctaHref: "/signup?partner=true",
    note: "Hingga 500 anggota per komunitas",
  },
] as const;

export function PricingCards() {
  return (
    <div className="grid grid-cols-1 gap-7 md:grid-cols-3 md:items-stretch lg:gap-6">
      {PRICING_TIERS.map((tier) => (
        <div key={tier.eyebrow} className={`relative ${tier.popular ? "z-10" : ""}`}>
          {tier.popular && (
            <Badge className="absolute -top-3 left-1/2 z-20 -translate-x-1/2 rounded-full bg-chart-2 px-3 py-1 text-xs font-semibold text-chart-2-foreground shadow-sm">
              Direkomendasikan
            </Badge>
          )}

          <Card
            className={`flex h-full flex-col rounded-2xl border bg-card shadow-[0_16px_38px_-28px_rgba(0,0,0,0.55)] transition-shadow hover:shadow-lg ${
              tier.popular ? "border-2 border-chart-2 ring-1 ring-chart-2/25" : "border-border"
            }`}
          >
            <CardContent className="flex h-full flex-col p-7 lg:p-8">
              <div className="mb-7 flex items-start justify-between gap-3">
                <div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">{tier.eyebrow}</p>
                  {tier.name && <h3 className="font-heading text-3xl font-bold tracking-tight text-foreground">{tier.name}</h3>}
                </div>
                {tier.quota && <p className="pt-0.5 text-right text-xs font-medium text-muted-foreground">{tier.quota}</p>}
              </div>

              <div className="mb-7 flex flex-wrap items-baseline gap-x-1 gap-y-0.5">
                <span className="font-heading text-3xl font-bold tracking-tight text-foreground">{tier.price}</span>
                {tier.priceSuffix && <span className="text-base font-semibold text-muted-foreground">{tier.priceSuffix}</span>}
              </div>

              <ul className="flex-1 space-y-3.5">
                {tier.features.map((feature) => (
                  <li key={feature.name} className="flex items-start gap-2.5">
                    {feature.included ? (
                      <CheckIcon className="mt-0.5 size-4 shrink-0 text-chart-2" aria-hidden="true" />
                    ) : (
                      <XIcon className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
                    )}
                    <span className="text-sm leading-[1.25] text-muted-foreground">{feature.name}</span>
                  </li>
                ))}
              </ul>

              {tier.note && <p className="mt-7 text-center text-xs text-muted-foreground">{tier.note}</p>}
              <Button
                className={`mt-7 w-full ${tier.popular ? "bg-chart-2 text-chart-2-foreground hover:bg-chart-2/90" : ""}`}
                variant={tier.ctaVariant}
                size="lg"
                render={<Link href={tier.ctaHref} />}
              >
                {tier.cta}
              </Button>
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
}
