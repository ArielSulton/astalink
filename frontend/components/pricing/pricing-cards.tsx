"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { ArrowRight, Brain, Crown, TrendingUp, Check as CheckIcon, X as XIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";

type Feature = { name: string; included: boolean };

type Tier = {
  name: string;
  description: string;
  monthlyPrice: number | null;
  accent: string;
  iconBg: string;
  icon: typeof Brain;
  features: readonly Feature[];
  cta: string;
  ctaVariant: "outline" | "default" | "secondary";
  ctaHref: string;
  popular: boolean;
};

const PRICING_TIERS: readonly Tier[] = [
  {
    name: "Gratis",
    description: "Untuk pemula yang ingin mencoba analisis AI",
    monthlyPrice: 0,
    accent: "text-muted-foreground",
    iconBg: "bg-muted border-border",
    icon: Brain,
    features: [
      { name: "Laporan alokasi 1/bln", included: true },
      { name: "Chat AI 10 pesan/hari", included: true },
      { name: "Watchlist 3 saham", included: true },
      { name: "Verifikasi OJK", included: true },
      { name: "Analisis fundamental", included: false },
      { name: "Backtesting", included: false },
      { name: "Channel Web + WA terbatas", included: true },
      { name: "Ekspor PDF/Excel", included: false },
      { name: "Seats: 1", included: true },
      { name: "API access", included: false },
      { name: "Deployment: Cloud shared", included: true },
      { name: "Fine-tuning model", included: false },
      { name: "Support: Community/email", included: true },
    ],
    cta: "Mulai Gratis",
    ctaVariant: "outline",
    ctaHref: "/signup",
    popular: false,
  },
  {
    name: "Pro",
    description: "Untuk investor aktif yang butuh analisis lengkap",
    monthlyPrice: 99000,
    accent: "text-chart-2",
    iconBg: "bg-chart-2/10 border-chart-2/30",
    icon: TrendingUp,
    features: [
      { name: "Laporan alokasi ~30/bln (fair-use)", included: true },
      { name: "Chat AI tak terbatas (fair-use)", included: true },
      { name: "Watchlist tak terbatas", included: true },
      { name: "Verifikasi OJK", included: true },
      { name: "Analisis fundamental", included: true },
      { name: "Backtesting 5 tahun", included: true },
      { name: "Channel Web + WA penuh", included: true },
      { name: "Ekspor PDF/Excel", included: true },
      { name: "Seats: 1", included: true },
      { name: "API: 1.000 req/bln", included: true },
      { name: "Deployment: Cloud shared", included: true },
      { name: "Fine-tuning model", included: false },
      { name: "Support: Prioritas 24 jam", included: true },
    ],
    cta: "Langganan Sekarang",
    ctaVariant: "default",
    ctaHref: "/signup",
    popular: true,
  },
  {
    name: "Enterprise",
    description: "Untuk tim, manajer dana, & institusi",
    monthlyPrice: 15000000,
    accent: "text-primary",
    iconBg: "bg-primary/10 border-primary/30",
    icon: Crown,
    features: [
      { name: "Laporan alokasi tak terbatas", included: true },
      { name: "Chat AI tak terbatas + prioritas antrian", included: true },
      { name: "Watchlist tak terbatas", included: true },
      { name: "Verifikasi OJK", included: true },
      { name: "Analisis fundamental", included: true },
      { name: "Backtesting horizon custom", included: true },
      { name: "Channel Web + WA + webhook/integrasi broker", included: true },
      { name: "Ekspor PDF/Excel + white-label", included: true },
      { name: "Seats: 5+", included: true },
      { name: "API: tak terbatas/negotiable", included: true },
      { name: "Deployment: Cloud/on-premise", included: true },
      { name: "Fine-tuning model", included: true },
      { name: "Support: Dedicated account manager SLA 99.9%", included: true },
    ],
    cta: "Hubungi Penjualan",
    ctaVariant: "secondary",
    ctaHref: "/signup?enterprise=true",
    popular: false,
  },
] as const;

