"use client";

import { useEffect, useState, useMemo } from "react";
import {
  Plus, Trash2, BookOpen, MoreHorizontal, Search, Loader2, FolderOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { kbApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import { useToast } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";

interface KB {
  id: string;
  name: string;
  description?: string;
  document_count: number;
  chunk_count: number;
  updated_at?: string;
  embedding_model?: string;
}

const EMBEDDING_MODELS = [
  { value: "bge-m3", label: "BGE-M3 (推荐)" },
  { value: "bge-large-zh", label: "BGE-Large-ZH" },
  { value: "text2vec-large-chinese", label: "Text2Vec-Large" },
  { value: "m3e-large", label: "M3E-Large" },
];

export default function KBPage() {
  const [kbs, setKbs] = useState<KB[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createModel, setCreateModel] = useState("bge-m3");
  const [creating, setCreating] = useState(false);

  // Delete dialog
  const [deleteTarget, setDeleteTarget] = useState<KB | null>(null);
  const [deleting, setDeleting] = useState(false);

  const { addToast } = useToast();

  const fetchKBs = async () => {
    setLoading(true);
    try {
      const data = await kbApi.list({ page_size: 100 });
      setKbs(data.items || []);
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKBs(); }, []);

  const filteredKBs = useMemo(() => {
    if (!debouncedSearch) return kbs;
    const q = debouncedSearch.toLowerCase();
    return kbs.filter((kb) =>
      kb.name.toLowerCase().includes(q) || kb.description?.toLowerCase().includes(q)
    );
  }, [kbs, debouncedSearch]);

  const handleCreate = async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      await kbApi.create({ name: createName, description: createDesc, embedding_model: createModel });
      setCreateName(""); setCreateDesc(""); setCreateModel("bge-m3");
      setCreateOpen(false);
      addToast("知识库创建成功", "success");
      await fetchKBs();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await kbApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      addToast("知识库已删除", "success");
      await fetchKBs();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">知识库管理</h1>
          <p className="text-muted-foreground text-sm">创建和管理你的知识库</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          新建知识库
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索知识库..."
          className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner className="h-8 w-8" />
        </div>
      ) : filteredKBs.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={searchQuery ? "无匹配的知识库" : "暂无知识库"}
          description={searchQuery ? "尝试其他搜索词" : "点击上方按钮创建第一个知识库"}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredKBs.map((kb) => (
            <Card
              key={kb.id}
              className="p-5 hover:shadow-md transition-all duration-200 group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-brand/10">
                    <FolderOpen className="h-4 w-4 text-brand" />
                  </div>
                  <h3 className="font-semibold text-sm truncate max-w-[180px]">{kb.name}</h3>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => setDeleteTarget(kb)}>
                      <Trash2 className="h-4 w-4 mr-2" />
                      删除
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>

              <p className="text-xs text-muted-foreground line-clamp-2 mb-4 min-h-[2rem]">
                {kb.description || "暂无描述"}
              </p>

              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <Badge variant="secondary" className="text-xs">
                  {kb.document_count || 0} 文档
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  {kb.chunk_count || 0} Chunks
                </Badge>
              </div>

              <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-muted-foreground">
                <span>{kb.updated_at ? new Date(kb.updated_at).toLocaleDateString("zh-CN") : "—"}</span>
                {kb.embedding_model && (
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {kb.embedding_model}
                  </Badge>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建知识库</DialogTitle>
            <DialogDescription>创建一个新的知识库来管理文档</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium mb-1.5 block">名称</label>
              <Input
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="知识库名称"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">描述</label>
              <Input
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
                placeholder="描述（可选）"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">嵌入模型</label>
              <select
                value={createModel}
                onChange={(e) => setCreateModel(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm bg-background"
              >
                {EMBEDDING_MODELS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
            <Button onClick={handleCreate} disabled={!createName.trim() || creating} loading={creating}>
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除知识库「{deleteTarget?.name}」吗？此操作不可撤销，关联的文档和数据将一并删除。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDelete} loading={deleting}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
