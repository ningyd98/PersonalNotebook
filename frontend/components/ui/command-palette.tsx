"use client";

import * as React from "react";
import { Search, Command, FileText, Settings, BookmarkPlus, Hash } from "lucide-react";

import { cn } from "@/lib/utils";

export interface CommandItem {
  id: string;
  label: string;
  icon?: React.ElementType;
  shortcut?: string;
  onSelect: () => void;
}

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands?: CommandItem[];
}

const defaultCommands: CommandItem[] = [
  {
    id: "new-note",
    label: "新建笔记",
    icon: FileText,
    shortcut: "⌘N",
    onSelect: () => {},
  },
  {
    id: "search",
    label: "搜索笔记",
    icon: Search,
    shortcut: "⌘F",
    onSelect: () => {},
  },
  {
    id: "bookmarks",
    label: "收藏夹",
    icon: BookmarkPlus,
    shortcut: "⌘B",
    onSelect: () => {},
  },
  {
    id: "tags",
    label: "标签管理",
    icon: Hash,
    onSelect: () => {},
  },
  {
    id: "settings",
    label: "设置",
    icon: Settings,
    onSelect: () => {},
  },
];

function CommandPalette({
  open,
  onOpenChange,
  commands = defaultCommands,
}: CommandPaletteProps) {
  const [query, setQuery] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [activeIndex, setActiveIndex] = React.useState(0);

  const filtered = React.useMemo(() => {
    if (!query) return commands;
    const lower = query.toLowerCase();
    return commands.filter((cmd) =>
      cmd.label.toLowerCase().includes(lower)
    );
  }, [commands, query]);

  React.useEffect(() => {
    if (open) {
      setQuery("");
      setActiveIndex(0);
      // Delay focus to allow animation
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  React.useEffect(() => {
    setActiveIndex(0);
  }, [filtered.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filtered.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === "Enter" && filtered[activeIndex]) {
      e.preventDefault();
      filtered[activeIndex].onSelect();
      onOpenChange(false);
    } else if (e.key === "Escape") {
      onOpenChange(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in-0"
        onClick={() => onOpenChange(false)}
      />

      {/* Palette */}
      <div className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2">
        <div className="overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-2xl animate-in fade-in-0 zoom-in-95 slide-in-from-top-4">
          {/* Search Input */}
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入命令或搜索..."
              className="flex-1 bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              ESC
            </kbd>
          </div>

          {/* Command List */}
          <div className="max-h-72 overflow-y-auto p-1">
            {filtered.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                未找到匹配的命令
              </div>
            ) : (
              filtered.map((cmd, index) => {
                const Icon = cmd.icon ?? Command;
                return (
                  <div
                    key={cmd.id}
                    onClick={() => {
                      cmd.onSelect();
                      onOpenChange(false);
                    }}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={cn(
                      "flex cursor-pointer items-center rounded-md px-3 py-2 text-sm transition-colors",
                      index === activeIndex
                        ? "bg-accent text-accent-foreground"
                        : "text-foreground"
                    )}
                  >
                    <Icon className="mr-3 h-4 w-4 text-muted-foreground" />
                    <span className="flex-1">{cmd.label}</span>
                    {cmd.shortcut && (
                      <kbd className="ml-auto text-xs text-muted-foreground">
                        {cmd.shortcut}
                      </kbd>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="border-t px-3 py-2">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <kbd className="rounded border bg-muted px-1 font-mono text-[10px]">↑↓</kbd>
                导航
              </span>
              <span className="flex items-center gap-1">
                <kbd className="rounded border bg-muted px-1 font-mono text-[10px]">↵</kbd>
                选择
              </span>
              <span className="flex items-center gap-1">
                <kbd className="rounded border bg-muted px-1 font-mono text-[10px]">esc</kbd>
                关闭
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export { CommandPalette };