const ANNUAL_DISCOUNT = 0.2;

function formatRupiah(amount: number) {
  return `Rp ${Math.round(amount).toLocaleString("id-ID")}`;
}

export function PricingCards() {
  const [annual, setAnnual] = useState(false);
  const switchId = useId();

  return (
    <div>
      <div className="flex items-center justify-center gap-3 mb-14">
        <label htmlFor={switchId} className="text-sm font-medium text-foreground cursor-pointer">
          Bulanan
        </label>
        <Switch id={switchId} checked={annual} onCheckedChange={setAnnual} />
        <label htmlFor={switchId} className="text-sm font-medium text-muted-foreground cursor-pointer">
          Tahunan
        </label>
        <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
          Hemat {ANNUAL_DISCOUNT * 100}%
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-6 items-start">
        {PRICING_TIERS.map((tier) => {
          const Icon = tier.icon;
          const effectiveMonthly =
            tier.monthlyPrice === null ? null : annual ? tier.monthlyPrice * (1 - ANNUAL_DISCOUNT) : tier.monthlyPrice;

          return (
            <div key={tier.name} className={`relative ${tier.popular ? "z-10" : ""}`}>
              {tier.popular && (
                <div className="absolute top-1 left-1/2 -translate-x-1/2 z-20">
                  <Badge className="bg-chart-2 text-chart-2-foreground text-xs px-2.5 py-1 rounded-full font-medium">
                    Paling Populer
                  </Badge>
                </div>
              )}

              <Card
                className={`relative flex flex-col transition-all duration-300 ${
                  tier.popular
                    ? "ring-2 ring-chart-2/50 shadow-[0_20px_60px_-20px_rgba(10,14,12,0.25)] scale-[1.02]"
                    : "hover:ring-foreground/15 hover:shadow-lg"
                }`}
              >
                <CardHeader className="pb-4">
                  <div className={`w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 mb-4 ${tier.iconBg}`}>
                    <Icon className={`w-6 h-6 ${tier.accent}`} />
                  </div>
                  <CardTitle className="text-xl">{tier.name}</CardTitle>
                  <CardDescription>{tier.description}</CardDescription>
                </CardHeader>

                <CardContent className="flex-1 flex flex-col space-y-6">
                  <div className="border-t border-border pt-6">
                    <div className="flex items-baseline gap-1 mb-2">
                      <span className="font-heading text-4xl font-bold text-foreground">
                        {effectiveMonthly === null ? "Custom" : formatRupiah(effectiveMonthly)}
                      </span>
                      {effectiveMonthly !== null && (
                        <span className="text-muted-foreground text-sm font-mono">/bulan</span>
                      )}
                    </div>
                    {tier.name === "Enterprise" && (
                      <p className="text-muted-foreground text-sm">Hubungi kami untuk penawaran custom</p>
                    )}
                    {tier.name === "Pro" && annual && (
                      <p className="text-muted-foreground text-sm">
                        Ditagih {formatRupiah(tier.monthlyPrice! * 12 * (1 - ANNUAL_DISCOUNT))}/tahun
                      </p>
                    )}
                  </div>

                  <ul className="space-y-3 flex-1">
                    {tier.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-3">
                        {feature.included ? (
                          <CheckIcon className="w-5 h-5 text-chart-2 shrink-0 mt-0.5" />
                        ) : (
                          <XIcon className="w-5 h-5 text-muted-foreground/30 shrink-0 mt-0.5" />
                        )}
                        <span className={`text-sm ${feature.included ? "text-foreground" : "text-muted-foreground/60 line-through"}`}>
                          {feature.name}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <Button className="w-full" variant={tier.ctaVariant} size="lg" render={<Link href={tier.ctaHref} />}>
                    {tier.cta}
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </CardContent>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
