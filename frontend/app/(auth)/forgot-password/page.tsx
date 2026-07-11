import Image from "next/image";
import Link from "next/link";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { Card, CardContent } from "@/components/ui/card";

export default function ForgotPasswordPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <Card className="overflow-hidden p-0">
          <CardContent className="p-6 md:p-8">
            <div className="mb-6 flex flex-col items-center gap-2 text-center">
              <div className="mb-2 flex items-center gap-2">
                <div className="flex size-8 items-center justify-center">
                  <Image src="/astalink.png" alt="Astalink" width={32} height={32} className="size-8 object-contain" />
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-foreground font-bold tracking-tight">Astalink</span>
                  <span className="text-chart-2 text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
                </div>
              </div>
              <h1 className="text-2xl font-bold">Lupa password?</h1>
              <p className="text-sm text-balance text-muted-foreground">
                Masukkan email kamu, kami kirim link untuk reset password
              </p>
            </div>
            <ForgotPasswordForm />
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Ingat password kamu?{" "}
              <Link href="/login" className="underline underline-offset-4 hover:text-foreground">
                Kembali ke login
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
