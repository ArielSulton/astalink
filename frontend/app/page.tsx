import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-8">Astalink Template</h1>
      <p className="text-muted-foreground mb-8">
        Next.js + FastAPI + LangGraph + Supabase
      </p>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          Login
        </Link>
        <Link
          href="/signup"
          className="px-4 py-2 rounded-md border border-input hover:bg-accent"
        >
          Sign Up
        </Link>
      </div>
    </main>
  );
}
