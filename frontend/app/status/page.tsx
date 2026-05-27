"use client";

import { useEffect, useState } from "react";
import { Server, Database, HardDrive, Radio, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function StatusPage() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [backend, modelGw] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`).then(r => r.json()).catch(() => ({ status: "error" })),
          fetch(`${process.env.NEXT_PUBLIC_MODEL_GATEWAY_URL || "http://localhost:8900"}/health`).then(r => r.json()).catch(() => ({ status: "error" })),
        ]);
        setHealth({ backend, modelGw });
      } catch { setHealth({ error: "无法连接" }); }
      finally { setLoading(false); }
    }
    fetchAll();
  }, []);

  const StatusBadge = ({ ok }: { ok: boolean }) =>
    ok ? <CheckCircle className="h-5 w-5 text-green-500" /> : <XCircle className="h-5 w-5 text-red-500" />;

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold">系统状态</h1><p className="text-muted-foreground text-sm">服务健康检查</p></div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><Server className="h-4 w-4"/>后端 API</span>
            <StatusBadge ok={health?.backend?.status === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">http://localhost:8000</p>
          <pre className="text-xs bg-muted/30 p-2 rounded overflow-auto max-h-20">{JSON.stringify(health?.backend, null, 2)}</pre>
        </div>

        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><Radio className="h-4 w-4"/>Model Gateway</span>
            <StatusBadge ok={health?.modelGw?.status === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">http://localhost:8900</p>
          <pre className="text-xs bg-muted/30 p-2 rounded overflow-auto max-h-20">{JSON.stringify(health?.modelGw, null, 2)}</pre>
        </div>

        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><Database className="h-4 w-4"/>PostgreSQL</span>
            <StatusBadge ok={health?.backend?.postgres === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">localhost:5432</p>
        </div>

        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><Database className="h-4 w-4"/>Qdrant</span>
            <StatusBadge ok={health?.backend?.qdrant === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">localhost:6333</p>
        </div>

        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><HardDrive className="h-4 w-4"/>MinIO</span>
            <StatusBadge ok={health?.backend?.minio === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">localhost:9000</p>
        </div>

        <div className="bg-card border rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium flex items-center gap-2"><Database className="h-4 w-4"/>Redis</span>
            <StatusBadge ok={health?.backend?.redis === "ok"} />
          </div>
          <p className="text-xs text-muted-foreground">localhost:6379</p>
        </div>
      </div>
    </div>
  );
}
