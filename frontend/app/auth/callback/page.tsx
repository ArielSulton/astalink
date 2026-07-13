"use client";
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Only allow same-origin relative paths as a redirect target. Reject
    // protocol-relative ("//evil.com"), backslash tricks, and any value
    // carrying a scheme (":" blocks javascript:/data:) to prevent open redirects.
    const rawNext = searchParams.get("next") ?? "/dashboard";
    const next =
      rawNext.startsWith("/") &&
      !rawNext.startsWith("//") &&
      !rawNext.startsWith("/\\") &&
      !rawNext.includes(":")
        ? rawNext
        : "/dashboard";

    // The client's default flowType is "pkce", under which the SDK's own
    // detectSessionInUrl only ever looks for a ?code= param — it silently
    // ignores #access_token= hash fragments (a known supabase-js gap:
    // github.com/supabase/supabase-js/issues/931). Admin-API-generated
    // links (signup confirm, password reset) deliver via that hash
    // fragment, never a code, so the tokens must be parsed and applied
    // by hand here instead of relying on auto-detection.
    const hashParams = new URLSearchParams(window.location.hash.slice(1));
    const accessToken = hashParams.get("access_token");
    const refreshToken = hashParams.get("refresh_token");

    if (!accessToken || !refreshToken) {
      router.replace("/login?error=auth_callback_failed");
      return;
    }

    const supabase = createClient();
    supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken })
      .then(({ error }) => {
        router.replace(error ? "/login?error=auth_callback_failed" : next);
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
