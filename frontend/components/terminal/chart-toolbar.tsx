"use client";
import { Activity, Cpu, LogIn, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuGroup,
} from "@/components/ui/dropdown-menu";
import { INDICATORS, type IndicatorId } from "@/lib/hooks/use-indicators";
import { type ChartType } from "@/lib/hooks/use-chart-type";
import { TIMEFRAMES, type Timeframe, type TimeframeConfig } from "@/lib/hooks/use-timeframe";
import { cn } from "@/lib/utils";

interface ChartToolbarProps {
  ticker: string;
  symLabel: string;
  timeframe: TimeframeConfig;
  onTimeframeChange: (v: Timeframe) => void;
  indicators: IndicatorId[];
  onToggleIndicator: (id: IndicatorId) => void;
  chartType: ChartType;
  onChartTypeChange: (ct: ChartType) => void;
  scale: "linear" | "log";
  onScaleChange: (s: "linear" | "log") => void;
  onExport: () => void;
}

const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: "candle", label: "Candle" },
  { value: "line", label: "Line" },
  { value: "area", label: "Area" },
  { value: "heikin-ashi", label: "Heikin Ashi" },
];

export function ChartToolbar({
  symLabel, timeframe, onTimeframeChange, indicators, onToggleIndicator,
  chartType, onChartTypeChange, scale, onScaleChange, onExport,
}: ChartToolbarProps) {
  const activeLabels = INDICATORS.filter((i) => indicators.includes(i.id));

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-card/40 px-4 py-2">
      {/* Ticker label */}
      <span className="rounded-lg border border-border bg-secondary px-2.5 py-1 font-mono text-xs font-bold uppercase tracking-wide text-foreground">
        {symLabel}
      </span>

      {/* Timeframe dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="outline" size="sm" className="h-8 gap-1.5 font-mono" />}
        >
          <Activity className="size-3.5" /> {timeframe.label}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-32">
          {TIMEFRAMES.map((tf) => (
            <DropdownMenuItem key={tf.value} onClick={() => onTimeframeChange(tf.value)} className="font-mono">
              {tf.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Indicators dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="outline" size="sm" className="h-8 gap-1.5" />}
        >
          <SlidersHorizontal className="size-3.5" /> Indikator
          {activeLabels.length > 0 && (
            <span className="ml-1 rounded-full bg-secondary px-1.5 text-[10px] font-mono font-bold text-muted-foreground">
              {activeLabels.length}
            </span>
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {(["trend", "volatility", "momentum", "volume"] as const).map((cat) => (
            <DropdownMenuGroup key={cat}>
              {cat !== "trend" && <DropdownMenuSeparator />}
              <DropdownMenuLabel className="text-[10px] uppercase tracking-wider text-muted-foreground">{cat}</DropdownMenuLabel>
              {INDICATORS.filter((i) => i.category === cat).map((i) => (
                <DropdownMenuItem key={i.id} onSelect={(e) => e.preventDefault()} onClick={() => onToggleIndicator(i.id)}
                  className="flex items-center justify-between">
                  <span>{i.label}</span>
                  <span className={cn("flex size-4 items-center justify-center rounded border",
                    indicators.includes(i.id) ? "border-chart-2 bg-chart-2 text-background" : "border-border")}>
                    {indicators.includes(i.id) && "✓"}
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Chart type dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="outline" size="sm" className="h-8 gap-1.5" />}
        >
          <Cpu className="size-3.5" /> {CHART_TYPES.find((c) => c.value === chartType)?.label}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-40">
          {CHART_TYPES.map((c) => (
            <DropdownMenuItem key={c.value} onClick={() => onChartTypeChange(c.value)}>
              {c.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Scale toggle */}
      <Button variant="outline" size="sm" className="h-8 font-mono" onClick={() => onScaleChange(scale === "linear" ? "log" : "linear")}>
        {scale === "linear" ? "Lin" : "Log"}
      </Button>

      {/* Export */}
      <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={onExport}>
        <LogIn className="size-3.5" /> Export
      </Button>

      {/* Active indicator chips */}
      <div className="flex flex-wrap items-center gap-1 ml-auto">
        {activeLabels.map((i) => (
          <button key={i.id} onClick={() => onToggleIndicator(i.id)} type="button"
            className="rounded-md border border-border bg-secondary/50 px-2 py-0.5 text-[10px] font-mono font-semibold text-muted-foreground hover:text-foreground transition-colors">
            {i.label} <span className="ml-0.5 text-muted-foreground/50">×</span>
          </button>
        ))}
      </div>
    </div>
  );
}