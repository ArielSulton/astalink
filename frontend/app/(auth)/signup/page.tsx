import Link from "next/link";
import { SignupForm } from "@/components/auth/signup-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SignupPage() {
  return (
    <div className="relative min-h-screen bg-background bg-grid-pattern flex items-center justify-center p-4 overflow-hidden">
      {/* Radial glow backdrop */}
      <div className="absolute top-[35%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[420px] h-[420px] rounded-full bg-[radial-gradient(circle,oklch(0.538_0.243_264/0.10)_0%,transparent_70%)] pointer-events-none filter blur-2xl" />

      <Card className="w-full max-w-md bg-glass border border-border shadow-[0_24px_60px_rgba(0,0,0,0.5)] relative z-10 backdrop-blur-xl rounded-2xl overflow-hidden">
        <CardHeader className="space-y-1 text-center pt-8 pb-4">
          <div className="flex justify-center items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/25 flex items-center justify-center">
              <span className="text-primary text-[11px] font-black font-mono">A</span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-foreground font-bold text-base tracking-tight">Astalink</span>
              <span className="text-primary text-[9px] font-mono font-black uppercase tracking-widest">AI</span>
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-foreground">Create an account</CardTitle>
          <CardDescription className="text-muted-foreground text-sm">
            Enter your email and password to get started
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 px-8 pb-8">
          <SignupForm />
          <p className="text-center text-sm text-muted-foreground mt-4">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:text-primary/80 hover:underline font-semibold transition-colors">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
