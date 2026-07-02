import type { Metadata } from "next";
import { Geist, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Astalink AI — Investasi IDX Berbasis AI",
  description:
    "Platform investasi saham IDX dengan AI multi-agen, kepatuhan OJK otomatis, dan kontrol penuh di tangan kamu.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={cn("font-sans dark", geist.variable, plusJakarta.variable)}>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
