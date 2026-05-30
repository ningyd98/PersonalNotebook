"use client";

import { useState, useEffect } from "react";
import {
  Bug, Loader2, ChevronDown, ChevronRight, AlertCircle,
  Search, ArrowRight, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { chatApi, kbApi } from "@/lib/api";
import { useToast } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

interface PipelineStep {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;
}

const pipelineSteps: PipelineStep[] = [
  { id: "query", label: "Query", icon: Search, color: "text-blue-500" },
  { id: "retrieve", label: "Retrieve", icon: Zap, color: "text-green-500" },
  { id: "rerank", label: "Rerank", icon: Bug, color: "text-yellow-500" },
  { id: "generate", label: "Generate", icon: ArrowRight, color: "text-purple-500" },
  { id: "cite", label: "Cite", icon: AlertCircle, color: "text-orange-500" },
];

function JsonBlock({ data, title }: { data: any; title?: string }) {
  const [expanded, setExpanded] = useState(false);
  const json = JSON.stringify(data, null, 2);
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors"
      >
        <span>{title || "JSON"}</span>
        {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>
      {expanded && (
        <pre className="px-3 pb-3 text-xs font-mono overflow-auto max-h-64 bg-muted/30">{json}</pre>
      )}
    </div>
  );
}

function StepSection({
  step,
  count,
  children,
  active,
}: {
  step: PipelineStep;
  count?: number;
  children: React.ReactNode;
  active?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = step.icon;

  return (
    <div className={cn(
      "border rounded-lg transition-all",
      active && "border-primary/50 shadow-sm"
    )}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Icon className={cn("h-4 w-4", step.color)} />
          <span>{step.label}</span>
          {count !== undefined && (
            <Badge variant="secondary" className="text-[10px]">{count}</Badge>
          )}
        </div>
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {expanded && <div className="px-3 pb-3 space-y-2">{children}</div>}
    </div>
  );
}

export default function DebugPage() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [kbId, setKbId] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const { addToast } = useToast();

  useEffect(() => {
    kbApi.list({ page_size: 50 }).then(d => setKbs(d.items || [])).catch(() => {});
  }, []);

  const runDebug = async () => {
    if (!kbId || !question) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await chatApi.debug({
        kb_id: kbId,
        question,
        top_k: 8,
        use_rerank: true,
        strict_citation: true,
      });
      setResult(data);
    } catch (e: any) {
      addToast(e.message, "error");
      setResult({ error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Debug Trace</h1>
        <p className="text-muted-foreground text-sm">完整 RAG 管线可视化调试</p>
      </div>

      {/* Input */}
      <Card className="p-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <Select value={kbId} onValueChange={setKbId}>
            <SelectTrigger className="w-full sm:w-64">
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {kbs.map((kb: any) => (
                <SelectItem key={kb.id} value={kb.id}>{kb.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="输入调试问题"
            className="flex-1 px-3 py-2 border rounded-md text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"
            onKeyDown={(e) => e.key === "Enter" && runDebug()}
          />
          <Button onClick={runDebug} disabled={loading || !kbId || !question} loading={loading}>
            Debug
          </Button>
        </div>
      </Card>

      {result?.error && (
        <div className="flex items-center gap-2 text-destructive text-sm p-3 bg-destructive/10 rounded-lg">
          <AlertCircle className="h-4 w-4" /> {result.error}
        </div>
      )}

      {result && !result.error && (
        <div className="space-y-4">
          {/* Summary */}
          <Card className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground text-xs">查询类型</span>
                <p className="font-semibold">{result.query_type}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-xs">检索结果</span>
                <p className="font-semibold">{result.merged_results_count}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-xs">引用覆盖</span>
                <p className="font-semibold">{(result.citation_coverage * 100).toFixed(0)}%</p>
              </div>
              <div>
                <span className="text-muted-foreground text-xs">延迟</span>
                <p className="font-semibold">{result.latency_ms?.toFixed(0)}ms</p>
              </div>
            </div>
          </Card>

          {/* Pipeline Visualization */}
          <div className="flex items-center justify-center gap-2 py-3">
            {pipelineSteps.map((step, idx) => {
              const Icon = step.icon;
              return (
                <div key={step.id} className="flex items-center gap-2">
                  <div className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium",
                    result ? "border-primary/30 bg-primary/5" : "border-border"
                  )}>
                    <Icon className={cn("h-3.5 w-3.5", step.color)} />
                    {step.label}
                  </div>
                  {idx < pipelineSteps.length - 1 && (
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  )}
                </div>
              );
            })}
          </div>

          {result.refusal_reason && (
            <div className="p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg text-sm text-orange-600 dark:text-orange-400">
              <strong>拒答:</strong> {result.refusal_reason}
            </div>
          )}

          {/* Steps Detail */}
          <StepSection step={pipelineSteps[0]} active>
            <div className="text-xs text-muted-foreground">
              查询类型: <Badge variant="outline" className="text-[10px] font-mono">{result.query_type}</Badge>
            </div>
            <JsonBlock data={{ question, query_type: result.query_type }} title="Query Input" />
          </StepSection>

          <StepSection step={pipelineSteps[1]} count={result.dense_results?.length} active>
            <div className="space-y-2 max-h-64 overflow-auto">
              {result.dense_results?.map((h: any, i: number) => (
                <div key={i} className="border-b pb-2 text-xs">
                  <span className="text-muted-foreground">score={h.score?.toFixed(3)}</span>
                  <p className="line-clamp-2">{h.content}</p>
                </div>
              ))}
            </div>
          </StepSection>

          <StepSection step={pipelineSteps[2]} count={result.reranked_results?.length} active>
            <div className="space-y-2 max-h-64 overflow-auto">
              {result.reranked_results?.map((h: any, i: number) => (
                <div key={i} className="border-b pb-2 text-xs">
                  <span className="text-muted-foreground">rerank_score={h.rerank_score?.toFixed(3)}</span>
                  <p className="line-clamp-2">{h.content}</p>
                </div>
              ))}
            </div>
          </StepSection>

          <StepSection step={pipelineSteps[3]} active>
            <div className="space-y-3 max-h-96 overflow-auto">
              {result.evidence_pack?.evidences?.map((ev: any, i: number) => (
                <div key={i} className="border p-2 rounded text-xs space-y-1">
                  <div className="flex gap-2 flex-wrap">
                    <Badge className="text-[10px]">final={ev.final_score?.toFixed(3)}</Badge>
                    <span className="text-muted-foreground">dense={ev.dense_score?.toFixed(3)}</span>
                    <span className="text-muted-foreground">doc={ev.document_id?.substring(0, 8)}</span>
                  </div>
                  <p className="text-muted-foreground line-clamp-3">{ev.content}</p>
                </div>
              ))}
            </div>
          </StepSection>

          <StepSection step={pipelineSteps[4]} count={result.citations?.length} active>
            <div className="space-y-2 mb-3">
              {result.unsupported_claims?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-destructive mb-1">Unsupported Claims:</p>
                  {result.unsupported_claims.map((c: string, i: number) => (
                    <div key={i} className="bg-destructive/10 p-1.5 rounded text-xs mb-1">{c}</div>
                  ))}
                </div>
              )}
              {result.supported_claims?.map((c: string, i: number) => (
                <div key={i} className="bg-green-500/10 p-1.5 rounded text-xs mb-1">{c}</div>
              ))}
            </div>
            <div className="whitespace-pre-wrap text-sm bg-muted/30 p-3 rounded">{result.answer}</div>
            {result.citations && (
              <JsonBlock data={result.citations} title="Citations JSON" />
            )}
          </StepSection>
        </div>
      )}
    </div>
  );
}
