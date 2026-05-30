"use client";

import { useEffect, useCallback } from "react";

type KeyCombo = {
  key: string;
  meta?: boolean;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
};

export function useKeyboard(
  combo: KeyCombo,
  handler: (e: KeyboardEvent) => void,
  options?: { preventDefault?: boolean; enabled?: boolean }
) {
  const callback = useCallback(
    (e: KeyboardEvent) => {
      if (options?.enabled === false) return;

      const isMac = typeof navigator !== "undefined" && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent);
      const metaMatch = combo.meta ? (isMac ? e.metaKey : e.metaKey || e.ctrlKey) : !e.metaKey && !e.ctrlKey || !combo.meta;
      const ctrlMatch = combo.ctrl ? e.ctrlKey : !e.ctrlKey || !combo.ctrl;
      const shiftMatch = combo.shift ? e.shiftKey : !e.shiftKey || !combo.shift;
      const altMatch = combo.alt ? e.altKey : !e.altKey || !combo.alt;

      if (
        e.key.toLowerCase() === combo.key.toLowerCase() &&
        (combo.meta ? (isMac ? e.metaKey : e.metaKey || e.ctrlKey) : true) &&
        (combo.ctrl ? e.ctrlKey : true) &&
        (combo.shift ? e.shiftKey : true) &&
        (combo.alt ? e.altKey : true)
      ) {
        if (options?.preventDefault !== false) {
          e.preventDefault();
        }
        handler(e);
      }
    },
    [combo.key, combo.meta, combo.ctrl, combo.shift, combo.alt, handler, options?.preventDefault, options?.enabled]
  );

  useEffect(() => {
    window.addEventListener("keydown", callback);
    return () => window.removeEventListener("keydown", callback);
  }, [callback]);
}
