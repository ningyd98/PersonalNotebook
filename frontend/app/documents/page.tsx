"use client";

import { useEffect, useState } from "react";
import {
  Upload, FolderOpen, FileText, Trash2, RefreshCw, Eye,
  Loader2, AlertCircle, Search, Filter, ChevronDown, ChevronUp,
  Image, Music, Video, Table2, FileCode, CheckCircle2, AlertTriangle, XCircle,
  Settings2,
} from "lucide-react";
import { apiFetch, docApi } from "@/lib/api";

type DetailTab = "info" | "blocks" | "chunks" | "assets" | "tables" | "quality";

interface UploadOptions {
  parse_mode: "fast" | "accurate";
  ocr_mode: "auto" | "force" | "disabled";
  multimodal_enhancement: boolean;
  extract_images: boolean;
  image_ocr: boolean;
  audio_transcription: boolean;
  table_structured: boolean;
}

const defaultUploadOptions: UploadOptions = {
  parse_mode: "fast",
  ocr_mode: "auto",
  multimodal_enhancement: true,
  extract_images: true,
  image_ocr: false,
  audio_transcription: false,
  table_structured: true,
};

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
  const [detailTab, setDetailTab] = useState<DetailTab>("info");
  const [blockTypeFilter, setBlockTypeFilter] = useState<string>("all");
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [uploadOptions, setUploadOptions] = useState<UploadOptions>(defaultUploadOptions);
  const [searchQuery, setSearchQuery] = useState("");

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
      // Attach options as JSON
      formData.append("options", JSON.stringify(uploadOptions));
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

  const handleReembed = async (docId: string) => {
    try {
      await docApi.reembed(docId);
      setError("重新嵌入任务已提交");
    } catch (e: any) { setError(e.message); }
  };

  const viewDocDetail = async (doc: any) => {
    setSelectedDoc(doc);
    setTab("detail");
    setDetailTab("info");
    try {
      const [blocksRes, chunksRes, assetsRes, tablesRes, quality] = await Promise.all([
        docApi.blocks(doc.id).catch(() => ({ blocks: [] })),
        docApi.chunks(doc.id).catch(() => ({ chunks: [] })),
        docApi.assets(doc.id).catch(() => ({ assets: [] })),
        docApi.tables(doc.id).catch(() => ({ tables: [] })),
        docApi.qualityReport(doc.id).catch(() => null),
      ]);
      setDetailData({
        ...doc,
        blocks: blocksRes.blocks || [],
        chunks: chunksRes.chunks || [],
        assets: assetsRes.assets || [],
        tables: tablesRes.tables || [],
        quality,
      });
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

  const qualityIcon = (status: string) => {
    if (status === "green") return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    if (status === "yellow") return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
    return <XCircle className="h-5 w-5 text-red-600" />;
  };

  // Block type filter options
  const blockTypes = detailData?.blocks
    ? ["all", ...Array.from(new Set(detailData.blocks.map((b: any) => b.type || b.block_type)))]
    : ["all"];

  const filteredBlocks = detailData?.blocks
    ? blockTypeFilter === "all"
      ? detailData.blocks
      : detailData.blocks.filter((b: any) => (b.type || b.block_type) === blockTypeFilter)
    : [];

  // Filter documents by search
  const filteredDocs = searchQuery
    ? documents.filter((d: any) => d.filename?.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents;

  // Detail tab components
  const renderInfoTab = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="space-y-3">
        <InfoRow label="文件名" value={selectedDoc?.filename} />
        <InfoRow label="文件大小" value={selectedDoc?.file_size ? `${Math.round(selectedDoc.file_size / 1024)} KB` : "-"} />
        <InfoRow label="文件类型" value={selectedDoc?.file_type} />
        <InfoRow label="来源类型" value={selectedDoc?.source_type} />
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground w-24">解析状态</span>
          <span className={`px-2 py-0.5 rounded text-xs ${statusColor(selectedDoc?.parse_status)}`}>
            {selectedDoc?.parse_status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground w-24">嵌入状态</span>
          <span className={`px-2 py-0.5 rounded text-xs ${statusColor(selectedDoc?.embed_status)}`}>
            {selectedDoc?.embed_status}
          </span>
        </div>
        <InfoRow label="内容 Hash" value={selectedDoc?.content_hash || "-"} />
        <InfoRow label="版本号" value={selectedDoc?.version?.toString() || "1"} />
        <InfoRow label="文档 ID" value={selectedDoc?.id} />
      </div>
      <div className="col-span-full flex gap-2 pt-2">
        <button onClick={() => handleReparse(selectedDoc?.id)} className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
          <RefreshCw className="h-3 w-3 inline mr-1" />重新解析
        </button>
        <button onClick={() => handleReembed(selectedDoc?.id)} className="px-3 py-1.5 text-xs border rounded-md hover:bg-accent">
          重新嵌入
        </button>
      </div>
    </div>
  );

  const renderBlocksTab = () => (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">共 {detailData?.blocks?.length || 0} 个 blocks</span>
        <select value={blockTypeFilter} onChange={(e) => setBlockTypeFilter(e.target.value)}
          className="px-2 py-1 border rounded-md text-xs bg-background">
          {blockTypes.map((t: string) => (
            <option key={t} value={t}>{t === "all" ? "全部类型" : t}</option>
          ))}
        </select>
      </div>
      <div className="max-h-[500px] overflow-auto space-y-1">
        {filteredBlocks.map((b: any) => (
          <div key={b.block_id || b.id} className="flex gap-2 py-1.5 px-2 hover:bg-muted/50 rounded text-xs border-b">
            <span className="text-muted-foreground w-24 flex-shrink-0 font-mono">
              [{b.type || b.block_type}]
            </span>
            {b.level != null && (
              <span className="text-blue-600 flex-shrink-0">H{b.level}</span>
            )}
            {b.page != null && (
              <span className="text-green-600 flex-shrink-0">P{b.page}</span>
            )}
            {b.slide != null && (
              <span className="text-purple-600 flex-shrink-0">S{b.slide}</span>
            )}
            {b.sheet_name && (
              <span className="text-orange-600 flex-shrink-0">{b.sheet_name}</span>
            )}
            <span className="truncate flex-1">{(b.text || "").substring(0, 150)}</span>
          </div>
        ))}
        {filteredBlocks.length === 0 && (
          <div className="text-center text-muted-foreground py-6 text-sm">无 blocks 数据</div>
        )}
      </div>
    </div>
  );

  const renderChunksTab = () => (
    <div className="space-y-3">
      <span className="text-sm text-muted-foreground">共 {detailData?.chunks?.length || 0} 个切片</span>
      <div className="max-h-[500px] overflow-auto space-y-2">
        {detailData?.chunks?.map((c: any) => (
          <div key={c.id} className="border rounded-md p-3 text-xs">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-muted-foreground font-mono">#{c.chunk_index ?? c.id?.slice(-4)}</span>
              {c.token_count && <span className="text-blue-600">{c.token_count} tokens</span>}
            </div>
            <p className="whitespace-pre-wrap line-clamp-4 leading-relaxed">
              {(c.content || c.text || "").substring(0, 500)}
            </p>
            {c.metadata && Object.keys(c.metadata).length > 0 && (
              <div className="mt-2 text-muted-foreground">
                {Object.entries(c.metadata).slice(0, 5).map(([k, v]) => (
                  <span key={k} className="mr-3">{k}: {String(v)}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {(!detailData?.chunks || detailData.chunks.length === 0) && (
          <div className="text-center text-muted-foreground py-6 text-sm">无切片数据</div>
        )}
      </div>
    </div>
  );

  const renderAssetsTab = () => (
    <div className="space-y-3">
      <span className="text-sm text-muted-foreground">共 {detailData?.assets?.length || 0} 个资产</span>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {detailData?.assets?.map((a: any) => {
          const Icon = a.asset_type === "image" || a.asset_type === "frame" ? Image
            : a.asset_type === "audio" ? Music
            : a.asset_type === "video" ? Video
            : FileText;
          return (
            <div key={a.asset_id || a.id} className="border rounded-md p-3 text-xs space-y-1">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{a.asset_type}</span>
                <span className="text-muted-foreground">{a.mime_type}</span>
              </div>
              {a.asset_type === "image" && a.asset_uri && (
                <div className="bg-muted/50 rounded p-2 flex items-center justify-center h-24">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={a.asset_uri} alt={a.asset_id} className="max-h-20 object-contain"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                </div>
              )}
              <div className="text-muted-foreground space-y-0.5">
                {a.width && a.height && <div>尺寸: {a.width}×{a.height}</div>}
                {a.duration_seconds != null && <div>时长: {a.duration_seconds.toFixed(1)}s</div>}
                {a.file_size > 0 && <div>大小: {Math.round(a.file_size / 1024)}KB</div>}
              </div>
            </div>
          );
        })}
        {(!detailData?.assets || detailData.assets.length === 0) && (
          <div className="col-span-full text-center text-muted-foreground py-6 text-sm">无资产数据</div>
        )}
      </div>
    </div>
  );

  const renderTablesTab = () => (
    <div className="space-y-3">
      <span className="text-sm text-muted-foreground">共 {detailData?.tables?.length || 0} 个表格</span>
      <div className="max-h-[500px] overflow-auto space-y-4">
        {detailData?.tables?.map((t: any, idx: number) => (
          <div key={idx} className="border rounded-md overflow-hidden">
            <div className="bg-muted/50 px-3 py-2 text-xs font-medium">
              表格 {idx + 1}
              {t.sheet_name && ` — ${t.sheet_name}`}
              {t.slide != null && ` — Slide ${t.slide}`}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                {t.headers && (
                  <thead className="border-b bg-muted/30">
                    <tr>
                      {t.headers.map((h: string, i: number) => (
                        <th key={i} className="px-3 py-2 text-left font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {(t.rows || []).slice(0, 50).map((row: any[], ri: number) => (
                    <tr key={ri} className="border-b last:border-0">
                      {row.map((cell: any, ci: number) => (
                        <td key={ci} className="px-3 py-2 whitespace-nowrap">{String(cell ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                  {(t.rows || []).length > 50 && (
                    <tr>
                      <td colSpan={t.headers?.length || 1} className="px-3 py-2 text-center text-muted-foreground">
                        ...还有 {(t.rows || []).length - 50} 行
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ))}
        {(!detailData?.tables || detailData.tables.length === 0) && (
          <div className="text-center text-muted-foreground py-6 text-sm">无表格数据</div>
        )}
      </div>
    </div>
  );

  const renderQualityTab = () => (
    <div className="space-y-4">
      {detailData?.quality ? (
        <>
          <div className="flex items-center gap-3 p-4 border rounded-lg">
            {qualityIcon(detailData.quality.overall_status)}
            <div>
              <p className="font-medium">整体状态</p>
              <p className="text-sm text-muted-foreground capitalize">{detailData.quality.overall_status}</p>
            </div>
          </div>
          {detailData.quality.checks && (
            <div className="space-y-2">
              {detailData.quality.checks.map((check: any, idx: number) => (
                <div key={idx} className="flex items-center gap-3 p-3 border rounded-md text-sm">
                  {qualityIcon(check.status)}
                  <div className="flex-1">
                    <p className="font-medium">{check.name}</p>
                    {check.message && <p className="text-xs text-muted-foreground">{check.message}</p>}
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    check.status === "green" ? "bg-green-100 text-green-700"
                    : check.status === "yellow" ? "bg-yellow-100 text-yellow-700"
                    : "bg-red-100 text-red-700"
                  }`}>{check.status}</span>
                </div>
              ))}
            </div>
          )}
          {detailData.quality.metrics && (
            <div className="border rounded-lg p-4">
              <h4 className="font-medium mb-2 text-sm">质量指标</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                {Object.entries(detailData.quality.metrics).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-muted-foreground">{key}:</span>{" "}
                    <span className="font-medium">{typeof value === "number" ? value.toFixed(3) : String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-muted-foreground py-8">
          <p className="text-sm">暂无质量报告</p>
          <p className="text-xs mt-1">文档解析完成后将自动生成</p>
        </div>
      )}
    </div>
  );

  const detailTabs: { key: DetailTab; label: string; icon: any }[] = [
    { key: "info", label: "基本信息", icon: FileText },
    { key: "blocks", label: "Blocks", icon: FileCode },
    { key: "chunks", label: "Chunks", icon: Search },
    { key: "assets", label: "Assets", icon: Image },
    { key: "tables", label: "Tables", icon: Table2 },
    { key: "quality", label: "Quality Report", icon: CheckCircle2 },
  ];

  // Detail view
  if (tab === "detail" && selectedDoc) {
    return (
      <div className="space-y-4">
        <button onClick={() => setTab("list")} className="text-sm text-primary hover:underline">
          ← 返回文档列表
        </button>
        <h2 className="text-xl font-bold">{selectedDoc.filename}</h2>

        {/* Tabs */}
        <div className="flex gap-1 border-b">
          {detailTabs.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => setDetailTab(t.key)}
                className={`flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 transition-colors ${
                  detailTab === t.key
                    ? "border-primary text-primary font-medium"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}>
                <Icon className="h-3.5 w-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="bg-card border rounded-lg p-4">
          {detailTab === "info" && renderInfoTab()}
          {detailTab === "blocks" && renderBlocksTab()}
          {detailTab === "chunks" && renderChunksTab()}
          {detailTab === "assets" && renderAssetsTab()}
          {detailTab === "tables" && renderTablesTab()}
          {detailTab === "quality" && renderQualityTab()}
        </div>
      </div>
    );
  }

  // List view
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
          <button onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
            className={`flex items-center gap-1 px-3 py-2 border rounded-md text-sm ${showAdvancedOptions ? "bg-accent" : "hover:bg-accent/50"}`}>
            <Settings2 className="h-4 w-4" />
            高级选项
            {showAdvancedOptions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        </div>

        {/* Advanced upload options */}
        {showAdvancedOptions && (
          <div className="border rounded-md p-3 space-y-3 bg-muted/30">
            <h4 className="text-sm font-medium">解析选项</h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">解析模式</label>
                <select value={uploadOptions.parse_mode}
                  onChange={(e) => setUploadOptions({ ...uploadOptions, parse_mode: e.target.value as "fast" | "accurate" })}
                  className="w-full px-2 py-1.5 border rounded-md text-xs bg-background mt-1">
                  <option value="fast">快速解析</option>
                  <option value="accurate">精准解析</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">OCR 模式</label>
                <select value={uploadOptions.ocr_mode}
                  onChange={(e) => setUploadOptions({ ...uploadOptions, ocr_mode: e.target.value as "auto" | "force" | "disabled" })}
                  className="w-full px-2 py-1.5 border rounded-md text-xs bg-background mt-1">
                  <option value="auto">自动</option>
                  <option value="force">强制 OCR</option>
                  <option value="disabled">禁用 OCR</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <ToggleOption label="多模态增强" checked={uploadOptions.multimodal_enhancement}
                onChange={(v) => setUploadOptions({ ...uploadOptions, multimodal_enhancement: v })} />
              <ToggleOption label="提取图片" checked={uploadOptions.extract_images}
                onChange={(v) => setUploadOptions({ ...uploadOptions, extract_images: v })} />
              <ToggleOption label="图片 OCR" checked={uploadOptions.image_ocr}
                onChange={(v) => setUploadOptions({ ...uploadOptions, image_ocr: v })} />
              <ToggleOption label="音频转写" checked={uploadOptions.audio_transcription}
                onChange={(v) => setUploadOptions({ ...uploadOptions, audio_transcription: v })} />
              <ToggleOption label="表格结构化" checked={uploadOptions.table_structured}
                onChange={(v) => setUploadOptions({ ...uploadOptions, table_structured: v })} />
            </div>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center gap-3 mb-3">
          <h3 className="font-semibold">文档列表 ({filteredDocs.length})</h3>
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文件名..." className="w-full pl-8 pr-3 py-1.5 border rounded-md text-sm bg-background" />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : filteredDocs.length === 0 ? (
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
                {filteredDocs.map((doc: any) => (
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

function InfoRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground w-24">{label}</span>
      <span className="text-sm font-mono break-all">{value || "-"}</span>
    </div>
  );
}

function ToggleOption({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs cursor-pointer">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
        className="rounded border-gray-300" />
      {label}
    </label>
  );
}
