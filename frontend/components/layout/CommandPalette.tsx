"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, FileText, BookOpen, MessageSquare, BarChart3, Bug, Server, LayoutDashboard, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useKeyboard } from "@/hooks/useKeyboard";

const commands = [
  { id: "dashboard", label: "仪表盘", icon: LayoutDashboard, href: "/" },
  { id: "kb", label: "知识库管理", icon: BookOpen, href: "/kb" },
  { id: "documents", label: "文档管理", icon: FileText, href: "/documents" },
  { id: "chat", label: "RAG 问答", icon: MessageSquare, href: "/chat" },
  { id: "eval", label: "评测管理", icon: BarChart3, href: "/eval" },
  { id: "debug", label: "Debug Trace", icon: Bug, href: "/debug" },
  { id: "status", label: "系统状态", icon: Server, href: "/status" },
];

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const execute = useCallback((cmd: typeof commands[0]) => {
    router.push(cmd.href);
    onClose();
  }, [router, onClose]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        execute(filtered[selectedIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, filtered, selectedIndex, execute, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-card border rounded-xl shadow-lg overflow-hidden animate-scaleIn">
        <div className="flex items-center gap-3 px-4 border-b">
          <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索页面或功能..."
            className="flex-1 py-3 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded border">
            ESC
          </kbd>
        </div>
        <div className="max-h-72 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-muted-foreground">
              无匹配结果
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon;
              return (
                <button
                  key={cmd.id}
                  onClick={() => execute(cmd)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={cn(
                    "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                    idx === selectedIndex
                      ? "bg-accent text-accent-foreground"
                      : "text-foreground hover:bg-accent/50"
                  )}
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 text-left">{cmd.label}</span>
                  {idx === selectedIndex && (
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
