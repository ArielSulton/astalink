"use client";
import { useState, useEffect, useCallback } from "react";
const KEY = "astalink_sidebar_collapsed";
export function useSidebarCollapsed(defaultValue = false) {
  const [collapsed, setCollapsedState] = useState(defaultValue);
  useEffect(() => {
    try {
      const s = localStorage.getItem(KEY);
      if (s !== null) setCollapsedState(s === "true");
    } catch {}
  }, []);
  const setCollapsed = useCallback((v: boolean) => {
    setCollapsedState(v);
    try { localStorage.setItem(KEY, String(v)); } catch {}
  }, []);
  return { collapsed, setCollapsed };
}