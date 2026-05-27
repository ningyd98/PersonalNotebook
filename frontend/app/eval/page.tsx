"use client";

import { BarChart3, TrendingUp, AlertTriangle, FileText } from "lucide-react";

export default function EvalPage() {
  const metrics = {
    recall5: "—",
    recall10: "—",
    mrr: "—",
    citationAccuracy: "—",
    hallucinationRate: "—",
    totalCases: 0,
    passedCases: 0,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">评测</h1>
        <p className="text-muted-foreground">RAG 系统质量评估</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card rounded-lg border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Recall@5</span>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </div>
          <p className="text-2xl font-bold">{metrics.recall5}</p>
        </div>
        <div className="bg-card rounded-lg border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">MRR</span>
            <BarChart3 className="h-4 w-4 text-green-500" />
          </div>
          <p className="text-2xl font-bold">{metrics.mrr}</p>
        </div>
        <div className="bg-card rounded-lg border p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">引用准确率</span>
            <FileText className="h-4 w-4 text-purple-500" />
          </div>
          <p className="text-2xl font-bold">{metrics.citationAccuracy}</p>
        </div>
      </div>

      <div className="bg-card rounded-lg border p-4">
        <h3 className="font-semibold mb-3">评测概览</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">总用例数</span>
            <p className="font-semibold">{metrics.totalCases}</p>
          </div>
          <div>
            <span className="text-muted-foreground">通过数</span>
            <p className="font-semibold">{metrics.passedCases}</p>
          </div>
          <div>
            <span className="text-muted-foreground">幻觉率</span>
            <p className="font-semibold">{metrics.hallucinationRate}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Recall@10</span>
            <p className="font-semibold">{metrics.recall10}</p>
          </div>
        </div>
      </div>

      <div className="text-center text-muted-foreground py-8 bg-card rounded-lg border">
        <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-20" />
        <p className="text-sm">评测功能将在 Phase 5 完全实现</p>
        <p className="text-xs mt-1">
          当前可导入评测数据集，并通过 POST /api/eval/run 手动运行评测
        </p>
      </div>
    </div>
  );
}
