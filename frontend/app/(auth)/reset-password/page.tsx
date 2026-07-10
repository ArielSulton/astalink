"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { Card, CardContent } from "@/components/ui/card";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [hasSession, setHasSession] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession()
      .then(({ data: { session } }) => {
        setHasSession(!!session);
        setChecking(false);
        if (!session) {
          router.replace("/forgot-password");
        }
      })
      .catch(() => {
        setHasSession(false);
        setChecking(false);
        router.replace("/forgot-password");
      });
  }, [router]);

  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <Card className="overflow-hidden p-0">
          <CardContent className="p-6 md:p-8">
            <div className="mb-6 flex flex-col items-center gap-2 text-center">
              <div className="mb-2 flex items-center gap-2">
                <div className="flex size-8 items-center justify-center rounded-lg bg-chart-2/15 border border-chart-2/30">
                  <span className="text-chart-2 text-[11px] font-black font-mono">A</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-foreground font-bold tracking-tight">Astalink</span>
                  <span className="text-chart-2 text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
                </div>
              </div>
              <h1 className="text-2xl font-bold">Buat password baru</h1>
              <p className="text-sm text-balance text-muted-foreground">
                Masukkan password baru untuk akun kamu
              </p>
            </div>
            {checking ? (
              <p className="text-center text-sm text-muted-foreground">Memuat…</p>
            ) : hasSession ? (
              <ResetPasswordForm />
            ) : (
              <p className="text-center text-sm text-muted-foreground">
                Link tidak valid atau sudah kedaluwarsa.{" "}
                <Link href="/forgot-password" className="underline underline-offset-4 hover:text-foreground">
                  Minta link baru
                </Link>
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
