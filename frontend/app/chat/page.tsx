"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Send, Loader2, FileText, Image, Video, FileCode, Table2,
  ThumbsUp, ThumbsDown, MessageSquare, Plus, PanelLeftClose, PanelLeft,
  ChevronDown, AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { chatApi, kbApi } from "@/lib/api";
import { useToast } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

interface Citation {
  evidence_id: string;
  source_type: string;
  document_id: string;
  filename: string;
  page_number?: number;
  slide_number?: number;
  sheet_name?: string;
  cell_range?: string;
  section_path?: string;
  score: number;
  content_preview: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  model_name?: string;
  latency_ms?: number;
  isRefusal?: boolean;
}

function CitationCard({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = citation.source_type === "slide" ? Image
    : citation.source_type === "table" ? Table2
    : citation.source_type === "code" ? FileCode
    : citation.source_type === "video" ? Video : FileText;

  const location = [
    citation.page_number && `第${citation.page_number}页`,
    citation.slide_number && `幻灯片${citation.slide_number}`,
    citation.sheet_name && `Sheet「${citation.sheet_name}」`,
    citation.section_path,
  ].filter(Boolean).join(" · ");

  return (
    <Card className="p-3 text-sm">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="font-medium text-foreground truncate">{citation.filename}</span>
        <Badge variant="outline" className="text-[10px] ml-auto">
          {(citation.score * 100).toFixed(0)}%
        </Badge>
      </div>
      {location && <p className="text-xs text-muted-foreground mt-1">{location}</p>}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-brand hover:underline mt-1"
      >
        {expanded ? "收起" : "展开详情"}
      </button>
      {expanded && (
        <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">
          {citation.content_preview}
        </p>
      )}
    </Card>
  );
}

function ChatMessage({ msg, onFeedback }: { msg: Message; onFeedback: (id: string, rating: number) => void }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3 animate-fadeIn", isUser && "flex-row-reverse")}>
      <div className={cn(
        "max-w-[80%] rounded-2xl px-4 py-3",
        isUser
          ? "bg-brand text-brand-foreground rounded-br-md"
          : "bg-card border rounded-bl-md"
      )}>
        <div className={cn("text-sm whitespace-pre-wrap leading-relaxed", !isUser && "prose-chat")}>
          {msg.content}
        </div>
        {msg.isRefusal && (
          <div className="mt-2 flex items-center gap-2 p-2 bg-orange-500/10 border border-orange-500/20 rounded-lg text-xs text-orange-600 dark:text-orange-400">
            <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
            <span>低置信拒答 — 知识库中未找到足够的可靠证据</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [kbs, setKbs] = useState<any[]>([]);
  const [kbId, setKbId] = useState("");
  const [conversations, setConversations] = useState<any[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, streamingContent, scrollToBottom]);

  useEffect(() => {
    kbApi.list({ page_size: 50 }).then(d => setKbs(d.items || [])).catch(() => {});
    chatApi.conversations().then(d => setConversations(d.conversations || d || [])).catch(() => {});
  }, []);

  const loadConversation = async (id: string) => {
    try {
      const data = await chatApi.getConversation(id);
      setConvId(id);
      if (data.kb_id) setKbId(data.kb_id);
      setMessages(data.messages?.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations_json || m.citations,
        model_name: m.model_name,
        latency_ms: m.latency_ms,
        isRefusal: m.content?.includes("当前知识库未找到可靠依据"),
      })) || []);
    } catch (e: any) {
      addToast(e.message, "error");
    }
  };

  const handleSend = async () => {
    if (!question.trim() || !kbId) return;
    setLoading(true);
    setStreamingContent("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
    };
    setMessages(prev => [...prev, userMsg]);
    setQuestion("");

    // Typing effect simulation
    const fullQuestion = question;
    let displayIdx = 0;

    try {
      const res = await chatApi.send({
        kb_id: kbId,
        question: fullQuestion,
        top_k: 8,
        use_rerank: true,
        strict_citation: true,
        debug: true,
        conversation_id: convId || undefined,
      });

      if (!convId) setConvId(res.conversation_id);

      const isRefusal = res.answer?.includes("当前知识库未找到可靠依据");

      // Simulate streaming effect
      const answerText = res.answer || "";
      const streamInterval = setInterval(() => {
        displayIdx += Math.ceil(answerText.length / 20);
        if (displayIdx >= answerText.length) {
          displayIdx = answerText.length;
          clearInterval(streamInterval);
          setStreamingContent("");

          const assistantMsg: Message = {
            id: res.message_id || (Date.now() + 1).toString(),
            role: "assistant",
            content: answerText,
            citations: res.citations,
            isRefusal,
          };
          setMessages(prev => [...prev, assistantMsg]);
        } else {
          setStreamingContent(answerText.substring(0, displayIdx) + "▍");
        }
      }, 50);

      // Refresh conversations
      chatApi.conversations().then(d => setConversations(d.conversations || d || [])).catch(() => {});
    } catch (e: any) {
      addToast(e.message || "请求失败", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgId: string, rating: number) => {
    try {
      await chatApi.feedback(msgId, { rating, error_type: rating < 3 ? "not_useful" : "useful" });
      addToast(rating >= 3 ? "感谢反馈" : "感谢反馈，我们会改进", "success");
    } catch {}
  };

  const startNewConversation = () => {
    setConvId(null);
    setMessages([]);
    setStreamingContent("");
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-0 animate-fadeIn">
      {/* Conversation Sidebar */}
      {showSidebar && (
        <div className="w-60 border-r flex flex-col flex-shrink-0 mr-4">
          <Button onClick={startNewConversation} className="m-3 gap-2" size="sm">
            <Plus className="h-4 w-4" /> 新对话
          </Button>
          <ScrollArea className="flex-1">
            <div className="space-y-1 px-2 pb-2">
              {conversations.map((c: any) => (
                <button
                  key={c.id}
                  onClick={() => loadConversation(c.id)}
                  className={cn(
                    "w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors",
                    convId === c.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/50 text-muted-foreground"
                  )}
                >
                  <MessageSquare className="h-3 w-3 inline mr-1.5" />
                  {c.title?.substring(0, 30) || "对话"}
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center gap-3 mb-4">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowSidebar(!showSidebar)}>
            {showSidebar ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
          </Button>
          <Select value={kbId} onValueChange={setKbId}>
            <SelectTrigger className="w-64 h-9">
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {kbs.map((kb: any) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name} ({kb.document_count || 0} 文档)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto space-y-4 px-1">
          {messages.length === 0 && !loading && (
            <div className="flex items-center justify-center h-full text-center text-muted-foreground">
              <div>
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p className="font-medium">选择知识库并输入问题开始问答</p>
                <p className="text-xs mt-1">回答基于知识库证据，提供引用来源</p>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id}>
              <ChatMessage msg={msg} onFeedback={handleFeedback} />
              {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 ml-0 space-y-2">
                  <button className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
                    <ChevronDown className="h-3 w-3" />
                    引用来源 ({msg.citations.length})
                  </button>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {msg.citations.map((c) => (
                      <CitationCard key={c.evidence_id} citation={c} />
                    ))}
                  </div>
                </div>
              )}
              {msg.role === "assistant" && msg.id && (
                <div className="flex items-center gap-1 mt-1 ml-0">
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-green-500"
                    onClick={() => handleFeedback(msg.id, 4)}>
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-red-500"
                    onClick={() => handleFeedback(msg.id, 1)}>
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          ))}

          {/* Streaming content */}
          {streamingContent && (
            <div className="flex gap-3">
              <div className="max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3 bg-card border">
                <div className="text-sm whitespace-pre-wrap leading-relaxed prose-chat">
                  {streamingContent}
                </div>
              </div>
            </div>
          )}

          {loading && !streamingContent && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm p-3">
              <Loader2 className="h-4 w-4 animate-spin" /> 正在检索并生成回答...
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t pt-4 mt-4">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="输入问题，例如：Q-learning 和 SARSA 的区别是什么？"
              className="flex-1 px-4 py-3 border rounded-xl bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={loading || !kbId}
            />
            <Button
              onClick={handleSend}
              disabled={loading || !question.trim() || !kbId}
              size="icon"
              className="h-12 w-12 rounded-xl"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            回答基于知识库证据，未经证实的陈述将被标记
          </p>
        </div>
      </div>
    </div>
  );
}
