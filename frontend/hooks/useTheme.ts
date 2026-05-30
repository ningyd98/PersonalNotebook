"use client";

import { useEffect, useState, useCallback } from "react";

type Theme = "light" | "dark" | "system";

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === "undefined") return "system";
    return (localStorage.getItem("theme") as Theme) || "system";
  });

  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    const stored = (localStorage.getItem("theme") as Theme) || "system";
    return stored === "system" ? getSystemTheme() : stored;
  });

  useEffect(() => {
    const root = document.documentElement;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const applyTheme = () => {
      const resolved = theme === "system" ? getSystemTheme() : theme;
      setResolvedTheme(resolved);
      root.classList.remove("light", "dark");
      root.classList.add(resolved);
    };

    applyTheme();
    mediaQuery.addEventListener("change", applyTheme);
    return () => mediaQuery.removeEventListener("change", applyTheme);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem("theme", t);
  }, []);

  return { theme, setTheme, resolvedTheme };
}
