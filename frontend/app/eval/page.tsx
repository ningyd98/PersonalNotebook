"use client";

import { useEffect, useState } from "react";
import {
  Plus, Trash2, Loader2, Play, FileText, CheckCircle, XCircle,
  BarChart3, Save,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { evalApi, kbApi } from "@/lib/api";
import { useToast } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";

interface EvalSuite {
  id: string;
  name: string;
  description?: string;
  kb_id?: string;
  case_count?: number;
  created_at?: string;
}

const ANSWER_TYPES = [
  { value: "factoid", label: "事实查询" },
  { value: "summary", label: "总结归纳" },
  { value: "comparison", label: "对比" },
  { value: "reasoning", label: "推理" },
  { value: "no_answer", label: "无答案" },
  { value: "table_qa", label: "表格" },
];

export default function EvalPage() {
  const [suites, setSuites] = useState<EvalSuite[]>([]);
  const [kbs, setKbs] = useState<any[]>([]);
  const [selectedKbId, setSelectedKbId] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [runProgress, setRunProgress] = useState<Record<string, number>>({});

  // Create suite dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // Add case dialog
  const [addCaseTarget, setAddCaseTarget] = useState<EvalSuite | null>(null);
  const [caseQuestion, setCaseQuestion] = useState("");
  const [caseAnswer, setCaseAnswer] = useState("");
  const [caseType, setCaseType] = useState("factoid");
  const [addingCase, setAddingCase] = useState(false);

  // Delete dialog
  const [deleteTarget, setDeleteTarget] = useState<EvalSuite | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Result report
  const [reportData, setReportData] = useState<any>(null);

  const { addToast } = useToast();

  const fetchSuites = async () => {
    try {
      const data = await evalApi.listSuites();
      setSuites(data.suites || data || []);
    } catch {}
  };

  const fetchKBs = async () => {
    try {
      const data = await kbApi.list({ page_size: 50 });
      setKbs(data.items || []);
    } catch {}
  };

  useEffect(() => {
    Promise.all([fetchSuites(), fetchKBs()]).finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      await evalApi.createSuite({
        name: createName,
        description: createDesc,
        kb_id: selectedKbId || null,
      });
      setCreateName(""); setCreateDesc("");
      setCreateOpen(false);
      addToast("评测集创建成功", "success");
      await fetchSuites();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setCreating(false);
    }
  };

  const handleAddCase = async () => {
    if (!addCaseTarget || !caseQuestion.trim()) return;
    setAddingCase(true);
    try {
      await evalApi.createCase(addCaseTarget.id, {
        question: caseQuestion,
        reference_answer: caseAnswer,
        answer_type: caseType,
      });
      setCaseQuestion(""); setCaseAnswer("");
      setAddCaseTarget(null);
      addToast("用例添加成功", "success");
      await fetchSuites();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setAddingCase(false);
    }
  };

  const handleRun = async (suiteId: string) => {
    if (!selectedKbId) {
      addToast("请先选择知识库", "error");
      return;
    }
    setRunning((prev) => ({ ...prev, [suiteId]: true }));
    setRunProgress((prev) => ({ ...prev, [suiteId]: 0 }));

    // Simulate progress
    const progressInterval = setInterval(() => {
      setRunProgress((prev) => {
        const current = prev[suiteId] || 0;
        if (current >= 90) return prev;
        return { ...prev, [suiteId]: current + Math.random() * 15 };
      });
    }, 500);

    try {
      const result = await evalApi.startRun({
        dataset_id: suiteId,
        kb_id: selectedKbId,
        top_k: 8,
        use_rerank: true,
      });
      clearInterval(progressInterval);
      setRunProgress((prev) => ({ ...prev, [suiteId]: 100 }));
      addToast(`评测已提交: ${result.run_id}`, "success");
    } catch (e: any) {
      clearInterval(progressInterval);
      addToast(e.message, "error");
    } finally {
      setTimeout(() => {
        setRunning((prev) => ({ ...prev, [suiteId]: false }));
        setRunProgress((prev) => ({ ...prev, [suiteId]: 0 }));
      }, 1000);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await evalApi.deleteSuite(deleteTarget.id);
      setDeleteTarget(null);
      addToast("评测集已删除", "success");
      await fetchSuites();
    } catch (e: any) {
      addToast(e.message, "error");
    } finally {
      setDeleting(false);
    }
  };

  const handleExportReport = async (suiteId: string) => {
    try {
      const report = await evalApi.getReport(suiteId);
      setReportData(report);
    } catch {
      addToast("评测尚未运行或报告不可用", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">评测管理</h1>
          <p className="text-muted-foreground text-sm">创建评测集、运行评测、查看报告</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" /> 新建评测集
        </Button>
      </div>

      {/* KB selector */}
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">评测知识库:</span>
          <Select value={selectedKbId} onValueChange={setSelectedKbId}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {kbs.map((kb: any) => (
                <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Suites list */}
      {suites.length === 0 ? (
        <EmptyState
          icon={BarChart3}
          title="暂无评测集"
          description="点击上方按钮创建第一个评测集"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {suites.map((suite) => (
            <Card key={suite.id} className="p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-sm">{suite.name}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                    {suite.description || "暂无描述"}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive hover:text-destructive"
                  onClick={() => setDeleteTarget(suite)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>

              <div className="flex items-center gap-2 mb-3">
                <Badge variant="secondary" className="text-xs">
                  {suite.case_count || 0} 用例
                </Badge>
                {suite.kb_id && (
                  <Badge variant="outline" className="text-[10px] font-mono">
                    KB
                  </Badge>
                )}
              </div>

              {running[suite.id] && (
                <div className="mb-3">
                  <Progress value={runProgress[suite.id] || 0} className="h-1.5" />
                  <p className="text-xs text-muted-foreground mt-1">评测运行中...</p>
                </div>
              )}

              <div className="flex items-center gap-2 pt-3 border-t">
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5 text-xs flex-1"
                  onClick={() => setAddCaseTarget(suite)}
                >
                  <Plus className="h-3 w-3" /> 添加用例
                </Button>
                <Button
                  size="sm"
                  className="gap-1.5 text-xs flex-1"
                  onClick={() => handleRun(suite.id)}
                  disabled={running[suite.id] || !selectedKbId}
                  loading={running[suite.id]}
                >
                  <Play className="h-3 w-3" /> 运行
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs"
                  onClick={() => handleExportReport(suite.id)}
                >
                  报告
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Report */}
      {reportData && (
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">评测报告</h3>
            <Button variant="ghost" size="sm" onClick={() => setReportData(null)}>关闭</Button>
          </div>
          <div className="space-y-3">
            {reportData.summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(reportData.summary).map(([key, value]) => (
                  <div key={key} className="text-center p-3 border rounded-lg">
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="text-lg font-bold">
                      {typeof value === "number" ? value.toFixed(3) : String(value)}
                    </p>
                  </div>
                ))}
              </div>
            )}
            <pre className="text-xs font-mono bg-muted/30 p-4 rounded-lg overflow-auto max-h-96">
              {JSON.stringify(reportData, null, 2)}
            </pre>
          </div>
        </Card>
      )}

      {/* Create Suite Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建评测集</DialogTitle>
            <DialogDescription>创建一个评测集来组织测试用例</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium mb-1.5 block">名称</label>
              <Input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="评测集名称" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">描述</label>
              <Input value={createDesc} onChange={(e) => setCreateDesc(e.target.value)} placeholder="描述（可选）" />
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

      {/* Add Case Dialog */}
      <Dialog open={!!addCaseTarget} onOpenChange={(open) => !open && setAddCaseTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加用例到「{addCaseTarget?.name}」</DialogTitle>
            <DialogDescription>添加一个测试问题到评测集</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium mb-1.5 block">问题</label>
              <textarea
                value={caseQuestion}
                onChange={(e) => setCaseQuestion(e.target.value)}
                placeholder="测试问题"
                rows={2}
                className="w-full px-3 py-2 border rounded-md text-sm bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">标准答案（可选）</label>
              <textarea
                value={caseAnswer}
                onChange={(e) => setCaseAnswer(e.target.value)}
                placeholder="参考答案"
                rows={3}
                className="w-full px-3 py-2 border rounded-md text-sm bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">答案类型</label>
              <Select value={caseType} onValueChange={setCaseType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ANSWER_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddCaseTarget(null)}>取消</Button>
            <Button onClick={handleAddCase} disabled={!caseQuestion.trim() || addingCase} loading={addingCase}>
              <Save className="h-4 w-4 mr-2" /> 添加
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
              确定要删除评测集「{deleteTarget?.name}」吗？此操作不可撤销。
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
