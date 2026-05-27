"use client";

import { useState } from "react";
import { Bug, Loader2, ChevronDown, ChevronRight, AlertCircle } from "lucide-react";
import { chatApi, apiFetch } from "@/lib/api";

export default function DebugPage() {
  const [kbId, setKbId] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const runDebug = async () => {
    if (!kbId || !question) return;
    setLoading(true);
    try {
      const data = await apiFetch("/api/chat/debug", {
        method: "POST",
        body: JSON.stringify({ kb_id: kbId, question, top_k: 8, use_rerank: true, strict_citation: true }),
      });
      setResult(data);
    } catch (e: any) { setResult({ error: e.message }); }
    finally { setLoading(false); }
  };

  const toggle = (key: string) => setExpanded(p => ({ ...p, [key]: !p[key] }));
  const Section = ({ title, children, id }: { title: string; children: React.ReactNode; id: string }) => (
    <div className="border rounded-lg">
      <button onClick={() => toggle(id)} className="w-full flex items-center justify-between p-3 text-sm font-medium hover:bg-muted/50">
        {title} {expanded[id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {expanded[id] && <div className="px-3 pb-3">{children}</div>}
    </div>
  );

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      <div><h1 className="text-2xl font-bold">Debug Trace</h1><p className="text-muted-foreground text-sm">完整 RAG 管线可视化</p></div>

      <div className="flex gap-2">
        <input value={kbId} onChange={e => setKbId(e.target.value)} placeholder="知识库 UUID" className="px-3 py-2 border rounded-md text-sm w-64" />
        <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="问题" className="flex-1 px-3 py-2 border rounded-md text-sm" onKeyDown={e => e.key === "Enter" && runDebug()} />
        <button onClick={runDebug} disabled={loading} className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Debug"}</button>
      </div>

      {result?.error && <div className="text-red-500 p-3 bg-red-50 rounded-md flex gap-2"><AlertCircle className="h-4 w-4"/>{result.error}</div>}

      {result && !result.error && (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-4 gap-3 p-3 bg-muted/30 rounded-lg">
            <div><span className="text-muted-foreground">类型:</span> <b>{result.query_type}</b></div>
            <div><span className="text-muted-foreground">向量数:</span> {result.merged_results_count}</div>
            <div><span className="text-muted-foreground">引用覆盖:</span> {(result.citation_coverage * 100).toFixed(0)}%</div>
            <div><span className="text-muted-foreground">延迟:</span> {result.latency_ms?.toFixed(0)}ms</div>
          </div>

          {result.refusal_reason && (
            <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg text-orange-800">
              <b>⚠️ 拒答:</b> {result.refusal_reason}
            </div>
          )}

          <Section id="dense" title={`Dense Results (${result.dense_results?.length || 0})`}>
            <div className="space-y-2 max-h-64 overflow-auto">
              {result.dense_results?.map((h: any, i: number) => <div key={i} className="border-b pb-2 text-xs"><span className="text-muted-foreground">score={h.score?.toFixed(3)}</span><p className="line-clamp-2">{h.content}</p></div>)}
            </div>
          </Section>

          <Section id="reranked" title={`Reranked (${result.reranked_results?.length || 0})`}>
            <div className="space-y-2 max-h-64 overflow-auto">
              {result.reranked_results?.map((h: any, i: number) => <div key={i} className="border-b pb-2 text-xs"><span className="text-muted-foreground">score={h.rerank_score?.toFixed(3)}</span><p className="line-clamp-2">{h.content}</p></div>)}
            </div>
          </Section>

          <Section id="evidence" title={`EvidencePack (${result.evidence_pack?.evidences?.length || 0})`}>
            <div className="space-y-3 max-h-96 overflow-auto">
              {result.evidence_pack?.evidences?.map((ev: any, i: number) => (
                <div key={i} className="border p-2 rounded text-xs space-y-1">
                  <div className="flex gap-2 flex-wrap">
                    <span className="bg-primary/10 px-1 rounded">final={ev.final_score?.toFixed(3)}</span>
                    <span className="text-muted-foreground">dense={ev.dense_score?.toFixed(3)}</span>
                    <span className="text-muted-foreground">doc={ev.document_id?.substring(0,8)}</span>
                    <span className="text-muted-foreground">v{ev.version_id}</span>
                    <span className="text-muted-foreground">chunk={ev.chunk_id?.substring(0,8)}</span>
                  </div>
                  <p className="text-muted-foreground line-clamp-3">{ev.content}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section id="claims" title={`Claims (supported=${result.supported_claims?.length}, unsupported=${result.unsupported_claims?.length})`}>
            {result.unsupported_claims?.length > 0 && (
              <div className="space-y-1 mb-2"><b className="text-red-600">Unsupported:</b>
                {result.unsupported_claims.map((c: string, i: number) => <div key={i} className="bg-red-50 p-1 rounded text-xs">{c}</div>)}
              </div>
            )}
            {result.supported_claims?.map((c: string, i: number) => <div key={i} className="bg-green-50 p-1 rounded text-xs mb-1">{c}</div>)}
          </Section>

          <Section id="answer" title="Answer">
            <pre className="whitespace-pre-wrap text-sm bg-muted/30 p-3 rounded">{result.answer}</pre>
          </Section>

          <Section id="citations" title={`Citations (${result.citations?.length || 0})`}>
            <pre className="text-xs bg-muted/30 p-3 rounded overflow-auto max-h-64">{JSON.stringify(result.citations, null, 2)}</pre>
          </Section>
        </div>
      )}
    </div>
  );
}
