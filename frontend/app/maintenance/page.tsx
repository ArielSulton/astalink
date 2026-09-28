import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Pemeliharaan Sistem",
  description: "Layanan AstaLink sedang dalam pemeliharaan.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function MaintenancePage() {
  return (
    <div className="relative min-h-svh overflow-hidden bg-[#0a0a0a] text-[#fafafa]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-20"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-chart-2/60 to-transparent"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-48 left-1/2 size-[34rem] -translate-x-1/2 rounded-full bg-chart-2/[0.055] blur-[120px]"
      />

      <div className="relative mx-auto flex min-h-svh w-full max-w-7xl flex-col px-6 py-7 sm:px-10 sm:py-9 lg:px-12">
        <header className="flex items-center gap-2.5" aria-label="AstaLink">
          <Image
            src="/logo_astalink.png"
            alt=""
            width={32}
            height={32}
            priority
            className="size-8 object-contain"
          />
          <div className="flex items-baseline gap-1.5">
            <span className="text-sm font-bold tracking-tight">AstaLink</span>
            <span className="font-mono text-[9px] font-extrabold uppercase tracking-[0.18em] text-chart-2">
              AI
            </span>
          </div>
        </header>

        <main className="flex flex-1 items-center py-16">
          <section className="w-full max-w-2xl" aria-labelledby="maintenance-title">
            <div
              role="status"
              className="mb-7 inline-flex items-center gap-2 rounded-md border border-chart-2/25 bg-chart-2/[0.07] px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-chart-2"
            >
              <span aria-hidden="true" className="size-1.5 rounded-full bg-chart-2" />
              Pemeliharaan sistem
            </div>

            <h1
              id="maintenance-title"
              className="max-w-xl text-balance text-4xl font-bold leading-[1.1] tracking-[-0.035em] sm:text-5xl lg:text-[3.5rem]"
            >
              AstaLink sedang dalam pemeliharaan.
            </h1>

            <p className="mt-6 max-w-xl text-pretty text-base leading-7 text-[#a1a1aa] sm:text-lg sm:leading-8">
              Akses ke layanan untuk sementara dinonaktifkan selama pemeliharaan
              sistem. Silakan kembali beberapa saat lagi.
            </p>

            <div className="mt-10">
              <a
                href="https://www.instagram.com/astalabs.id?stkn=MXVpeXJscDg0YzNjcg%3D%3D"
                className="inline-flex min-h-12 items-center justify-center rounded-lg bg-chart-2 px-6 text-sm font-bold text-[#07110b] shadow-[0_12px_32px_-12px_oklch(0.723_0.219_149.579/0.55)] transition-colors hover:bg-chart-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-chart-2 focus-visible:ring-offset-4 focus-visible:ring-offset-[#0a0a0a]"
              >
                AstaLabs.id
              </a>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/[0.08] pt-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#71717a]">
            AstaLink AI · Status layanan
          </p>
        </footer>
      </div>
    </div>
  );
}
