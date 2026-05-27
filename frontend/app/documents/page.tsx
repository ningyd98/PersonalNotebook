"use client";

import { useEffect, useState } from "react";
import {
  Upload, FolderOpen, FileText, Trash2, RefreshCw, Eye,
  Loader2, AlertCircle, Search, Filter,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function DocumentsPage() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [kbId, setKbId] = useState("");
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [tab, setTab] = useState<"list" | "detail">("list");
  const [detailData, setDetailData] = useState<any>(null);

  const fetchKBs = async () => {
    try {
      const d = await apiFetch("/api/kbs?page_size=50");
      setKbs(d.items || []);
    } catch {}
  };

  const fetchDocs = async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const d = await apiFetch(`/api/kbs/${kbId}/documents?page_size=50`);
      setDocuments(d.items || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKBs(); }, []);
  useEffect(() => { if (kbId) fetchDocs(); }, [kbId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !kbId) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/kbs/${kbId}/documents/upload`,
        { method: "POST", body: formData }
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.duplicate) {
        setError(`文件已存在 (dedup): ${data.document_id}`);
      }
      await fetchDocs();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("确定删除此文档？")) return;
    try {
      await apiFetch(`/api/documents/${docId}`, { method: "DELETE" });
      await fetchDocs();
    } catch (e: any) { setError(e.message); }
  };

  const handleReparse = async (docId: string) => {
    try {
      await apiFetch(`/api/documents/${docId}/reparse`, { method: "POST" });
      setError("重新解析任务已提交");
      setTimeout(fetchDocs, 2000);
    } catch (e: any) { setError(e.message); }
  };

  const viewDocDetail = async (doc: any) => {
    setSelectedDoc(doc);
    setTab("detail");
    try {
      const [blocks, chunks, quality] = await Promise.all([
        apiFetch(`/api/documents/${doc.id}/blocks`),
        apiFetch(`/api/documents/${doc.id}/chunks`),
        apiFetch(`/api/documents/${doc.id}/quality-report`),
      ]);
      setDetailData({ ...doc, blocks: blocks.blocks, chunks: chunks.chunks, quality });
    } catch (e: any) {
      setError(e.message);
    }
  };

  const statusColor = (s: string) => {
    if (s === "completed") return "bg-green-100 text-green-700";
    if (s === "failed") return "bg-red-100 text-red-700";
    if (s === "indexed" || s === "parsed") return "bg-blue-100 text-blue-700";
    return "bg-yellow-100 text-yellow-700";
  };

  if (tab === "detail" && selectedDoc) {
    return (
      <div className="space-y-4">
        <button onClick={() => setTab("list")} className="text-sm text-primary hover:underline">
          ← 返回文档列表
        </button>
        <h2 className="text-xl font-bold">{selectedDoc.filename}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><span className="text-muted-foreground">状态:</span> <span className={`px-2 py-0.5 rounded text-xs ${statusColor(selectedDoc.parse_status)}`}>{selectedDoc.parse_status}</span></div>
          <div><span className="text-muted-foreground">类型:</span> {selectedDoc.file_type}</div>
          <div><span className="text-muted-foreground">大小:</span> {Math.round(selectedDoc.file_size / 1024)}KB</div>
          <div><span className="text-muted-foreground">来源:</span> {selectedDoc.source_type}</div>
        </div>
        <div className="bg-card border rounded-lg p-4">
          <h3 className="font-semibold mb-2">Blocks ({detailData?.blocks?.length || 0})</h3>
          <div className="max-h-64 overflow-auto space-y-1 text-xs">
            {detailData?.blocks?.map((b: any) => (
              <div key={b.id} className="flex gap-2">
                <span className="text-muted-foreground w-16 flex-shrink-0">[{b.block_type}]</span>
                <span className="truncate">{(b.text || "").substring(0, 100)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-card border rounded-lg p-4">
          <h3 className="font-semibold mb-2">Chunks ({detailData?.chunks?.length || 0})</h3>
          <div className="max-h-64 overflow-auto space-y-2 text-xs">
            {detailData?.chunks?.map((c: any) => (
              <div key={c.id} className="border-b pb-2">
                <span className="text-muted-foreground">#{c.chunk_index}</span>
                <p className="line-clamp-2 mt-1">{(c.content || "").substring(0, 200)}</p>
              </div>
            ))}
          </div>
        </div>
        {detailData?.quality && (
          <div className="bg-card border rounded-lg p-4">
            <h3 className="font-semibold mb-2">质量报告</h3>
            <p className="text-sm">
              整体状态: <span className={`font-semibold ${
                detailData.quality.overall_status === "green" ? "text-green-600"
                : detailData.quality.overall_status === "yellow" ? "text-yellow-600"
                : "text-red-600"
              }`}>{detailData.quality.overall_status}</span>
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">文档管理</h1>
        <p className="text-muted-foreground">导入和管理知识库文档</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm p-3 rounded-md bg-red-50 text-red-500">
          <AlertCircle className="h-4 w-4" /> {error}
          <button onClick={() => setError("")} className="ml-auto text-xs">×</button>
        </div>
      )}

      <div className="bg-card rounded-lg border p-4 space-y-3 max-w-lg">
        <select value={kbId} onChange={(e) => setKbId(e.target.value)}
          className="w-full px-3 py-2 border rounded-md text-sm bg-background">
          <option value="">选择知识库</option>
          {kbs.map((kb: any) => (
            <option key={kb.id} value={kb.id}>{kb.name} ({kb.document_count || 0} 文档)</option>
          ))}
        </select>
        <div className="flex flex-wrap gap-2">
          <label className={`flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm cursor-pointer ${!kbId ? "opacity-50 pointer-events-none" : ""}`}>
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {uploading ? "上传中..." : "上传文件"}
            <input type="file" className="hidden" onChange={handleUpload} disabled={!kbId || uploading} />
          </label>
        </div>
      </div>

      <div>
        <h3 className="font-semibold mb-3">文档列表 ({documents.length})</h3>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : documents.length === 0 ? (
          <div className="text-center text-muted-foreground py-8 bg-card rounded-lg border">
            <FileText className="h-10 w-10 mx-auto mb-2 opacity-20" />
            <p className="text-sm">{kbId ? "暂无文档，上传第一个文件" : "请先选择知识库"}</p>
          </div>
        ) : (
          <div className="bg-card rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50">
                <tr className="text-left text-muted-foreground">
                  <th className="p-3">文件名</th>
                  <th className="p-3">类型</th>
                  <th className="p-3">状态</th>
                  <th className="p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc: any) => (
                  <tr key={doc.id} className="border-b last:border-0 hover:bg-muted/50">
                    <td className="p-3">
                      <button onClick={() => viewDocDetail(doc)} className="text-left hover:text-primary">
                        <span className="font-medium">{doc.filename}</span>
                        <br />
                        <span className="text-xs text-muted-foreground">
                          parse: {doc.parse_status} | embed: {doc.embed_status} | index: {doc.index_status}
                        </span>
                      </button>
                    </td>
                    <td className="p-3 text-muted-foreground">{doc.file_type}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${statusColor(doc.parse_status)}`}>
                        {doc.parse_status}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex gap-2">
                        <button onClick={() => viewDocDetail(doc)} title="查看详情"
                          className="text-muted-foreground hover:text-foreground"><Eye className="h-4 w-4" /></button>
                        <button onClick={() => handleReparse(doc.id)} title="重新解析"
                          className="text-muted-foreground hover:text-foreground"><RefreshCw className="h-4 w-4" /></button>
                        <button onClick={() => handleDelete(doc.id)} title="删除"
                          className="text-red-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
