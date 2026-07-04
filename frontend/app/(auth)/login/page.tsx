import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6 md:max-w-4xl">
        <Card className="overflow-hidden p-0">
          <CardContent className="grid p-0 md:grid-cols-2">
            <div className="flex flex-col justify-center gap-6 p-6 md:p-8">
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="mb-2 flex items-center gap-2">
                  <div className="flex size-8 items-center justify-center rounded-lg bg-chart-2/15 border border-chart-2/30">
                    <span className="text-chart-2 text-[11px] font-black font-mono">A</span>
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-foreground font-bold tracking-tight">Astalink</span>
                    <span className="text-chart-2 text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
                  </div>
                </div>
                <h1 className="text-2xl font-bold">Welcome back</h1>
                <p className="text-sm text-balance text-muted-foreground">
                  Masuk untuk mengelola portofolio IDX Anda
                </p>
              </div>
              <LoginForm />
              <p className="text-center text-sm text-muted-foreground">
                Belum punya akun?{" "}
                <Link href="/signup" className="underline underline-offset-4 hover:text-foreground">
                  Sign up
                </Link>
              </p>
            </div>

            {/* Brand panel */}
            <div className="relative hidden flex-col justify-between overflow-hidden border-l border-border bg-sidebar p-8 md:flex">
              <div className="pointer-events-none absolute inset-0 bg-grid-pattern" />
              <div className="pointer-events-none absolute -top-20 -right-20 size-64 rounded-full bg-chart-2/10 blur-[80px]" />
              <p className="relative text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
                Astalink AI Console
              </p>
              <div className="relative space-y-3">
                <p className="font-heading text-2xl font-bold leading-snug text-foreground">
                  AI yang menganalisis.
                  <br />
                  <span className="text-chart-2">Kamu yang memutuskan.</span>
                </p>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Multi-agen AI memindai pasar IDX dan memverifikasi kepatuhan OJK —
                  tidak ada transaksi tanpa konfirmasi PIN Anda.
                </p>
              </div>
              <p className="relative text-[10px] font-mono tracking-wide text-muted-foreground/70">
                Teregulasi OJK · Data Terenkripsi · Human-in-the-Loop
              </p>
            </div>
          </CardContent>
        </Card>
        <p className="px-6 text-center text-xs text-balance text-muted-foreground">
          Dengan masuk, Anda menyetujui Ketentuan Layanan dan Kebijakan Privasi Astalink.
        </p>
      </div>
    </div>
  );
}
