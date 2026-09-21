import { expect, test } from "vitest";

import { clampPage, pageCount, paginate } from "./paginate";

const rows = Array.from({ length: 57 }, (_, i) => i);

test("returns the slice belonging to the requested page", () => {
  expect(paginate(rows, 2, 25)).toEqual(rows.slice(25, 50));
});

test("returns a short final page rather than padding it", () => {
  expect(paginate(rows, 3, 25)).toHaveLength(7);
});

test("counts a partial page as a page of its own", () => {
  expect(pageCount(57, 25)).toBe(3);
});

test("keeps a single page for an empty ledger so the footer still reads 1 of 1", () => {
  expect(pageCount(0, 25)).toBe(1);
});

test("pulls the page back in range when filtering shrinks the list", () => {
  expect(clampPage(5, 57, 25)).toBe(3);
});

test("never drops below the first page", () => {
  expect(clampPage(0, 57, 25)).toBe(1);
});
