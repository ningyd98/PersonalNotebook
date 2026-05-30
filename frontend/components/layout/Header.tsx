"use client";

import { useMemo } from "react";
import { usePathname } from "next/navigation";
import { Search, Bell, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const pathLabels: Record<string, string> = {
  "": "仪表盘",
  kb: "知识库",
  documents: "文档",
  chat: "问答",
  eval: "评测",
  debug: "调试",
  status: "状态",
};

export function Header({ onCommandPalette }: { onCommandPalette?: () => void }) {
  const pathname = usePathname();

  const breadcrumbs = useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    const items = [{ label: "首页", href: "/" }];
    let currentPath = "";
    for (const seg of segments) {
      currentPath += `/${seg}`;
      items.push({
        label: pathLabels[seg] || seg,
        href: currentPath,
      });
    }
    return items;
  }, [pathname]);

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b bg-background/80 backdrop-blur-sm flex-shrink-0">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm">
        {breadcrumbs.map((item, idx) => (
          <span key={item.href} className="flex items-center gap-1">
            {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
            {idx === breadcrumbs.length - 1 ? (
              <span className="font-medium text-foreground">{item.label}</span>
            ) : (
              <span className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                {item.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="gap-2 text-muted-foreground"
              onClick={onCommandPalette}
            >
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline text-xs">搜索</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono bg-muted rounded border">
                ⌘K
              </kbd>
            </Button>
          </TooltipTrigger>
          <TooltipContent>快速搜索 (⌘K)</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="icon" className="text-muted-foreground relative">
              <Bell className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>通知</TooltipContent>
        </Tooltip>

        <Avatar className="h-8 w-8 cursor-pointer">
          <AvatarFallback className="text-xs bg-brand text-brand-foreground">
            PN
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
