"use client";
import { useState, useEffect, useCallback } from "react";

export type IndicatorId =
  | "sma20" | "ema9" | "ema20" | "ema50" | "vwap"
  | "bb" | "macd" | "rsi" | "atr" | "stoch" | "volume" | "obv";

export interface IndicatorConfig {
  id: IndicatorId;
  label: string;
  category: "trend" | "volatility" | "momentum" | "volume";
  default: boolean;
  intradayOnly?: boolean;
}

export const INDICATORS: IndicatorConfig[] = [
  { id: "sma20", label: "SMA 20", category: "trend", default: true },
  { id: "ema9", label: "EMA 9", category: "trend", default: true },
  { id: "ema20", label: "EMA 20", category: "trend", default: true },
  { id: "ema50", label: "EMA 50", category: "trend", default: false },
  { id: "vwap", label: "VWAP", category: "trend", default: false, intradayOnly: true },
  { id: "bb", label: "Bollinger Bands", category: "volatility", default: true },
  { id: "atr", label: "ATR 14", category: "volatility", default: false },
  { id: "macd", label: "MACD", category: "momentum", default: true },
  { id: "rsi", label: "RSI 14", category: "momentum", default: true },
  { id: "stoch", label: "Stochastic", category: "momentum", default: false },
  { id: "volume", label: "Volume", category: "volume", default: true },
  { id: "obv", label: "OBV", category: "volume", default: false },
];

const KEY = "astalink_indicators";

export const DEFAULT_INDICATORS = INDICATORS.filter((i) => i.default).map((i) => i.id);

export function useIndicators(defaultValue: IndicatorId[] = DEFAULT_INDICATORS) {
  const [indicators, setIndicatorsState] = useState<IndicatorId[]>(defaultValue);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved) {
        const parsed: IndicatorId[] = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) setIndicatorsState(parsed);
      }
    } catch {}
  }, []);

  const setIndicators = useCallback((v: IndicatorId[]) => {
    setIndicatorsState(v);
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch {}
  }, []);

  const toggle = useCallback((id: IndicatorId) => {
    setIndicatorsState((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  return { indicators, setIndicators, toggle };
}