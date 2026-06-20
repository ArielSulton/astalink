"use client";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PricePoint } from "@/lib/api-client";

interface PriceChartProps {
  ticker: string;
  data: PricePoint[];
  lastClose: number | null;
  priceChangePct: number | null;
  bbUpper: number | null;
  bbLower: number | null;
}

const TOOLTIP_STYLE = {
  background: "rgba(8, 13, 30, 0.97)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  color: "#edf1ff",
  borderRadius: "12px",
  fontSize: "11px",
  boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.6)",
  backdropFilter: "blur(8px)",
};

function formatIDR(v: number): string {
  return `Rp ${v.toLocaleString("id-ID")}`;
}

export function PriceChart({
  ticker,
  data,
  lastClose,
  priceChangePct,
  bbUpper,
  bbLower,
}: PriceChartProps) {
  const isUp = (priceChangePct ?? 0) >= 0;

  const priceData = data.map((d) => ({
    date: d.date.slice(5), // "MM-DD"
    close: d.close,
    sma20: d.sma20,
    ema50: d.ema50,
  }));

  const rsiData = data.map((d) => ({
    date: d.date.slice(5),
    rsi14: d.rsi14,
  }));

  return (
    <div>
      {/* Price header */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <span className="px-2 py-0.5 rounded bg-secondary border border-border text-muted-foreground text-[10px] font-bold font-mono tracking-wider uppercase">
          {ticker.replace(".JK", "")}
        </span>
        <span className="font-mono text-3xl font-bold text-foreground tracking-tight">
          {lastClose != null ? formatIDR(lastClose) : "—"}
        </span>
        {priceChangePct != null && (
          <span
            className={`font-mono text-xs font-semibold px-2 py-0.5 rounded-lg border ${
              isUp
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/15"
                : "bg-red-500/10 text-red-400 border-red-500/15"
            }`}
          >
            {priceChangePct >= 0 ? "▲" : "▼"} {Math.abs(priceChangePct).toFixed(2)}%
          </span>
        )}
        {bbUpper != null && bbLower != null && (
          <span className="text-muted-foreground text-xs font-mono bg-secondary border border-border px-2.5 py-0.5 rounded-lg">
            BB: {formatIDR(bbLower)} – {formatIDR(bbUpper)}
          </span>
        )}
      </div>

      {/* Main price chart */}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={priceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.22} />
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#7585a3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#7585a3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => v.toLocaleString("id-ID")}
            width={76}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v, name) => [
              typeof v === "number" ? formatIDR(v) : String(v),
              name === "close" ? "Harga" : name === "sma20" ? "SMA20" : "EMA50",
            ]}
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke="#2563eb"
            strokeWidth={2}
            fill="url(#priceGrad)"
            dot={false}
            activeDot={{ r: 4, fill: "#2563eb" }}
          />
          <Line
            type="monotone"
            dataKey="sma20"
            stroke="#f4b000"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="ema50"
            stroke="#7585a3"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* RSI subplot label */}
      <div className="text-muted-foreground text-[10px] font-mono mt-2 mb-1">RSI 14</div>

      {/* RSI chart */}
      <ResponsiveContainer width="100%" height={72}>
        <LineChart data={rsiData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis dataKey="date" hide />
          <YAxis
            domain={[0, 100]}
            ticks={[30, 50, 70]}
            tick={{ fill: "#7585a3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={76}
          />
          <ReferenceLine y={70} stroke="#cf202f" strokeDasharray="3 3" strokeWidth={1} />
          <ReferenceLine y={30} stroke="#05b169" strokeDasharray="3 3" strokeWidth={1} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(v) => [typeof v === "number" ? v.toFixed(1) : String(v), "RSI14"]}
          />
          <Line
            type="monotone"
            dataKey="rsi14"
            stroke="#7585a3"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-2 text-[10px] font-mono text-muted-foreground">
        <span><span className="inline-block w-3 h-0.5 bg-[#2563eb] mr-1 align-middle" />Harga</span>
        <span><span className="inline-block w-3 h-0.5 mr-1 align-middle" style={{ borderTop: "1.5px dashed #f4b000" }} />SMA20</span>
        <span><span className="inline-block w-3 h-0.5 mr-1 align-middle" style={{ borderTop: "1.5px dashed #7585a3" }} />EMA50</span>
      </div>
    </div>
  );
}
