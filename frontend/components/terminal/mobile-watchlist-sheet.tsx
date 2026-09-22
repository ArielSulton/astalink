"use client";

import { List } from "lucide-react";
import { useState } from "react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { TickerChartData } from "@/lib/api-client";

import { WatchlistSidebar } from "./watchlist-sidebar";

type MobileWatchlistSheetProps = {
  watchlist: TickerChartData[];
  selectedTicker: string;
  onSelect: (ticker: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  loading: boolean;
};

export function MobileWatchlistSheet({
  watchlist,
  selectedTicker,
  onSelect,
  collapsed,
  onToggle,
  loading,
}: MobileWatchlistSheetProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-border bg-card/40 p-3 lg:hidden">
      <button
        type="button"
        aria-label="Buka daftar saham"
        onClick={() => setOpen(true)}
        className="inline-flex min-h-11 w-full items-center justify-between rounded-lg border border-border bg-secondary px-3 text-sm font-semibold text-foreground"
      >
        <span className="flex items-center gap-2">
          <List className="size-4" />
          Daftar saham
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {selectedTicker.replace(".JK", "")}
        </span>
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="bottom"
          className="max-h-[85svh] overflow-hidden p-0"
        >
          <SheetHeader>
            <SheetTitle>Daftar saham</SheetTitle>
            <SheetDescription>
              Pilih saham yang ingin dilihat pada grafik.
            </SheetDescription>
          </SheetHeader>
          <div className="max-h-[70svh] overflow-y-auto [&>aside]:min-h-[24rem] [&>aside]:w-full [&>aside]:border-r-0">
            <WatchlistSidebar
              watchlist={watchlist}
              selectedTicker={selectedTicker}
              onSelect={(ticker) => {
                onSelect(ticker);
                setOpen(false);
              }}
              collapsed={collapsed}
              onToggle={onToggle}
              loading={loading}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
