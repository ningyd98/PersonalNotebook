"use client";

import { useState, useCallback, createContext, useContext } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useTheme } from "@/hooks/useTheme";
import { useKeyboard } from "@/hooks/useKeyboard";

function ThemeInitializer() {
  useTheme();
  return null;
}

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-lg border shadow-lg text-sm animate-slideInRight ${
            t.type === "error"
              ? "bg-destructive text-destructive-foreground border-destructive"
              : t.type === "success"
              ? "bg-green-600 text-white border-green-700"
              : "bg-card text-card-foreground border-border"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <span>{t.message}</span>
            <button onClick={() => onDismiss(t.id)} className="text-current opacity-70 hover:opacity-100 text-xs">
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

interface Toast {
  id: string;
  message: string;
  type: "info" | "success" | "error";
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: Toast["type"] = "info") => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

const ToastContext = createContext<{
  addToast: (message: string, type?: Toast["type"]) => void;
}>({ addToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useKeyboard({ key: "k", meta: true }, () => {
    setCommandPaletteOpen((prev) => !prev);
  });

  return (
    <TooltipProvider delayDuration={200}>
      <ThemeInitializer />
      <ToastProvider>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <Header onCommandPalette={() => setCommandPaletteOpen(true)} />
            <main className="flex-1 overflow-auto p-6">
              {children}
            </main>
          </div>
        </div>
        <CommandPalette
          open={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
        />
      </ToastProvider>
    </TooltipProvider>
  );
}
