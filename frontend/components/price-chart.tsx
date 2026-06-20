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
  background: "#16181c",
  border: "1px solid #2a2d36",
  color: "#ffffff",
  borderRadius: "8px",
  fontSize: "12px",
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
  const changeColor = isUp ? "#05b169" : "#cf202f";

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
      <div className="flex items-baseline gap-3 mb-3">
        <span className="text-[#a8acb3] text-xs font-mono">{ticker.replace(".JK", "")}</span>
        <span className="font-mono text-2xl font-medium text-white">
          {lastClose != null ? formatIDR(lastClose) : "—"}
        </span>
        <span className="font-mono text-sm" style={{ color: changeColor }}>
          {priceChangePct != null
            ? `${priceChangePct >= 0 ? "+" : ""}${priceChangePct.toFixed(2)}%`
            : ""}
        </span>
        {bbUpper != null && bbLower != null && (
          <span className="text-[#a8acb3] text-xs font-mono">
            BB {formatIDR(bbLower)}–{formatIDR(bbUpper)}
          </span>
        )}
      </div>

      {/* Main price chart */}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={priceData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0052ff" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#0052ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#a8acb3", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#a8acb3", fontSize: 10 }}
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
            stroke="#0052ff"
            strokeWidth={2}
            fill="url(#priceGrad)"
            dot={false}
            activeDot={{ r: 4, fill: "#0052ff" }}
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
            stroke="#a8acb3"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 2"
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* RSI subplot label */}
      <div className="text-[#a8acb3] text-[10px] font-mono mt-2 mb-1">RSI 14</div>

      {/* RSI chart */}
      <ResponsiveContainer width="100%" height={72}>
        <LineChart data={rsiData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" vertical={false} />
          <XAxis dataKey="date" hide />
          <YAxis
            domain={[0, 100]}
            ticks={[30, 50, 70]}
            tick={{ fill: "#a8acb3", fontSize: 10 }}
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
            stroke="#a8acb3"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-2 text-[10px] font-mono text-[#a8acb3]">
        <span><span className="inline-block w-3 h-0.5 bg-[#0052ff] mr-1 align-middle" />Harga</span>
        <span><span className="inline-block w-3 h-0.5 bg-[#f4b000] mr-1 align-middle" style={{ borderTop: "1.5px dashed #f4b000" }} />SMA20</span>
        <span><span className="inline-block w-3 h-0.5 bg-[#a8acb3] mr-1 align-middle" style={{ borderTop: "1.5px dashed #a8acb3" }} />EMA50</span>
      </div>
    </div>
  );
}
