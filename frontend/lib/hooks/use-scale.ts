"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "astalink_scale";
export type Scale = "linear" | "log";
export function useScale(defaultValue: Scale = "linear") {
  const [scale, setScaleState] = useState<Scale>(defaultValue);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = localStorage.getItem(KEY) as Scale | null;
        if (saved === "linear" || saved === "log") setScaleState(saved);
      } catch {}
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const setScale = useCallback((v: Scale) => {
    setScaleState(v);
    try { localStorage.setItem(KEY, v); } catch {}
  }, []);
  return { scale, setScale };
}
