"use client";
import { useState, useEffect, useCallback } from "react";

export type ChartType = "candle" | "line" | "area" | "heikin-ashi";
const KEY = "astalink_chart_type";
const OPTIONS: ChartType[] = ["candle", "line", "area", "heikin-ashi"];

export function useChartType(defaultValue: ChartType = "candle") {
  const [chartType, setChartTypeState] = useState<ChartType>(defaultValue);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = localStorage.getItem(KEY) as ChartType | null;
        if (saved && OPTIONS.includes(saved)) setChartTypeState(saved);
      } catch {}
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const setChartType = useCallback((v: ChartType) => {
    setChartTypeState(v);
    try { localStorage.setItem(KEY, v); } catch {}
  }, []);
  return { chartType, setChartType };
}
