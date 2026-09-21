import type { TransactionItem } from "./types";

export type SideFilter = "all" | "buy" | "sell";
export type StatusFilter = "all" | "filled" | "pending" | "failed";
export type RangeFilter = "all" | "7d" | "30d" | "90d";

export interface TransactionFilters {
  query: string;
  side: SideFilter;
  status: StatusFilter;
  range: RangeFilter;
}

export const DEFAULT_FILTERS: TransactionFilters = {
  query: "",
  side: "all",
  status: "all",
  range: "all",
};

const RANGE_DAYS: Record<Exclude<RangeFilter, "all">, number> = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
};

/** The ticker as traders say it: BBCA.JK is just BBCA. */
export function bareTicker(ticker: string): string {
  return ticker.replace(".JK", "");
}

function matchesQuery(item: TransactionItem, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return (
    bareTicker(item.ticker).toLowerCase().includes(needle) ||
    (item.broker_ref ?? "").toLowerCase().includes(needle)
  );
}

export function filterTransactions(
  items: TransactionItem[],
  filters: TransactionFilters,
  now: Date = new Date(),
): TransactionItem[] {
  const cutoff =
    filters.range === "all"
      ? null
      : now.getTime() - RANGE_DAYS[filters.range] * 24 * 60 * 60 * 1000;

  return items.filter((item) => {
    if (!matchesQuery(item, filters.query)) return false;
    if (filters.side !== "all" && item.side.toLowerCase() !== filters.side) return false;
    if (filters.status !== "all" && item.status.toLowerCase() !== filters.status) return false;
    if (cutoff != null && new Date(item.created_at).getTime() < cutoff) return false;
    return true;
  });
}

/** Drives the "Reset" affordance: only shown once the view is narrowed. */
export function hasActiveFilters(filters: TransactionFilters): boolean {
  return (
    filters.query.trim() !== "" ||
    filters.side !== "all" ||
    filters.status !== "all" ||
    filters.range !== "all"
  );
}
