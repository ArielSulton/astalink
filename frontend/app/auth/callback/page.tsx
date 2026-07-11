"use client";
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const next = searchParams.get("next") ?? "/dashboard";
    const supabase = createClient();

    supabase.auth.getSession()
      .then(({ data: { session } }) => {
        router.replace(session ? next : "/login?error=auth_callback_failed");
      })
      .catch(() => {
        router.replace("/login?error=auth_callback_failed");
      });
  }, [router, searchParams]);

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted">
      <p className="text-sm text-muted-foreground">Memproses...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <CallbackHandler />
    </Suspense>
  );
}
