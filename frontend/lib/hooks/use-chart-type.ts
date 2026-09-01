"use client";
import { useState, useEffect, useCallback } from "react";

export type ChartType = "candle" | "line" | "area" | "heikin-ashi";
const KEY = "astalink_chart_type";
const OPTIONS: ChartType[] = ["candle", "line", "area", "heikin-ashi"];

export function useChartType(defaultValue: ChartType = "candle") {
  const [chartType, setChartTypeState] = useState<ChartType>(defaultValue);
  useEffect(() => {
    try {
      const s = localStorage.getItem(KEY) as ChartType | null;
      if (s && OPTIONS.includes(s)) setChartTypeState(s);
    } catch {}
  }, []);
  const setChartType = useCallback((v: ChartType) => {
    setChartTypeState(v);
    try { localStorage.setItem(KEY, v); } catch {}
  }, []);
  return { chartType, setChartType };
}