import Image from "next/image";

export function PartnershipCredit() {
  return (
    <div className="border-t border-sidebar-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-3 px-6 py-7 text-center">
        <p className="text-[10px] font-mono font-semibold uppercase tracking-[0.18em] text-sidebar-foreground/40">
          Berkolaborasi dengan
        </p>
        <Image
          src="/aeterna-foundation.png"
          alt="Logo Aeterna Foundation"
          width={176}
          height={40}
          className="h-8 w-auto object-contain opacity-80 transition-opacity hover:opacity-100"
        />
        <span className="text-xs font-medium text-sidebar-foreground/65">
          Aeterna Foundation
        </span>
      </div>
    </div>
  );
}
