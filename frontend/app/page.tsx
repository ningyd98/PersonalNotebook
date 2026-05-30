"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen, FileText, Database, MessageSquare, Plus, Upload, ArrowRight,
  CheckCircle, AlertTriangle, XCircle, Clock, Loader2, Activity, Zap, Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch, healthApi } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface DashboardStats {
  kbCount: number;
  docCount: number;
  chunkCount: number;
  convCount: number;
  modelStatus: string;
}

interface Activity {
  id: string;
  action: string;
  target: string;
  time: string;
  icon: React.ReactNode;
}

interface ServiceStatus {
  name: string;
  ok: boolean;
  port: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    kbCount: 0, docCount: 0, chunkCount: 0, convCount: 0, modelStatus: "检查中...",
  });
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      try {
        const kbs = await apiFetch("/api/kbs");
        const kbCount = kbs.total || 0;
        let docCount = 0, chunkCount = 0;
        if (kbs.items) {
          for (const kb of kbs.items) {
            docCount += kb.document_count || 0;
            chunkCount += kb.chunk_count || 0;
          }
        }

        let convCount = 0;
        try {
          const convs = await apiFetch("/api/conversations");
          convCount = convs.total || 0;
        } catch {}

        let modelStatus = "未连接";
        try {
          const ms = await healthApi.modelStatus();
          const okProviders = (ms.providers || []).filter((p: any) => p.status === "ok");
          modelStatus = okProviders.length > 0
            ? `${okProviders.length} 个 provider 可用`
            : "无可用 provider";
        } catch {
          modelStatus = "未连接";
        }

        setStats({ kbCount, docCount, chunkCount, convCount, modelStatus });

        // Check service health
        let backend: any = { status: "error" };
        try { backend = await healthApi.backend(); } catch {}

        setServices([
          { name: "Backend API", ok: backend.status === "ok", port: "8000" },
          { name: "PostgreSQL", ok: backend.postgres === "ok", port: "5432" },
          { name: "Qdrant", ok: backend.qdrant === "ok", port: "6333" },
          { name: "MinIO", ok: backend.minio === "ok", port: "9000" },
          { name: "Redis", ok: backend.redis === "ok", port: "6379" },
          { name: "ModelGateway", ok: modelStatus !== "未连接", port: "8900" },
        ]);
      } catch {
        // silently fail
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const statCards = [
    { label: "知识库", value: stats.kbCount, icon: BookOpen, gradient: "from-blue-500/20 to-blue-600/5", iconColor: "text-blue-500" },
    { label: "文档总数", value: stats.docCount, icon: FileText, gradient: "from-green-500/20 to-green-600/5", iconColor: "text-green-500" },
    { label: "Chunk 数", value: stats.chunkCount, icon: Database, gradient: "from-purple-500/20 to-purple-600/5", iconColor: "text-purple-500" },
    { label: "对话数", value: stats.convCount, icon: MessageSquare, gradient: "from-orange-500/20 to-orange-600/5", iconColor: "text-orange-500" },
  ];

  const quickActions = [
    { label: "创建知识库", icon: Plus, href: "/kb", desc: "新建一个知识库空间" },
    { label: "上传文档", icon: Upload, href: "/documents", desc: "导入文件到知识库" },
    { label: "开始问答", icon: MessageSquare, href: "/chat", desc: "与知识库对话" },
  ];

  const activities: Activity[] = [
    { id: "1", action: "知识库检查", target: `${stats.kbCount} 个知识库在线`, time: "刚刚", icon: <BookOpen className="h-4 w-4 text-blue-500" /> },
    { id: "2", action: "文档索引", target: `共 ${stats.docCount} 个文档`, time: "刚刚", icon: <FileText className="h-4 w-4 text-green-500" /> },
    { id: "3", action: "模型服务", target: stats.modelStatus, time: "实时", icon: <Cpu className="h-4 w-4 text-purple-500" /> },
    { id: "4", action: "对话记录", target: `${stats.convCount} 条对话`, time: "累计", icon: <MessageSquare className="h-4 w-4 text-orange-500" /> },
    { id: "5", action: "向量索引", target: `${stats.chunkCount} 个 Chunk`, time: "累计", icon: <Database className="h-4 w-4 text-indigo-500" /> },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">欢迎回来</h1>
        <p className="text-muted-foreground">PersonalNotebook 系统概览</p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link key={action.label} href={action.href}>
              <Card className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group border-dashed">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{action.label}</p>
                    <p className="text-xs text-muted-foreground">{action.desc}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-1 transition-transform" />
                </div>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label} className="p-5">
              <div className={cn("flex items-center justify-between mb-3")}>
                <span className="text-sm text-muted-foreground">{card.label}</span>
                <div className={cn("p-2 rounded-lg bg-gradient-to-br", card.gradient)}>
                  <Icon className={cn("h-4 w-4", card.iconColor)} />
                </div>
              </div>
              <p className="text-3xl font-bold tracking-tight">{card.value}</p>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            最近动态
          </h3>
          <div className="space-y-3">
            {activities.map((item) => (
              <div key={item.id} className="flex items-start gap-3 text-sm">
                <div className="mt-0.5 p-1.5 rounded-md bg-muted/50">{item.icon}</div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{item.action}</p>
                  <p className="text-muted-foreground text-xs truncate">{item.target}</p>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap">{item.time}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Service Status */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-muted-foreground" />
            系统状态
          </h3>
          <div className="space-y-3">
            {services.map((svc) => (
              <div key={svc.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "h-2 w-2 rounded-full",
                    svc.ok ? "bg-green-500" : "bg-red-500"
                  )} />
                  <span className="font-medium">{svc.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground font-mono">:{svc.port}</span>
                  {svc.ok ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t">
            <p className="text-xs text-muted-foreground">
              模型服务: {stats.modelStatus}
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
