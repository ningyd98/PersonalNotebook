"use client";

import { useEffect, useState } from "react";
import {
  Send, Loader2, FileText, Image, Video, FileCode, Table2,
  AlertCircle, ThumbsUp, ThumbsDown, MessageSquare, Plus,
} from "lucide-react";
import { chatApi, apiFetch } from "@/lib/api";

interface Citation {
  evidence_id: string; source_type: string; document_id: string;
  filename: string; page_number?: number; slide_number?: number;
  sheet_name?: string; cell_range?: string; section_path?: string;
  start_time?: number; end_time?: number; score: number;
  content_preview: string;
}

interface Message {
  id: string; role: "user" | "assistant"; content: string;
  citations?: Citation[]; model_name?: string; latency_ms?: number;
}

function formatTime(seconds?: number): string {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function CitationCard({ citation }: { citation: Citation }) {
  const Icon = citation.source_type === "slide" ? Image
    : citation.source_type === "table" ? Table2
    : citation.source_type === "code" ? FileCode
    : citation.source_type === "video" ? Video : FileText;

  const location = [citation.page_number && `第${citation.page_number}页`,
    citation.slide_number && `第${citation.slide_number}页幻灯片`,
    citation.sheet_name && `Sheet「${citation.sheet_name}」`,
    citation.section_path,
  ].filter(Boolean).join(" · ");

  return (
    <div className="bg-muted/50 rounded-md p-3 space-y-1 text-sm border">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="font-medium text-foreground">{citation.filename}</span>
        <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
          {(citation.score * 100).toFixed(0)}%
        </span>
      </div>
      {location && <p className="text-xs text-muted-foreground">{location}</p>}
      <p className="text-xs text-muted-foreground line-clamp-2">{citation.content_preview}</p>
    </div>
  );
}

export default function ChatPage() {
  const [kbId, setKbId] = useState("");
  const [kbs, setKbs] = useState<any[]>([]);
  const [conversations, setConversations] = useState<any[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load KB list and conversations
  useEffect(() => {
    apiFetch("/api/kbs?page_size=50").then(d => setKbs(d.items || [])).catch(() => {});
    apiFetch("/api/conversations").then(d => setConversations(d.conversations || [])).catch(() => {});
  }, []);

  // Load conversation messages
  const loadConversation = async (id: string) => {
    try {
      const data = await apiFetch(`/api/conversations/${id}`);
      setConvId(id);
      if (data.kb_id) setKbId(data.kb_id);
      setMessages(data.messages?.map((m: any) => ({
        id: m.id, role: m.role, content: m.content,
        citations: m.citations_json,
        model_name: m.model_name, latency_ms: m.latency_ms,
      })) || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSend = async () => {
    if (!question.trim() || !kbId.trim()) return;
    setLoading(true);
    setError("");

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: question };
    setMessages(prev => [...prev, userMsg]);
    setQuestion("");

    try {
      const res = await chatApi.send({
        kb_id: kbId,
        question: userMsg.content,
        top_k: 8,
        use_rerank: true,
        strict_citation: true,
        debug: true,
        conversation_id: convId || undefined,
      });

      if (!convId) {
        setConvId(res.conversation_id);
      }

      const assistantMsg: Message = {
        id: res.message_id || (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        citations: res.citations,
      };
      setMessages(prev => [...prev, assistantMsg]);

      // Refresh conversations list
      apiFetch("/api/conversations").then(d => setConversations(d.conversations || [])).catch(() => {});
    } catch (e: any) {
      setError(e.message || "请求失败");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgId: string, type: string, rating: number) => {
    try {
      await chatApi.feedback(msgId, { rating, error_type: type });
    } catch {}
  };

  return (
    <div className="flex h-[calc(100vh-3rem)] gap-4">
      {/* Conversation Sidebar */}
      <div className="w-56 border-r pr-3 space-y-2 flex-shrink-0 overflow-auto">
        <button onClick={() => { setConvId(null); setMessages([]); }}
          className="flex items-center gap-2 px-3 py-2 w-full text-sm bg-primary text-primary-foreground rounded-md">
          <Plus className="h-4 w-4" /> 新对话
        </button>
        <div className="space-y-1">
          {conversations.map((c: any) => (
            <button key={c.id} onClick={() => loadConversation(c.id)}
              className={`w-full text-left px-3 py-2 rounded-md text-sm truncate ${
                convId === c.id ? "bg-accent" : "hover:bg-accent/50"
              }`}>
              <MessageSquare className="h-3 w-3 inline mr-1" />
              {c.title?.substring(0, 30) || "对话"}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-4 flex items-center gap-3">
          <select value={kbId} onChange={(e) => setKbId(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm bg-background">
            <option value="">选择知识库</option>
            {kbs.map((kb: any) => (
              <option key={kb.id} value={kb.id}>{kb.name} ({kb.document_count || 0} 文档)</option>
            ))}
          </select>
          {!kbId && kbs.length > 0 && (
            <input type="text" value={kbId} onChange={(e) => setKbId(e.target.value)}
              placeholder="或输入 KB UUID" className="px-3 py-2 border rounded-md text-sm bg-background w-48" />
          )}
        </div>

        <div className="flex-1 overflow-auto space-y-4 mb-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground py-12">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>选择知识库并输入问题开始问答</p>
              <p className="text-xs mt-1">回答基于知识库证据，提供引用来源</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`space-y-2 ${msg.role === "user" ? "flex justify-end" : ""}`}>
              <div className={`max-w-[85%] rounded-lg p-4 ${
                msg.role === "user" ? "bg-primary text-primary-foreground ml-auto" : "bg-card border"
              }`}>
                <div className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</div>
              </div>

              {msg.citations && msg.citations.length > 0 && (
                <div className="space-y-2 ml-4">
                  <p className="text-xs font-medium text-muted-foreground">引用来源 ({msg.citations.length})</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {msg.citations.map((c) => <CitationCard key={c.evidence_id} citation={c} />)}
                  </div>
                </div>
              )}

              {msg.role === "assistant" && msg.id && (
                <div className="flex items-center gap-2 ml-4">
                  <button onClick={() => handleFeedback(msg.id, "useful", 4)}
                    className="text-muted-foreground hover:text-green-500 p-1"><ThumbsUp className="h-3.5 w-3.5" /></button>
                  <button onClick={() => handleFeedback(msg.id, "not_useful", 1)}
                    className="text-muted-foreground hover:text-red-500 p-1"><ThumbsDown className="h-3.5 w-3.5" /></button>
                </div>
              )}
            </div>
          ))}

          {error && (
            <div className="flex items-center gap-2 text-red-500 text-sm p-3 bg-red-50 rounded-md">
              <AlertCircle className="h-4 w-4" />{error}
            </div>
          )}
          {loading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm p-3">
              <Loader2 className="h-4 w-4 animate-spin" />正在检索并生成回答...
            </div>
          )}
        </div>

        <div className="border-t pt-4 pb-6">
          <div className="flex gap-2">
            <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="输入问题，例如：Q-learning 和 SARSA 的区别是什么？"
              className="flex-1 px-4 py-3 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={loading} />
            <button onClick={handleSend}
              disabled={loading || !question.trim() || !kbId.trim()}
              className="px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
