"use client";
import {
  Area, Bar, ComposedChart, CartesianGrid, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { ExtendedPricePoint } from "@/lib/api-client";
import type { IndicatorId } from "@/lib/hooks/use-indicators";
import type { ChartType } from "@/lib/hooks/use-chart-type";
import { cn } from "@/lib/utils";

export const TOOLTIP_STYLE = {
  background: "rgba(23, 23, 23, 0.97)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  color: "#fafafa",
  borderRadius: "12px",
  fontSize: "11px",
  boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.6)",
  backdropFilter: "blur(8px)",
};

function fmtIDR(v: number): string {
  return `Rp ${v.toLocaleString("id-ID")}`;
}

interface MainChartAreaProps {
  data: ExtendedPricePoint[];
  indicators: IndicatorId[];
  chartType: ChartType;
  scale: "linear" | "log";
  lastClose: number | null;
  priceChangePct: number | null;
}

export function MainChartArea({
  data, indicators, chartType, scale, lastClose, priceChangePct,
}: MainChartAreaProps) {
  const isUp = (priceChangePct ?? 0) >= 0;
  const showSma20 = indicators.includes("sma20");
  const showEma9 = indicators.includes("ema9");
  const showEma20 = indicators.includes("ema20");
  const showEma50 = indicators.includes("ema50");
  const showVwap = indicators.includes("vwap");
  const showBB = indicators.includes("bb");

  const yScale = scale === "log" ? "log" : "auto";

  return (
    <div className="rounded-xl border border-border bg-card/40 p-4">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <span className="font-mono text-3xl font-bold text-foreground tracking-tight tabular-nums">
          {lastClose != null ? fmtIDR(lastClose) : "—"}
        </span>
        {priceChangePct != null && (
          <span className={cn("font-mono text-xs font-semibold px-2 py-0.5 rounded-lg border",
            isUp ? "bg-chart-2/10 text-chart-2 border-chart-2/20" : "bg-destructive/10 text-destructive border-destructive/20")}>
            {priceChangePct >= 0 ? "▲" : "▼"} {Math.abs(priceChangePct).toFixed(2)}%
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-chart-2)" stopOpacity={0.2} />
              <stop offset="95%" stopColor="var(--color-chart-2)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: "#a1a1aa", fontSize: 10 }} tickLine={false} axisLine={false}
            interval="preserveStartEnd" />
          <YAxis yAxisId="price" scale={yScale} domain={["auto", "auto"]}
            tick={{ fill: "#a1a1aa", fontSize: 10 }} tickLine={false} axisLine={false} width={80} orientation="right"
            tickFormatter={(v: number) => v.toLocaleString("id-ID")} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v: unknown, name: unknown) => [
              typeof v === "number" ? fmtIDR(v) : String(v),
              typeof name === "string" ? name.toUpperCase() : String(name),
            ]}
          />

          {/* BB band fill (drawn before price so it sits under) */}
          {showBB && (
            <>
              <Area yAxisId="price" type="monotone" dataKey="bb_upper" stroke="none" fill="var(--color-chart-1)"
                fillOpacity={0.06} connectNulls />
              <Area yAxisId="price" type="monotone" dataKey="bb_lower" stroke="none" fill="transparent" connectNulls />
              <Line yAxisId="price" type="monotone" dataKey="bb_upper" stroke="var(--color-chart-1)" strokeWidth={1}
                strokeDasharray="3 3" strokeOpacity={0.7} dot={false} connectNulls />
              <Line yAxisId="price" type="monotone" dataKey="bb_lower" stroke="var(--color-chart-1)" strokeWidth={1}
                strokeDasharray="3 3" strokeOpacity={0.7} dot={false} connectNulls />
            </>
          )}

          {/* Price */}
          {chartType === "area" && (
            <Area yAxisId="price" type="monotone" dataKey="close" stroke="var(--color-chart-2)" strokeWidth={2}
              fill="url(#priceGrad)" dot={false} />
          )}
          {chartType === "line" && (
            <Line yAxisId="price" type="monotone" dataKey="close" stroke="var(--color-chart-2)" strokeWidth={2}
              dot={false} connectNulls />
          )}
          {chartType === "heikin-ashi" && (
            <Line yAxisId="price" type="monotone" dataKey="close" stroke="var(--color-chart-2)" strokeWidth={2}
              dot={false} connectNulls />
          )}
          {(chartType === "candle" || chartType === "heikin-ashi") && (
            // Default candle-like rendering via bars when chartType is candle:
            <Bar yAxisId="price" dataKey="close" fill="var(--color-chart-2)" fillOpacity={0.15} />
          )}

          {/* Overlays */}
          {showSma20 && <Line yAxisId="price" type="monotone" dataKey="sma20" stroke="var(--color-chart-1)" strokeWidth={1.5} dot={false} connectNulls />}
          {showEma9 && <Line yAxisId="price" type="monotone" dataKey="ema9" stroke="var(--color-chart-3)" strokeWidth={1.5} dot={false} connectNulls />}
          {showEma20 && <Line yAxisId="price" type="monotone" dataKey="ema20" stroke="var(--color-chart-4)" strokeWidth={1.5} dot={false} connectNulls />}
          {showEma50 && <Line yAxisId="price" type="monotone" dataKey="ema50" stroke="#a1a1aa" strokeWidth={1.5} dot={false} connectNulls />}
          {showVwap && <Line yAxisId="price" type="monotone" dataKey="vwap" stroke="var(--color-destructive)" strokeWidth={1.5} strokeDasharray="4 2" dot={false} connectNulls />}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-2 text-[10px] font-mono text-muted-foreground">
        <span><span className="inline-block w-3 h-0.5 bg-chart-2 mr-1 align-middle" />Harga</span>
        {showSma20 && <span><span className="inline-block w-3 h-0.5 bg-chart-1 mr-1 align-middle" />SMA20</span>}
        {showEma9 && <span><span className="inline-block w-3 h-0.5 bg-chart-3 mr-1 align-middle" />EMA9</span>}
        {showEma20 && <span><span className="inline-block w-3 h-0.5 bg-chart-4 mr-1 align-middle" />EMA20</span>}
        {showEma50 && <span><span className="inline-block w-3 h-0.5 mr-1 align-middle" style={{ background: "#a1a1aa" }} />EMA50</span>}
        {showVwap && <span><span className="inline-block w-3 h-0.5 bg-destructive mr-1 align-middle" />VWAP</span>}
        {showBB && <span><span className="inline-block w-3 h-0.5 mr-1 align-middle" style={{ borderTop: "1.5px dashed var(--color-chart-1)" }} />BB</span>}
      </div>
    </div>
  );
}