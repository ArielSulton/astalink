import { bareTicker } from "./filter";
import type { TransactionItem } from "./types";

export type SortKey =
  | "created_at"
  | "ticker"
  | "quantity"
  | "price"
  | "nominal"
  | "realized_pnl";

export type SortDirection = "asc" | "desc";

export interface TransactionSort {
  key: SortKey;
  direction: SortDirection;
}

export const DEFAULT_SORT: TransactionSort = { key: "created_at", direction: "desc" };

/** Rupiah actually moved by the order; unknown until the fill price is known. */
export function nominal(item: TransactionItem): number | null {
  return item.price != null ? item.quantity * item.price : null;
}

function numericValue(item: TransactionItem, key: SortKey): number | null {
  switch (key) {
    case "created_at":
      return new Date(item.created_at).getTime();
    case "quantity":
      return item.quantity;
    case "price":
      return item.price ?? null;
    case "nominal":
      return nominal(item);
    case "realized_pnl":
      return item.realized_pnl ?? null;
    default:
      return null;
  }
}

export function sortTransactions(
  items: TransactionItem[],
  sort: TransactionSort,
): TransactionItem[] {
  const factor = sort.direction === "asc" ? 1 : -1;

  return [...items].sort((a, b) => {
    if (sort.key === "ticker") {
      return bareTicker(a.ticker).localeCompare(bareTicker(b.ticker)) * factor;
    }

    const left = numericValue(a, sort.key);
    const right = numericValue(b, sort.key);

    // Blanks carry no ranking, so they sink to the bottom either way.
    if (left == null && right == null) return 0;
    if (left == null) return 1;
    if (right == null) return -1;

    return (left - right) * factor;
  });
}

/** Clicking the active column flips it; a new column opens on its biggest values. */
export function toggleSort(current: TransactionSort, key: SortKey): TransactionSort {
  if (current.key !== key) return { key, direction: "desc" };
  return { key, direction: current.direction === "asc" ? "desc" : "asc" };
}
