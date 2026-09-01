"use client";
import { useState, useEffect, useCallback } from "react";

export type Timeframe = "1H" | "1D" | "1W" | "1M" | "3M" | "6M" | "1Y" | "5Y" | "ALL";

export interface TimeframeConfig {
  label: string;
  value: Timeframe;
  period: string;
  interval: string;
}

export const TIMEFRAMES: TimeframeConfig[] = [
  { label: "1H", value: "1H", period: "1d", interval: "5m" },
  { label: "1D", value: "1D", period: "1d", interval: "15m" },
  { label: "1W", value: "1W", period: "1wk", interval: "30m" },
  { label: "1M", value: "1M", period: "1mo", interval: "1d" },
  { label: "3M", value: "3M", period: "3mo", interval: "1d" },
  { label: "6M", value: "6M", period: "6mo", interval: "1d" },
  { label: "1Y", value: "1Y", period: "1y", interval: "1wk" },
  { label: "5Y", value: "5Y", period: "5y", interval: "1mo" },
  { label: "ALL", value: "ALL", period: "max", interval: "3mo" },
];

const KEY = "astalink_timeframe";

export function useTimeframe(defaultValue: Timeframe = "1M") {
  const [timeframe, setTimeframeState] = useState<Timeframe>(defaultValue);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY) as Timeframe | null;
      if (saved && TIMEFRAMES.some((t) => t.value === saved)) setTimeframeState(saved);
    } catch {}
  }, []);

  const setTimeframe = useCallback((v: Timeframe) => {
    setTimeframeState(v);
    try { localStorage.setItem(KEY, v); } catch {}
  }, []);

  const config = TIMEFRAMES.find((t) => t.value === timeframe) ?? TIMEFRAMES[3];
  return { timeframe, setTimeframe, config, timeframes: TIMEFRAMES };
}