"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, BookOpen, Loader2, AlertCircle } from "lucide-react";
import { kbApi, apiFetch } from "@/lib/api";

export default function KBPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [kbs, setKbs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const fetchKBs = async () => {
    setLoading(true);
    try {
      const data = await apiFetch("/api/kbs?page_size=50");
      setKbs(data.items || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKBs(); }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await kbApi.create({ name, description });
      setName("");
      setDescription("");
      await fetchKBs();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除此知识库？")) return;
    try {
      await kbApi.delete(id);
      await fetchKBs();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">知识库管理</h1>
        <p className="text-muted-foreground">创建和管理你的知识库</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm p-3 bg-red-50 rounded-md">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      <div className="bg-card rounded-lg border p-4 space-y-3 max-w-lg">
        <h3 className="font-semibold">新建知识库</h3>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)}
          placeholder="知识库名称" className="w-full px-3 py-2 border rounded-md text-sm bg-background" />
        <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
          placeholder="描述（可选）" className="w-full px-3 py-2 border rounded-md text-sm bg-background" />
        <button onClick={handleCreate} disabled={creating || !name.trim()}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 disabled:opacity-50">
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          创建知识库
        </button>
      </div>

      <div>
        <h3 className="font-semibold mb-3">我的知识库 ({kbs.length})</h3>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : kbs.length === 0 ? (
          <div className="text-center text-muted-foreground py-8 bg-card rounded-lg border">
            <BookOpen className="h-10 w-10 mx-auto mb-2 opacity-20" />
            <p className="text-sm">暂无知识库，请创建一个</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {kbs.map((kb: any) => (
              <div key={kb.id} className="bg-card rounded-lg border p-4 space-y-2">
                <div className="flex items-start justify-between">
                  <h4 className="font-semibold truncate">{kb.name}</h4>
                  <button onClick={() => handleDelete(kb.id)} className="text-red-400 hover:text-red-600">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">{kb.description || "无描述"}</p>
                <div className="flex gap-3 text-xs text-muted-foreground">
                  <span>📄 {kb.document_count || 0} 文档</span>
                  <span>🧩 {kb.chunk_count || 0} Chunks</span>
                </div>
                <div className="text-xs text-muted-foreground font-mono break-all">
                  ID: {kb.id?.substring(0, 8)}...
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
