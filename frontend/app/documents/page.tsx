"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import {
  Upload, FolderOpen, FileText, Trash2, RefreshCw, Eye,
  Loader2, Search, Filter, ChevronDown, ChevronUp,
  Image, Music, Video, Table2, FileCode, CheckCircle2, AlertTriangle, XCircle,
  Settings2, LayoutGrid, List, ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { docApi, kbApi } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import { useToast } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { FileIcon } from "@/components/ui/file-icon";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";

type DetailTab = "info" | "blocks" | "chunks" | "assets" | "tables" | "quality";
type ViewMode = "grid" | "list";

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

function InfoRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground w-24">{label}</span>
      <span className="text-sm font-mono break-all">{value || "—"}</span>
    </div>
  );
}

function statusVariant(s: string): "default" | "secondary" | "destructive" | "outline" {
  if (s === "completed" || s === "indexed" || s === "parsed") return "default";
  if (s === "failed") return "destructive";
  return "secondary";
}

export default function DocumentsPage() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [kbId, setKbId] = useState("");
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 300);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>("info");
  const [blockTypeFilter, setBlockTypeFilter] = useState<string>("all");
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [uploadOptions, setUploadOptions] = useState<UploadOptions>(defaultUploadOptions);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  const fetchKBs = async () => {
    try {
      const d = await kbApi.list({ page_size: 50 });
      setKbs(d.items || []);
    } catch {}
  };

  const fetchDocs = async () => {
    if (!kbId) return;
    setLoading(true);
    try {
      const d = await docApi.list(kbId, { page_size: 100 });
      setDocuments(d.items || []);
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKBs(); }, []);
  useEffect(() => { if (kbId) fetchDocs(); }, [kbId]);

  const filteredDocs = useMemo(() => {
    if (!debouncedSearch) return documents;
    const q = debouncedSearch.toLowerCase();
    return documents.filter((d: any) => d.filename?.toLowerCase().includes(q));
  }, [documents, debouncedSearch]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0 || !kbId) return;
    setUploading(true);
    setUploadProgress(0);
    try {
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("file", files[i]);
        formData.append("options", JSON.stringify(uploadOptions));
        await docApi.upload(kbId, formData);
        setUploadProgress(Math.round(((i + 1) / files.length) * 100));
      }
      addToast(`${files.length} 个文件上传成功`, "success");
      await fetchDocs();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await docApi.delete(docId);
      addToast("文档已删除", "success");
      await fetchDocs();
    } catch (e: any) {
      addToast(e.message, "error");
    }
  };

  const handleReparse = async (docId: string) => {
    try {
      await docApi.reparse(docId);
      addToast("重新解析任务已提交", "success");
      setTimeout(fetchDocs, 2000);
    } catch (e: any) {
      addToast(e.message, "error");
    }
  };

  const handleReembed = async (docId: string) => {
    try {
      await docApi.reembed(docId);
      addToast("重新嵌入任务已提交", "success");
    } catch (e: any) {
      addToast(e.message, "error");
    }
  };

  const viewDocDetail = async (doc: any) => {
    setSelectedDoc(doc);
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
      addToast(e.message, "error");
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleUpload(e.dataTransfer.files);
  };

  const blockTypes = detailData?.blocks
    ? ["all", ...Array.from(new Set(detailData.blocks.map((b: any) => b.type || b.block_type)))]
    : ["all"];

  const filteredBlocks = detailData?.blocks
    ? blockTypeFilter === "all"
      ? detailData.blocks
      : detailData.blocks.filter((b: any) => (b.type || b.block_type) === blockTypeFilter)
    : [];

  const qualityIcon = (status: string) => {
    if (status === "green") return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    if (status === "yellow") return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
    return <XCircle className="h-5 w-5 text-red-600" />;
  };

  // Detail view
  if (selectedDoc) {
    return (
      <div className="space-y-4 animate-fadeIn">
        <Button variant="ghost" size="sm" onClick={() => setSelectedDoc(null)} className="gap-2">
          <ArrowLeft className="h-4 w-4" /> 返回文档列表
        </Button>
        <h2 className="text-xl font-bold">{selectedDoc.filename}</h2>

        <Tabs value={detailTab} onValueChange={(v) => setDetailTab(v as DetailTab)}>
          <TabsList>
            <TabsTrigger value="info">基本信息</TabsTrigger>
            <TabsTrigger value="blocks">Blocks</TabsTrigger>
            <TabsTrigger value="chunks">Chunks</TabsTrigger>
            <TabsTrigger value="assets">Assets</TabsTrigger>
            <TabsTrigger value="tables">Tables</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
          </TabsList>

          <TabsContent value="info" className="mt-4">
            <Card className="p-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <InfoRow label="文件名" value={selectedDoc.filename} />
                  <InfoRow label="文件大小" value={selectedDoc.file_size ? `${Math.round(selectedDoc.file_size / 1024)} KB` : "—"} />
                  <InfoRow label="文件类型" value={selectedDoc.file_type} />
                  <InfoRow label="来源类型" value={selectedDoc.source_type} />
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground w-24">解析状态</span>
                    <Badge variant={statusVariant(selectedDoc.parse_status)}>{selectedDoc.parse_status}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground w-24">嵌入状态</span>
                    <Badge variant={statusVariant(selectedDoc.embed_status)}>{selectedDoc.embed_status}</Badge>
                  </div>
                  <InfoRow label="版本号" value={selectedDoc.version?.toString() || "1"} />
                  <InfoRow label="文档 ID" value={selectedDoc.id} />
                </div>
                <div className="col-span-full flex gap-2 pt-2">
                  <Button size="sm" variant="outline" onClick={() => handleReparse(selectedDoc.id)} className="gap-1.5">
                    <RefreshCw className="h-3.5 w-3.5" /> 重新解析
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleReembed(selectedDoc.id)}>
                    重新嵌入
                  </Button>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="blocks" className="mt-4">
            <Card className="p-5">
              <div className="flex items-center gap-3 mb-3">
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
                    <span className="text-muted-foreground w-24 flex-shrink-0 font-mono">[{b.type || b.block_type}]</span>
                    {b.level != null && <span className="text-blue-600 flex-shrink-0">H{b.level}</span>}
                    {b.page != null && <span className="text-green-600 flex-shrink-0">P{b.page}</span>}
                    <span className="truncate flex-1">{(b.text || "").substring(0, 150)}</span>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="chunks" className="mt-4">
            <Card className="p-5">
              <span className="text-sm text-muted-foreground mb-3 block">共 {detailData?.chunks?.length || 0} 个切片</span>
              <div className="max-h-[500px] overflow-auto space-y-2">
                {detailData?.chunks?.map((c: any) => (
                  <div key={c.id} className="border rounded-md p-3 text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-muted-foreground font-mono">#{c.chunk_index ?? c.id?.slice(-4)}</span>
                      {c.token_count && <Badge variant="outline" className="text-[10px]">{c.token_count} tokens</Badge>}
                    </div>
                    <p className="whitespace-pre-wrap line-clamp-4 leading-relaxed">{(c.content || c.text || "").substring(0, 500)}</p>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="assets" className="mt-4">
            <Card className="p-5">
              <span className="text-sm text-muted-foreground mb-3 block">共 {detailData?.assets?.length || 0} 个资产</span>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {detailData?.assets?.map((a: any) => {
                  const Icon = a.asset_type === "image" || a.asset_type === "frame" ? Image
                    : a.asset_type === "audio" ? Music : a.asset_type === "video" ? Video : FileText;
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
                    </div>
                  );
                })}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="tables" className="mt-4">
            <Card className="p-5">
              <span className="text-sm text-muted-foreground mb-3 block">共 {detailData?.tables?.length || 0} 个表格</span>
              <div className="max-h-[500px] overflow-auto space-y-4">
                {detailData?.tables?.map((t: any, idx: number) => (
                  <div key={idx} className="border rounded-md overflow-hidden">
                    <div className="bg-muted/50 px-3 py-2 text-xs font-medium">
                      表格 {idx + 1} {t.sheet_name && `— ${t.sheet_name}`}
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        {t.headers && (
                          <thead className="border-b bg-muted/30">
                            <tr>{t.headers.map((h: string, i: number) => <th key={i} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr>
                          </thead>
                        )}
                        <tbody>
                          {(t.rows || []).slice(0, 50).map((row: any[], ri: number) => (
                            <tr key={ri} className="border-b last:border-0">
                              {row.map((cell: any, ci: number) => <td key={ci} className="px-3 py-2 whitespace-nowrap">{String(cell ?? "")}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="quality" className="mt-4">
            <Card className="p-5 space-y-4">
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
                          <Badge variant={check.status === "green" ? "default" : check.status === "yellow" ? "secondary" : "destructive"}>
                            {check.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <EmptyState icon={CheckCircle2} title="暂无质量报告" description="文档解析完成后将自动生成" />
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  // List view
  return (
    <div className="space-y-6 animate-fadeIn">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">文档管理</h1>
        <p className="text-muted-foreground text-sm">导入和管理知识库文档</p>
      </div>

      {/* KB selector + Upload area */}
      <Card className="p-5">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <select value={kbId} onChange={(e) => setKbId(e.target.value)}
              className="px-3 py-2 border rounded-md text-sm bg-background flex-shrink-0">
              <option value="">选择知识库</option>
              {kbs.map((kb: any) => (
                <option key={kb.id} value={kb.id}>{kb.name} ({kb.document_count || 0} 文档)</option>
              ))}
            </select>

            <div className="flex items-center gap-2 ml-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewMode(viewMode === "grid" ? "list" : "grid")}
              >
                {viewMode === "grid" ? <List className="h-4 w-4" /> : <LayoutGrid className="h-4 w-4" />}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                className="gap-1.5"
              >
                <Settings2 className="h-4 w-4" />
                高级选项
                {showAdvancedOptions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </div>
          </div>

          {/* Drag & Drop area */}
          {kbId && (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200",
                isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
              )}
            >
              <Upload className={cn("h-8 w-8 mx-auto mb-3", isDragging ? "text-primary" : "text-muted-foreground")} />
              <p className="text-sm font-medium">
                {uploading ? "上传中..." : "拖拽文件到此处，或点击选择"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">支持多文件上传</p>
              {uploading && <Progress value={uploadProgress} className="mt-3 max-w-xs mx-auto" />}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleUpload(e.target.files)}
                disabled={uploading}
              />
            </div>
          )}

          {/* Advanced options */}
          {showAdvancedOptions && (
            <div className="border rounded-lg p-4 space-y-3 bg-muted/30">
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
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  { key: "multimodal_enhancement" as const, label: "多模态增强" },
                  { key: "extract_images" as const, label: "提取图片" },
                  { key: "image_ocr" as const, label: "图片 OCR" },
                  { key: "audio_transcription" as const, label: "音频转写" },
                  { key: "table_structured" as const, label: "表格结构化" },
                ].map((opt) => (
                  <div key={opt.key} className="flex items-center gap-2">
                    <Switch
                      checked={uploadOptions[opt.key]}
                      onCheckedChange={(v) => setUploadOptions({ ...uploadOptions, [opt.key]: v })}
                    />
                    <span className="text-xs">{opt.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Documents */}
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
          <div className="flex justify-center py-12"><Spinner className="h-8 w-8" /></div>
        ) : filteredDocs.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={kbId ? "暂无文档" : "请先选择知识库"}
            description={kbId ? "上传第一个文件开始使用" : "在上方选择一个知识库"}
          />
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocs.map((doc: any) => (
              <Card key={doc.id} className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group"
                onClick={() => viewDocDetail(doc)}>
                <div className="flex items-start gap-3">
                  <FileIcon filename={doc.filename} className="h-8 w-8 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{doc.filename}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{doc.file_type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Badge variant={statusVariant(doc.parse_status)} className="text-[10px]">
                    {doc.parse_status}
                  </Badge>
                  <Badge variant={statusVariant(doc.embed_status)} className="text-[10px]">
                    {doc.embed_status}
                  </Badge>
                </div>
                <div className="flex items-center gap-1 mt-3 pt-2 border-t">
                  <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs"
                    onClick={(e) => { e.stopPropagation(); handleReparse(doc.id); }}>
                    <RefreshCw className="h-3 w-3" /> 解析
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs text-destructive hover:text-destructive"
                    onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}>
                    <Trash2 className="h-3 w-3" /> 删除
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b bg-muted/50">
                <tr className="text-left text-muted-foreground">
                  <th className="p-3">文件名</th>
                  <th className="p-3">类型</th>
                  <th className="p-3">解析</th>
                  <th className="p-3">嵌入</th>
                  <th className="p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocs.map((doc: any) => (
                  <tr key={doc.id} className="border-b last:border-0 hover:bg-muted/50">
                    <td className="p-3">
                      <button onClick={() => viewDocDetail(doc)} className="text-left hover:text-primary flex items-center gap-2">
                        <FileIcon filename={doc.filename} className="h-4 w-4" />
                        <span className="font-medium">{doc.filename}</span>
                      </button>
                    </td>
                    <td className="p-3 text-muted-foreground">{doc.file_type}</td>
                    <td className="p-3">
                      <Badge variant={statusVariant(doc.parse_status)} className="text-[10px]">{doc.parse_status}</Badge>
                    </td>
                    <td className="p-3">
                      <Badge variant={statusVariant(doc.embed_status)} className="text-[10px]">{doc.embed_status}</Badge>
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => viewDocDetail(doc)}>
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleReparse(doc.id)}>
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive hover:text-destructive" onClick={() => handleDelete(doc.id)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </div>
  );
}
