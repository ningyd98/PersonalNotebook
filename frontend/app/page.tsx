"use client";

import { useEffect, useState } from "react";
import {
  BookOpen, FileText, Database, CheckCircle, AlertTriangle,
  Clock, HardDrive, Loader2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DashboardStats {
  kbCount: number;
  docCount: number;
  parsedCount: number;
  failedCount: number;
  chunkCount: number;
  modelStatus: string;
  recentJobs: number;
  recentConversations: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    kbCount: 0, docCount: 0, parsedCount: 0, failedCount: 0,
    chunkCount: 0, modelStatus: "检查中...", recentJobs: 0, recentConversations: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch Kbs
        const kbs = await apiFetch("/api/kbs");
        const kbCount = kbs.total || 0;

        // Aggregate doc stats
        let docCount = 0, parsedCount = 0, failedCount = 0, chunkCount = 0;
        if (kbs.items) {
          for (const kb of kbs.items) {
            docCount += kb.document_count || 0;
            chunkCount += kb.chunk_count || 0;
          }
        }

        // Jobs
        let recentJobs = 0;
        if (kbCount > 0 && kbs.items?.length > 0) {
          try {
            const jobs = await apiFetch(`/api/kbs/${kbs.items[0].id}/jobs?page_size=5`);
            recentJobs = jobs.total || 0;
          } catch {}
        }

        // Conversations
        let recentConversations = 0;
        try {
          const convs = await apiFetch("/api/conversations");
          recentConversations = convs.total || 0;
        } catch {}

        // Model status — use model-gateway directly, not via backend
        let modelStatus = "未连接";
        try {
          const gwUrl = process.env.NEXT_PUBLIC_MODEL_GATEWAY_URL || "http://localhost:8900";
          const resp = await fetch(`${gwUrl}/model/status`);
          const ms = await resp.json();
          const providers = ms.providers || [];
          const okProviders = providers.filter((p: any) => p.status === "ok");
          modelStatus = okProviders.length > 0
            ? `${okProviders.length} 个 provider 可用`
            : "无可用 provider";
        } catch {
          modelStatus = "model-gateway 未连接";
        }

        setStats({
          kbCount, docCount, parsedCount, failedCount, chunkCount,
          modelStatus, recentJobs, recentConversations,
        });
      } catch (e: any) {
        setError(e.message || "无法连接后端服务");
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const cards = [
    { label: "知识库", value: stats.kbCount, icon: BookOpen, color: "text-blue-500" },
    { label: "文档总数", value: stats.docCount, icon: FileText, color: "text-green-500" },
    { label: "Chunk 数", value: stats.chunkCount, icon: Database, color: "text-purple-500" },
    { label: "导入任务", value: stats.recentJobs, icon: Clock, color: "text-orange-500" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">仪表盘</h1>
        <p className="text-muted-foreground">Personal-KB 系统概览</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-500 text-sm p-3 bg-red-50 rounded-md">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="bg-card rounded-lg border p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{card.label}</span>
                <Icon className={`h-5 w-5 ${card.color}`} />
              </div>
              <p className="text-2xl font-bold">{card.value}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-lg border p-4">
          <h3 className="font-semibold mb-3">最近动态</h3>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>📁 知识库：{stats.kbCount} 个</p>
            <p>📄 文档：{stats.docCount} 个 | Chunks：{stats.chunkCount} 个</p>
            <p>💬 最近对话：{stats.recentConversations} 个</p>
            <p>⏳ 待处理任务：{stats.recentJobs} 个</p>
          </div>
        </div>
        <div className="bg-card rounded-lg border p-4">
          <h3 className="font-semibold mb-3">模型服务状态</h3>
          <div className="flex items-center gap-2 mb-2">
            <span className={`h-2.5 w-2.5 rounded-full ${
              stats.modelStatus.includes("未连接") ? "bg-red-400" : "bg-green-400"
            }`} />
            <span className="text-sm">{stats.modelStatus}</span>
          </div>
          <p className="text-sm text-muted-foreground">
            请确保 model-gateway (端口 8900) 和 Ollama 服务正常运行。
          </p>
        </div>
      </div>
    </div>
  );
}
