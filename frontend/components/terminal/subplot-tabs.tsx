"use client";
import { useState } from "react";
import {
  ComposedChart,
  ResponsiveContainer,
  Bar,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import type { ExtendedPricePoint } from "@/lib/api-client";

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

interface SubplotTabsProps {
  data: ExtendedPricePoint[];
  subplots: { id: string; label: string }[];
}

function xIsSameDay(data: ExtendedPricePoint[]): boolean {
  if (data.length === 0) return false;
  const first = data[0].date.slice(0, 10);
  return data.every((d) => d.date.slice(0, 10) === first);
}

export function SubplotTabs({ data, subplots }: SubplotTabsProps) {
  const [activeTab, setActiveTab] = useState<string>(subplots[0]?.id ?? "volume");
  const xKey = xIsSameDay(data) ? "date" : "date";

  return (
    <div className="rounded-xl border border-border bg-card/40 p-3">
      <div className="flex items-center gap-1 border-b border-border pb-2 mb-2">
        {subplots.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveTab(s.id)}
            type="button"
            className={`rounded-t-lg px-3 py-1.5 text-[10px] font-mono font-medium transition-colors ${
              activeTab === s.id
                ? "text-foreground bg-card border-b-2 border-chart-2"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={128}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey={xKey} hide />
          <Tooltip contentStyle={TOOLTIP_STYLE} />

          {activeTab === "volume" && (
            <>
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Bar dataKey="volume" fill="var(--color-chart-3)" opacity={0.6} />
            </>
          )}

          {activeTab === "rsi" && (
            <>
              <YAxis
                domain={[0, 100]}
                ticks={[30, 50, 70]}
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <ReferenceLine y={70} stroke="var(--color-destructive)" strokeDasharray="3 3" />
              <ReferenceLine y={30} stroke="var(--color-chart-1)" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="rsi14"
                stroke="#a1a1aa"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </>
          )}

          {activeTab === "macd" && (
            <>
              <YAxis
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
              <Bar dataKey="macd_hist" fill="var(--color-chart-4)" opacity={0.6} />
              <Line
                type="monotone"
                dataKey="macd_line"
                stroke="var(--color-chart-2)"
                strokeWidth={1.2}
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="macd_signal"
                stroke="#a1a1aa"
                strokeWidth={1.2}
                dot={false}
                connectNulls
              />
            </>
          )}

          {activeTab === "atr" && (
            <>
              <YAxis
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Line
                type="monotone"
                dataKey="atr14"
                stroke="var(--color-chart-1)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </>
          )}

          {activeTab === "stoch" && (
            <>
              <YAxis
                domain={[0, 100]}
                ticks={[20, 50, 80]}
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <ReferenceLine y={80} stroke="var(--color-destructive)" strokeDasharray="3 3" />
              <ReferenceLine y={20} stroke="var(--color-chart-1)" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="stoch_k"
                stroke="var(--color-chart-2)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="stoch_d"
                stroke="#a1a1aa"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </>
          )}

          {activeTab === "obv" && (
            <>
              <YAxis
                tick={{ fill: "#a1a1aa", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Line
                type="monotone"
                dataKey="obv"
                stroke="var(--color-chart-3)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}