"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "astalink_sidebar_collapsed";
export function useSidebarCollapsed(defaultValue = false) {
  const [collapsed, setCollapsedState] = useState(defaultValue);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const saved = localStorage.getItem(KEY);
        if (saved !== null) setCollapsedState(saved === "true");
      } catch {}
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  const setCollapsed = useCallback((v: boolean) => {
    setCollapsedState(v);
    try { localStorage.setItem(KEY, String(v)); } catch {}
  }, []);
  return { collapsed, setCollapsed };
}
