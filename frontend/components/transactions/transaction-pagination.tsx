"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { PAGE_SIZES, pageCount, type PageSize } from "@/lib/transactions/paginate";

interface TransactionPaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: PageSize) => void;
}

const STEP_CLASS =
  "inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function TransactionPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: TransactionPaginationProps) {
  const pages = pageCount(total, pageSize);
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  const range = total === 0 ? "0 dari 0" : `${first}–${last} dari ${total}`;

  return (
    <div className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="font-mono text-[11px] text-muted-foreground">
        Menampilkan {range} transaksi
      </p>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
          <span>Baris per halaman</span>
          <select
            value={pageSize}
            onChange={(event) => onPageSizeChange(Number(event.target.value) as PageSize)}
            className="rounded-lg border border-border bg-secondary/40 px-2 py-1 font-mono text-[11px] text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {PAGE_SIZES.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className={STEP_CLASS}
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft className="size-3" aria-hidden />
            Sebelumnya
          </button>
          <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
            {page} / {pages}
          </span>
          <button
            type="button"
            className={STEP_CLASS}
            disabled={page >= pages}
            onClick={() => onPageChange(page + 1)}
          >
            Berikutnya
            <ChevronRight className="size-3" aria-hidden />
          </button>
        </div>
      </div>
    </div>
  );
}
