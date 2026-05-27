"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, BookOpen, FileText, MessageSquare,
  BarChart3, Bug, Server,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "仪表盘", icon: LayoutDashboard },
  { href: "/kb", label: "知识库", icon: BookOpen },
  { href: "/documents", label: "文档", icon: FileText },
  { href: "/chat", label: "问答", icon: MessageSquare },
  { href: "/debug", label: "Debug", icon: Bug },
  { href: "/eval", label: "评测", icon: BarChart3 },
  { href: "/status", label: "状态", icon: Server },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-60 border-r bg-card flex flex-col min-h-screen">
      <div className="p-4 border-b">
        <h1 className="text-lg font-bold text-primary">Personal-KB</h1>
        <p className="text-xs text-muted-foreground">个人知识库</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link key={item.href} href={item.href}
              className={cn("flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                isActive ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground")}>
              <Icon className="h-4 w-4" />{item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t">
        <p className="text-xs text-muted-foreground">v0.2.0 Phase 2A</p>
      </div>
    </aside>
  );
}
