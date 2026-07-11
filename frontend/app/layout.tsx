import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Oxanium } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const oxanium = Oxanium({subsets:['latin'],variable:'--font-sans'});
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
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
    <html lang="id" className={cn("font-sans dark", oxanium.variable, plusJakarta.variable)}>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
