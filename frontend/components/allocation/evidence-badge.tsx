import { cn } from "@/lib/utils";
import type { EvidenceTag } from "@/lib/api-client";

// Missing data must be as visible as present data: UNKNOWN gets the same
// visual weight as the filled tags, and VERIFIED must never look like CLAIMED.
const STYLES: Record<EvidenceTag, string> = {
  verified: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  claimed: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  estimated: "text-sky-400 bg-sky-500/10 border-sky-500/30",
  unknown: "text-rose-400 bg-rose-500/10 border-rose-500/30 border-dashed",
};

const LABELS: Record<EvidenceTag, string> = {
  verified: "VERIFIED",
  claimed: "CLAIMED",
  estimated: "ESTIMATED",
  unknown: "UNKNOWN",
};

export function EvidenceBadge({ tag, className }: { tag: EvidenceTag; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-[9px] font-bold font-mono tracking-wider border",
        STYLES[tag],
        className,
      )}
      title={
        tag === "verified" ? "Didukung dokumen (mutasi rekening, laporan, kontrak)"
        : tag === "claimed" ? "Hanya klaim pemilik bisnis — bobot skoring diturunkan"
        : tag === "estimated" ? "Diturunkan / diestimasi"
        : "Tidak ada data — tidak pernah diisi default"
      }
    >
      {LABELS[tag]}
    </span>
  );
}
