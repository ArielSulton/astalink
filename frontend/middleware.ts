import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const maintenanceMode = process.env.MAINTENANCE_MODE === "true";
  const pathname = request.nextUrl.pathname;

  if (maintenanceMode) {
    if (pathname === "/maintenance") {
      return NextResponse.next();
    }

    return NextResponse.redirect(new URL("/maintenance", request.url), 307);
  }

  if (pathname === "/maintenance") {
    return NextResponse.redirect(new URL("/", request.url), 307);
  }

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Redirect unauthenticated users away from protected routes
  const PROTECTED_PREFIXES = [
    "/dashboard",
    "/approvals",
    "/transactions",
    "/settings",
    "/portfolio",
    "/chatbot",
    "/legal-docs",
    "/news",
    "/allocation",
    "/business",
    "/recommendations",
  ];
  if (!user && PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    return NextResponse.redirect(redirectUrl);
  }

  // Redirect authenticated users away from auth pages
  if (
    user &&
    (pathname === "/login" || pathname === "/signup")
  ) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/dashboard";
    return NextResponse.redirect(redirectUrl);
  }

  return supabaseResponse;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
