"use client";
import { useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ExtendedPricePoint } from "@/lib/api-client";

interface SubplotTabsProps {
  data: ExtendedPricePoint[];
  indicators: string[];
  onToggleIndicator: (id: string) => void;
  onTogglePane: (pane: "volume" | "macd" | "rsi") => void;
  showVolume: boolean;
  showMacd: boolean;
  showRsi: boolean;
  height: number;
  onHeightChange: (h: number) => void;
}

const TOOLTIP_STYLE = {
  backgroundColor: "var(--chart-tooltip-bg)",
  border: "1px solid var(--chart-tooltip-border)",
  borderRadius: "6px",
  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
  padding: "8px 10px",
  fontSize: "11px",
  fontFamily: "var(--font-mono)",
  color: "var(--foreground)",
};

export function SubplotTabs({
  data, indicators, onToggleIndicator, onTogglePane,
  showVolume, showMacd, showRsi, height, onHeightChange,
}: SubplotTabsProps) {
  const [activeTab, setActiveTab] = useState<"main" | "indicators" | "settings">("main");

  const panes = [
    { id: "volume" as const, label: "Volume", enabled: showVolume },
    { id: "macd" as const, label: "MACD", enabled: showMacd },
    { id: "rsi" as const, label: "RSI", enabled: showRsi },
  ];

  const xKey = "date";

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border bg-card/40 px-2">
        {(["main", "indicators", "settings"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            type="button"
            className={`flex items-center gap-1.5 rounded-t-lg px-3 py-1.5 text-[11px] font-mono font-medium transition-colors ${
              activeTab === tab
                ? "text-foreground bg-card border-b-2 border-chart-2"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab === "main" && "Chart"}
            {tab === "indicators" && "Indikator"}
            {tab === "settings" && "Pengaturan"}
          </button>
        ))}
        <div className="flex-1" />
        {/* Height control */}
        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="icon" onClick={() => onHeightChange(Math.max(200, height - 50))} aria-label="Decrease height">
            <Minimize2 className="size-3.5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => onHeightChange(height + 50)} aria-label="Increase height">
            <Maximize2 className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* Tab panels */}
      <div className="flex-1 overflow-hidden">
        {activeTab === "main" && (
          <div className="p-2 space-y-2">
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
              <span>Pane aktif:</span>
              {panes.map((p) => (
                <button key={p.id} onClick={() => onTogglePane(p.id)} type="button"
                  className={`rounded border px-2 py-0.5 transition-colors ${
                    p.enabled
                      ? "border-chart-2/40 bg-chart-2/10 text-chart-2"
                      : "border-border text-muted-foreground hover:border-foreground/40"
                  }`}>
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
              <span>X-Key:</span>
              <code className="rounded bg-secondary px-1.5 py-0.5 text-foreground">{xKey}</code>
            </div>
          </div>
        )}

        {activeTab === "indicators" && (
          <div className="p-2 space-y-2">
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Overlay pada chart utama</p>
            <div className="flex flex-wrap gap-1">
              {indicators.map((id) => (
                <button key={id} onClick={() => onToggleIndicator(id)} type="button"
                  className="rounded border border-border bg-secondary/50 px-2 py-0.5 text-[10px] font-mono font-semibold text-muted-foreground hover:text-foreground transition-colors">
                  {id.toUpperCase()} <span className="ml-0.5 text-muted-foreground/50">×</span>
                </button>
              ))}
            </div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mt-2">Subplot pane</p>
            <div className="flex flex-wrap gap-1">
              {panes.map((p) => (
                <button key={p.id} onClick={() => onTogglePane(p.id)} type="button"
                  className={`rounded border px-2 py-0.5 text-[10px] font-mono font-medium transition-colors ${
                    p.enabled
                      ? "border-chart-2/40 bg-chart-2/10 text-chart-2"
                      : "border-border text-muted-foreground hover:border-foreground/40"
                  }`}>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="p-2 space-y-3">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-2">Tooltip Style</p>
              <pre className="rounded border border-border bg-secondary/50 p-2 text-[9px] font-mono text-muted-foreground overflow-auto max-h-40">
                {JSON.stringify(TOOLTIP_STYLE, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-2">Data Points</p>
              <p className="text-[11px] font-mono text-foreground">{data.length} candles</p>
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground mb-2">Chart Height</p>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="200"
                  max="800"
                  step="50"
                  value={height}
                  onChange={(e) => onHeightChange(Number(e.target.value))}
                  className="flex-1 accent-chart-2"
                />
                <span className="w-16 text-right text-[11px] font-mono tabular-nums text-foreground">{height}px</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}