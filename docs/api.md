# Personal-KB API 文档

## 基础 URL

- 后端 API: `http://localhost:8000/api`
- 模型网关: `http://localhost:8900/model`

## 认证

MVP 阶段使用简化的 JWT 认证。

```
POST /api/auth/login
{
  "username": "admin",
  "password": "password"
}

→ {
  "access_token": "mvp-single-user-token",
  "token_type": "bearer"
}
```

## 知识库 API

### POST /api/kbs — 创建知识库

```json
{
  "name": "我的知识库",
  "description": "个人学习笔记",
  "default_llm": "qwen3:8b",
  "embedding_model": "bge-m3",
  "rerank_model": "qwen3-reranker-0.6b",
  "chunk_strategy": "adaptive"
}
```

### GET /api/kbs — 知识库列表

### GET /api/kbs/{kb_id} — 知识库详情

### PUT /api/kbs/{kb_id} — 更新知识库

### DELETE /api/kbs/{kb_id} — 删除知识库（软删除）

## 文档 API

### POST /api/kbs/{kb_id}/documents/upload
上传单个文档（multipart/form-data）。

### POST /api/kbs/{kb_id}/documents/import-folder
从本地目录批量导入。

### GET /api/documents/{doc_id}/blocks
查看文档的 UDR blocks。

### GET /api/documents/{doc_id}/chunks
查看文档的切片结果。

### GET /api/documents/{doc_id}/quality-report
查看解析质量报告。

## 问答 API

### POST /api/chat

请求：
```json
{
  "kb_id": "uuid",
  "question": "Q-learning 是什么？",
  "retrieval_mode": "auto",
  "top_k": 8,
  "use_rerank": true,
  "strict_citation": true,
  "debug": false
}
```

响应：
```json
{
  "answer": "Q-learning 是一种无模型的时序差分控制算法...",
  "citations": [
    {
      "evidence_id": "ev_000",
      "source_type": "text",
      "filename": "rl_notes.md",
      "section_path": "第3章 > Q-learning",
      "score": 0.92,
      "content_preview": "Q-learning 更新公式..."
    }
  ],
  "trace": {
    "query_type": "text",
    "vector_hits": 40,
    "rerank_top_k": 8,
    "model": "qwen3:8b",
    "latency_ms": 3200
  },
  "conversation_id": "uuid",
  "message_id": "uuid",
  "model": "qwen3:8b"
}
```

### POST /api/messages/{msg_id}/feedback

```json
{
  "rating": 4,
  "comment": "回答准确",
  "error_type": "useful"
}
```

## 模型网关 API

### POST /model/chat

```json
{
  "model": "qwen3:8b",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.2,
  "max_tokens": 2048
}
```

### POST /model/embed

```json
{
  "model": "bge-m3",
  "texts": ["文本1", "文本2"]
}
```

### POST /model/rerank

```json
{
  "model": "qwen3-reranker-0.6b",
  "query": "问题",
  "documents": ["候选1", "候选2"]
}
```

### GET /model/status

返回所有 provider 的状态和可用模型列表。
