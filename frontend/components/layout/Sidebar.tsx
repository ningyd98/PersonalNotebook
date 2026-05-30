"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain, LayoutDashboard, BookOpen, FileText, MessageSquare,
  BarChart3, Bug, Server, Sun, Moon, ChevronsLeft, ChevronsRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/useTheme";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";

const navItems = [
  { href: "/", label: "仪表盘", icon: LayoutDashboard },
  { href: "/kb", label: "知识库", icon: BookOpen },
  { href: "/documents", label: "文档", icon: FileText },
  { href: "/chat", label: "问答", icon: MessageSquare },
  { href: "/eval", label: "评测", icon: BarChart3 },
  { href: "/debug", label: "调试", icon: Bug },
  { href: "/status", label: "状态", icon: Server },
];

export function Sidebar() {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("sidebar-collapsed");
    if (stored !== null) {
      setCollapsed(stored === "true");
    }
  }, []);

  const toggleCollapsed = useCallback(() => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("sidebar-collapsed", String(next));
  }, [collapsed]);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  return (
    <aside
      className={cn(
        "flex flex-col h-screen border-r border-sidebar-border bg-sidebar-bg transition-all duration-300 ease-in-out flex-shrink-0",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-sidebar-border flex-shrink-0">
        <Brain className="h-6 w-6 text-brand flex-shrink-0" />
        {!collapsed && (
          <span className="font-bold text-base text-sidebar-foreground truncate">
            PersonalNotebook
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          const link = (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md text-sm transition-all duration-200",
                collapsed ? "justify-center px-2 py-2.5" : "px-3 py-2.5",
                isActive
                  ? "bg-sidebar-active text-sidebar-foreground font-medium"
                  : "text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              <Icon className={cn("h-4 w-4 flex-shrink-0", isActive && "text-brand")} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.href} delayDuration={0}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  {item.label}
                </TooltipContent>
              </Tooltip>
            );
          }
          return link;
        })}
      </nav>

      <Separator className="bg-sidebar-border" />

      {/* Footer */}
      <div className={cn("py-3 px-2 space-y-2 flex-shrink-0", collapsed ? "flex flex-col items-center" : "")}>
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <button
              onClick={toggleTheme}
              className={cn(
                "flex items-center gap-3 rounded-md text-sm text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors",
                collapsed ? "justify-center p-2.5" : "px-3 py-2 w-full"
              )}
            >
              {resolvedTheme === "dark" ? (
                <Sun className="h-4 w-4 flex-shrink-0" />
              ) : (
                <Moon className="h-4 w-4 flex-shrink-0" />
              )}
              {!collapsed && <span>{resolvedTheme === "dark" ? "浅色模式" : "深色模式"}</span>}
            </button>
          </TooltipTrigger>
          {collapsed && (
            <TooltipContent side="right" sideOffset={8}>
              {resolvedTheme === "dark" ? "浅色模式" : "深色模式"}
            </TooltipContent>
          )}
        </Tooltip>

        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <button
              onClick={toggleCollapsed}
              className={cn(
                "flex items-center gap-3 rounded-md text-sm text-sidebar-muted hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors",
                collapsed ? "justify-center p-2.5" : "px-3 py-2 w-full"
              )}
            >
              {collapsed ? (
                <ChevronsRight className="h-4 w-4 flex-shrink-0" />
              ) : (
                <ChevronsLeft className="h-4 w-4 flex-shrink-0" />
              )}
              {!collapsed && <span>收起侧边栏</span>}
            </button>
          </TooltipTrigger>
          {collapsed && (
            <TooltipContent side="right" sideOffset={8}>
              展开侧边栏
            </TooltipContent>
          )}
        </Tooltip>

        {!collapsed && (
          <p className="text-xs text-sidebar-muted px-3 pt-1">v0.2.0</p>
        )}
      </div>
    </aside>
  );
}
