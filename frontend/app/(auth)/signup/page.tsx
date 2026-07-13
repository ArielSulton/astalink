import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { SignupForm } from "@/components/auth/signup-form";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Daftar",
  description: "Mulai analisis portofolio IDX pertamamu dalam 2 menit bersama Astalink AI.",
};

export default function SignupPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6 md:max-w-4xl">
        <Card className="overflow-hidden p-0">
          <CardContent className="grid p-0 md:grid-cols-2">
            <div className="flex flex-col justify-center gap-6 p-6 md:p-8">
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex size-8 items-center justify-center">
                    <Image src="/astalink.png" alt="Astalink" width={32} height={32} className="size-8 object-contain" />
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-foreground font-bold tracking-tight">Astalink</span>
                    <span className="text-chart-2 text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
                  </div>
                </div>
                <h1 className="text-2xl font-bold">Create your account</h1>
                <p className="text-sm text-balance text-muted-foreground">
                  Mulai analisis portofolio IDX pertamamu dalam 2 menit
                </p>
              </div>
              <SignupForm />
              <p className="text-center text-sm text-muted-foreground">
                Sudah punya akun?{" "}
                <Link href="/login" className="underline underline-offset-4 hover:text-foreground">
                  Sign in
                </Link>
              </p>
            </div>

            {/* Brand panel */}
            <div className="relative hidden flex-col justify-between overflow-hidden border-l border-border bg-sidebar p-8 md:flex">
              <div className="pointer-events-none absolute inset-0 bg-grid-pattern" />
              <div className="pointer-events-none absolute -bottom-20 -right-20 size-64 rounded-full bg-chart-2/10 blur-[80px]" />
              <p className="relative text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                Astalink AI Console
              </p>
              <div className="relative space-y-3">
                <p className="font-heading text-2xl font-bold leading-snug text-foreground">
                  Tiga lapisan yang
                  <br />
                  <span className="text-chart-2">melindungi investasimu.</span>
                </p>
                <ul className="space-y-2 text-sm leading-relaxed text-muted-foreground">
                  <li>01 · Analisis multi-agen fundamental &amp; teknikal</li>
                  <li>02 · Verifikasi regulasi OJK otomatis</li>
                  <li>03 · Konfirmasi PIN di tanganmu</li>
                </ul>
              </div>
              <p className="relative text-[10px] font-mono tracking-wide text-muted-foreground/70">
                Gratis · Tanpa kartu kredit · Teregulasi OJK
              </p>
            </div>
          </CardContent>
        </Card>
        <p className="px-6 text-center text-xs text-balance text-muted-foreground">
          Dengan mendaftar, Anda menyetujui Ketentuan Layanan dan Kebijakan Privasi Astalink.
        </p>
      </div>
    </div>
  );
}
