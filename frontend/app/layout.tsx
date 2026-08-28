import type { Metadata } from "next";
import { Oxanium, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const oxanium = Oxanium({subsets:['latin'],variable:'--font-sans'});
// globals.css maps --font-mono to --font-geist-mono, but nothing loaded that
// variable — every "tabular numbers" price/percent in the UI was silently
// falling back to Oxanium instead of a real monospace face. JetBrains Mono
// keeps the terminal-technical character DESIGN.md documents for numerics.
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

const SITE_URL = "https://astalink.my.id";
const SITE_TITLE = "Astalink AI — Investasi IDX Berbasis AI";
const SITE_DESCRIPTION =
  "Platform investasi saham IDX dengan AI multi-agen, kepatuhan OJK otomatis, dan kontrol penuh di tangan kamu.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_TITLE,
    template: "%s — Astalink AI",
  },
  description: SITE_DESCRIPTION,
  icons: {
    icon: "/astalink.png",
  },
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: SITE_URL,
    siteName: "Astalink AI",
    locale: "id_ID",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" data-scroll-behavior="smooth" className={cn("font-sans dark", oxanium.variable, jetbrainsMono.variable)}>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
