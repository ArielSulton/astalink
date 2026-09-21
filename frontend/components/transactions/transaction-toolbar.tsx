"use client";

import { RotateCcw, Search } from "lucide-react";

import {
  DEFAULT_FILTERS,
  hasActiveFilters,
  type RangeFilter,
  type SideFilter,
  type StatusFilter,
  type TransactionFilters,
} from "@/lib/transactions/filter";
import { cn } from "@/lib/utils";

interface TransactionToolbarProps {
  filters: TransactionFilters;
  onFiltersChange: (filters: TransactionFilters) => void;
}

const SIDE_OPTIONS: { value: SideFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "buy", label: "Beli" },
  { value: "sell", label: "Jual" },
];

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "filled", label: "Berhasil" },
  { value: "pending", label: "Menunggu" },
  { value: "failed", label: "Gagal" },
];

const RANGE_OPTIONS: { value: RangeFilter; label: string }[] = [
  { value: "all", label: "Semua" },
  { value: "7d", label: "7 Hari" },
  { value: "30d", label: "30 Hari" },
  { value: "90d", label: "90 Hari" },
];

function ChipGroup<T extends string>({
  label,
  options,
  value,
  onSelect,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onSelect: (next: T) => void;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2">
      <span className="shrink-0 font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
        {label}
      </span>
      <div
        role="group"
        aria-label={label}
        className="flex items-center gap-1 overflow-x-auto rounded-lg border border-border bg-secondary/30 p-1"
      >
        {options.map((option) => {
          const active = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => onSelect(option.value)}
              className={cn(
                "shrink-0 rounded-md px-2.5 py-1 font-mono text-[11px] font-bold uppercase tracking-wider transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                active
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function TransactionToolbar({ filters, onFiltersChange }: TransactionToolbarProps) {
  const patch = (next: Partial<TransactionFilters>) =>
    onFiltersChange({ ...filters, ...next });

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card/40 p-3">
      <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary/40 px-3">
        <Search className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        <input
          type="search"
          role="searchbox"
          aria-label="Cari transaksi"
          value={filters.query}
          onChange={(event) => patch({ query: event.target.value })}
          placeholder="Cari ticker atau ref broker…"
          className="w-full bg-transparent py-2 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <ChipGroup
          label="Jenis"
          options={SIDE_OPTIONS}
          value={filters.side}
          onSelect={(side) => patch({ side })}
        />
        <ChipGroup
          label="Status"
          options={STATUS_OPTIONS}
          value={filters.status}
          onSelect={(status) => patch({ status })}
        />
        <ChipGroup
          label="Rentang Waktu"
          options={RANGE_OPTIONS}
          value={filters.range}
          onSelect={(range) => patch({ range })}
        />

        {hasActiveFilters(filters) && (
          <button
            type="button"
            onClick={() => onFiltersChange(DEFAULT_FILTERS)}
            className="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <RotateCcw className="size-3" aria-hidden />
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
