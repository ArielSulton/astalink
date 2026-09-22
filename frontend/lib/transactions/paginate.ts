export const PAGE_SIZES = [25, 50, 100] as const;

export type PageSize = (typeof PAGE_SIZES)[number];

/** An empty ledger still occupies one page, so the footer reads "1 dari 1". */
export function pageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function clampPage(page: number, total: number, pageSize: number): number {
  return Math.min(Math.max(1, page), pageCount(total, pageSize));
}

export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const safe = clampPage(page, items.length, pageSize);
  const start = (safe - 1) * pageSize;
  return items.slice(start, start + pageSize);
}
