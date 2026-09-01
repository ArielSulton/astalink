"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "astalink_scale";
export type Scale = "linear" | "log";
export function useScale(defaultValue: Scale = "linear") {
  const [scale, setScaleState] = useState<Scale>(defaultValue);
  useEffect(() => {
    try {
      const s = localStorage.getItem(KEY) as Scale | null;
      if (s === "linear" || s === "log") setScaleState(s);
    } catch {}
  }, []);
  const setScale = useCallback((v: Scale) => {
    setScaleState(v);
    try { localStorage.setItem(KEY, v); } catch {}
  }, []);
  return { scale, setScale };
}