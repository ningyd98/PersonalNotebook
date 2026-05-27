"use client";

import { useEffect, useState } from "react";
import { Plus, BarChart3, Loader2, AlertCircle, Save, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function EvalPage() {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [kbs, setKbs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [kbId, setKbId] = useState("");
  const [message, setMessage] = useState("");
  const [selectedDs, setSelectedDs] = useState<any>(null);
  const [newQuestion, setNewQuestion] = useState("");
  const [newAnswer, setNewAnswer] = useState("");
  const [newAnswerType, setNewAnswerType] = useState("factoid");
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [exportData, setExportData] = useState("");

  useEffect(() => {
    apiFetch("/api/eval/datasets").then(d => setDatasets(d.datasets || d || [])).catch(() => {});
    apiFetch("/api/kbs?page_size=50").then(d => setKbs(d.items || [])).catch(() => {});
    setLoading(false);
  }, []);

  const createDataset = async () => {
    if (!name) return;
    const ds = await apiFetch("/api/eval/datasets", { method: "POST", body: JSON.stringify({ name, description: desc, kb_id: kbId || null }) });
    setDatasets(prev => [...prev, ds]);
    setName(""); setDesc(""); setMessage("评测集创建成功");
  };

  const addCase = async () => {
    if (!selectedDs || !newQuestion) return;
    await apiFetch(`/api/eval/datasets/${selectedDs.id}/cases`, {
      method: "POST", body: JSON.stringify({ question: newQuestion, reference_answer: newAnswer, answer_type: newAnswerType }),
    });
    setNewQuestion(""); setNewAnswer("");
    setMessage("用例添加成功");
  };

  const runEval = async (dsId: string) => {
    if (!kbId) { setMessage("请先选择知识库"); return; }
    setRunning(prev => ({ ...prev, [dsId]: true }));
    try {
      const result = await apiFetch("/api/eval/run", { method: "POST", body: JSON.stringify({ dataset_id: dsId, kb_id: kbId, top_k: 8, use_rerank: true }) });
      setMessage(`评测已提交: ${result.run_id}`);
    } catch (e: any) { setMessage(e.message); }
    finally { setRunning(prev => ({ ...prev, [dsId]: false })); }
  };

  const exportDataset = async (dsId: string) => {
    try {
      const report = await apiFetch(`/api/eval/runs/${dsId}/report`);
      setExportData(JSON.stringify(report, null, 2));
    } catch { setExportData("评测尚未运行或报告不可用"); }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin"/></div>;

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold">评测管理</h1><p className="text-muted-foreground text-sm">EvalSet 管理</p></div>

      {message && <div className="p-3 bg-blue-50 border border-blue-200 rounded text-sm flex gap-2 items-center"><AlertCircle className="h-4 w-4"/>{message}<button onClick={() => setMessage("")} className="ml-auto text-xs">×</button></div>}

      <div className="bg-card border rounded-lg p-4 space-y-3 max-w-lg">
        <h3 className="font-semibold">创建评测集</h3>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="评测集名称" className="w-full px-3 py-2 border rounded-md text-sm" />
        <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="描述（可选）" className="w-full px-3 py-2 border rounded-md text-sm" />
        <button onClick={createDataset} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm"><Plus className="h-4 w-4"/>创建</button>
      </div>

      <div className="bg-card border rounded-lg p-4 space-y-3">
        <h3 className="font-semibold">选择知识库</h3>
        <select value={kbId} onChange={e => setKbId(e.target.value)} className="px-3 py-2 border rounded-md text-sm">
          <option value="">全部</option>
          {kbs.map((kb: any) => <option key={kb.id} value={kb.id}>{kb.name}</option>)}
        </select>
      </div>

      <div className="bg-card border rounded-lg p-4 space-y-2 max-h-96 overflow-auto">
        <h3 className="font-semibold">评测集列表 ({datasets.length})</h3>
        {datasets.map((ds: any) => (
          <div key={ds.id} className="flex items-center justify-between border-b pb-2 text-sm">
            <div>
              <button onClick={() => setSelectedDs(ds)} className="font-medium hover:text-primary">{ds.name}</button>
              <p className="text-xs text-muted-foreground">{ds.description}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => runEval(ds.id)} disabled={running[ds.id]} className="px-3 py-1 bg-blue-500 text-white rounded text-xs">{running[ds.id] ? <Loader2 className="h-3 w-3 animate-spin"/> : "运行"}</button>
              <button onClick={() => exportDataset(ds.id)} className="px-3 py-1 border rounded text-xs">导出</button>
            </div>
          </div>
        ))}
      </div>

      {selectedDs && (
        <div className="bg-card border rounded-lg p-4 space-y-3">
          <h3 className="font-semibold">添加用例到「{selectedDs.name}」</h3>
          <textarea value={newQuestion} onChange={e => setNewQuestion(e.target.value)} placeholder="问题" rows={2} className="w-full px-3 py-2 border rounded-md text-sm" />
          <textarea value={newAnswer} onChange={e => setNewAnswer(e.target.value)} placeholder="标准答案（可选）" rows={3} className="w-full px-3 py-2 border rounded-md text-sm" />
          <select value={newAnswerType} onChange={e => setNewAnswerType(e.target.value)} className="px-3 py-2 border rounded-md text-sm">
            <option value="factoid">事实查询</option><option value="summary">总结归纳</option><option value="comparison">对比</option>
            <option value="reasoning">推理</option><option value="no_answer">无答案</option><option value="table_qa">表格</option>
          </select>
          <button onClick={addCase} className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-md text-sm"><Save className="h-4 w-4"/>添加用例</button>
        </div>
      )}

      {exportData && (
        <div className="bg-card border rounded-lg p-4">
          <h3 className="font-semibold mb-2">导出数据</h3>
          <pre className="text-xs bg-muted/30 p-3 rounded overflow-auto max-h-64">{exportData}</pre>
          <button onClick={() => setExportData("")} className="mt-2 px-3 py-1 border rounded text-xs">关闭</button>
        </div>
      )}
    </div>
  );
}
