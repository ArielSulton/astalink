"use client";

import { SearchX } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import {
  DEFAULT_FILTERS,
  filterTransactions,
  hasActiveFilters,
  type TransactionFilters,
} from "@/lib/transactions/filter";
import { clampPage, paginate, type PageSize } from "@/lib/transactions/paginate";
import {
  DEFAULT_SORT,
  sortTransactions,
  toggleSort,
  type SortKey,
} from "@/lib/transactions/sort";
import { summarize } from "@/lib/transactions/summary";
import type { TransactionItem } from "@/lib/transactions/types";

import { TransactionPagination } from "./transaction-pagination";
import { TransactionSummaryCards } from "./transaction-summary";
import { TransactionToolbar } from "./transaction-toolbar";
import { TransactionView } from "./transaction-view";

export function TransactionExplorer({ items }: { items: TransactionItem[] }) {
  const [filters, setFilters] = useState<TransactionFilters>(DEFAULT_FILTERS);
  const [sort, setSort] = useState(DEFAULT_SORT);
  const [pageSize, setPageSize] = useState<PageSize>(25);
  const [page, setPage] = useState(1);

  const matched = useMemo(() => filterTransactions(items, filters), [items, filters]);
  const ordered = useMemo(() => sortTransactions(matched, sort), [matched, sort]);

  // Filtering can strand the viewer past the end of a now-shorter list.
  const safePage = clampPage(page, ordered.length, pageSize);
  const visible = paginate(ordered, safePage, pageSize);
  const summary = useMemo(() => summarize(matched), [matched]);
  const filtered = hasActiveFilters(filters);

  const applyFilters = (next: TransactionFilters) => {
    setFilters(next);
    setPage(1);
  };

  const resizePage = (next: PageSize) => {
    setPageSize(next);
    setPage(1);
  };

  const reorder = (key: SortKey) => {
    setSort((current) => toggleSort(current, key));
    setPage(1);
  };

  return (
    <div className="space-y-4">
      <TransactionSummaryCards summary={summary} filtered={filtered} />

      <TransactionToolbar filters={filters} onFiltersChange={applyFilters} />

      {ordered.length === 0 ? (
        <EmptyState icon={SearchX} title="Tidak Ada Hasil">
          <p>
            Tidak ada transaksi yang cocok dengan pencarian atau filter yang aktif.
          </p>
          <button
            type="button"
            onClick={() => applyFilters(DEFAULT_FILTERS)}
            className="mt-4 rounded-lg border border-border px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            Hapus semua filter
          </button>
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-xl bg-card ring-1 ring-foreground/10">
          <TransactionView items={visible} sort={sort} onSortChange={reorder} />
          <TransactionPagination
            page={safePage}
            pageSize={pageSize}
            total={ordered.length}
            onPageChange={setPage}
            onPageSizeChange={resizePage}
          />
        </div>
      )}
    </div>
  );
}
