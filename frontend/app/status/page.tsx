"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Server, Database, HardDrive, Radio, Cpu, CheckCircle, XCircle,
  Loader2, RefreshCw, Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { healthApi } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface ServiceInfo {
  name: string;
  icon: React.ElementType;
  ok: boolean;
  port: string;
  responseTime?: number;
  detail?: string;
}

interface ModelProvider {
  name: string;
  status: string;
  models?: string[];
}

export default function StatusPage() {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [modelProviders, setModelProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = useCallback(async () => {
    setRefreshing(true);
    try {
      let backend: any = { status: "error" };
      try { backend = await healthApi.backend(); } catch {}

      let modelGw: any = { status: "error" };
      try { modelGw = await healthApi.modelGateway(); } catch {}

      let modelStatus: any = null;
      try { modelStatus = await healthApi.modelStatus(); } catch {}

      const svcList: ServiceInfo[] = [
        {
          name: "Backend API", icon: Server, ok: backend.status === "ok",
          port: "8000",
          responseTime: backend.response_time_ms,
          detail: backend.version || "",
        },
        {
          name: "Model Gateway", icon: Radio, ok: modelGw.status === "ok",
          port: "8900",
          responseTime: modelGw.response_time_ms,
        },
        {
          name: "PostgreSQL", icon: Database, ok: backend.postgres === "ok",
          port: "5432",
          responseTime: backend.pg_response_ms,
        },
        {
          name: "Qdrant", icon: Database, ok: backend.qdrant === "ok",
          port: "6333",
          responseTime: backend.qdrant_response_ms,
        },
        {
          name: "MinIO", icon: HardDrive, ok: backend.minio === "ok",
          port: "9000",
          responseTime: backend.minio_response_ms,
        },
        {
          name: "Redis", icon: Cpu, ok: backend.redis === "ok",
          port: "6379",
          responseTime: backend.redis_response_ms,
        },
      ];
      setServices(svcList);

      if (modelStatus?.providers) {
        setModelProviders(modelStatus.providers);
      } else {
        setModelProviders([]);
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  // Auto refresh every 30s
  useEffect(() => {
    const timer = setInterval(fetchStatus, 30000);
    return () => clearInterval(timer);
  }, [fetchStatus]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const healthyCount = services.filter((s) => s.ok).length;
  const healthPercent = services.length > 0 ? (healthyCount / services.length) * 100 : 0;

  // Simulated system resource data
  const resources = [
    { name: "CPU 使用率", value: 32, color: "bg-blue-500" },
    { name: "内存使用率", value: 58, color: "bg-purple-500" },
    { name: "磁盘使用率", value: 45, color: "bg-green-500" },
    { name: "网络 I/O", value: 23, color: "bg-orange-500" },
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">系统状态</h1>
          <p className="text-muted-foreground text-sm">服务健康检查与资源监控</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            上次刷新: {lastRefresh.toLocaleTimeString("zh-CN")}
          </span>
          <Button variant="outline" size="sm" onClick={fetchStatus} disabled={refreshing} className="gap-1.5">
            <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
            刷新
          </Button>
        </div>
      </div>

      {/* Health overview */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">整体健康度</span>
          </div>
          <Badge variant={healthyCount === services.length ? "default" : "destructive"}>
            {healthyCount}/{services.length} 正常
          </Badge>
        </div>
        <Progress value={healthPercent} className="h-2" />
        <p className="text-xs text-muted-foreground mt-2">
          自动刷新间隔: 30 秒
        </p>
      </Card>

      {/* Service Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map((svc) => {
          const Icon = svc.icon;
          return (
            <Card key={svc.name} className="p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className={cn(
                    "p-2 rounded-lg",
                    svc.ok ? "bg-green-500/10" : "bg-red-500/10"
                  )}>
                    <Icon className={cn("h-4 w-4", svc.ok ? "text-green-500" : "text-red-500")} />
                  </div>
                  <span className="font-medium text-sm">{svc.name}</span>
                </div>
                {svc.ok ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              <div className="space-y-1.5 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>端口</span>
                  <span className="font-mono">:{svc.port}</span>
                </div>
                {svc.responseTime != null && (
                  <div className="flex justify-between">
                    <span>响应时间</span>
                    <span className="font-mono">{svc.responseTime.toFixed(0)}ms</span>
                  </div>
                )}
                {svc.detail && (
                  <div className="flex justify-between">
                    <span>版本</span>
                    <span className="font-mono">{svc.detail}</span>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Providers */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-muted-foreground" />
            模型服务
          </h3>
          {modelProviders.length === 0 ? (
            <p className="text-sm text-muted-foreground">暂无模型服务信息</p>
          ) : (
            <div className="space-y-3">
              {modelProviders.map((p, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium text-sm">{p.name}</p>
                    {p.models && p.models.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {p.models.map((m, mi) => (
                          <Badge key={mi} variant="outline" className="text-[10px] font-mono">{m}</Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  <Badge variant={p.status === "ok" ? "default" : "destructive"}>
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* System Resources */}
        <Card className="p-5">
          <h3 className="font-semibold mb-4">系统资源</h3>
          <div className="space-y-4">
            {resources.map((r) => (
              <div key={r.name} className="space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{r.name}</span>
                  <span className="font-medium">{r.value}%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all duration-500", r.color)}
                    style={{ width: `${r.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            * 资源数据为模拟展示
          </p>
        </Card>
      </div>
    </div>
  );
}
