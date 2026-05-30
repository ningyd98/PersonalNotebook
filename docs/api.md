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

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 上传的文件 |
| options | JSON string | 否 | 导入选项，JSON 编码字符串 |

**options 参数说明：**

```json
{
  "fast_parse": false,
  "ocr_mode": "auto",
  "multimodal_enhance": false,
  "whisper_model": "medium",
  "language": "zh",
  "keyframe_interval": 10
}
```

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| fast_parse | bool | false | 快速解析模式，仅提取文本，跳过 OCR/ASR |
| ocr_mode | string | "auto" | OCR 模式：auto(自动检测)/force(强制OCR)/skip(跳过) |
| multimodal_enhance | bool | false | 多模态增强：图片 caption + 视频关键帧 + 音频转写 |
| whisper_model | string | "medium" | ASR 模型：tiny/base/small/medium/large |
| language | string | "zh" | ASR 语言代码 |
| keyframe_interval | int | 10 | 视频关键帧抽取间隔（秒） |

**响应：**

```json
{
  "message": "Document uploaded and ingest job created",
  "document_id": "uuid",
  "job_id": "uuid",
  "duplicate": false,
  "parse_status": "pending",
  "status": "UPLOADED",
  "file_hash": "sha256:...",
  "file_size": 12345,
  "mime_type": "application/pdf"
}
```

### POST /api/kbs/{kb_id}/documents/import-folder

从本地目录批量导入。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| folder_path | string | 是 | 本地文件夹路径 |
| recursive | bool | 否 | 是否递归扫描子目录（默认 true） |

### GET /api/documents/{doc_id} — 文档详情

返回文档完整信息，包含 block_count、chunk_count、asset_count、quality_report。

### DELETE /api/documents/{doc_id} — 删除文档（软删除）

### POST /api/documents/{doc_id}/retry — 重试失败文档

### POST /api/documents/{doc_id}/reparse — 重新解析文档

### POST /api/documents/{doc_id}/reembed — 重新嵌入文档

### POST /api/documents/{doc_id}/reindex — 重新索引文档

### GET /api/documents/{doc_id}/blocks — 查看文档 UDR blocks

返回文档解析后的所有 block 列表。

**响应：**

```json
{
  "document_id": "uuid",
  "total": 42,
  "blocks": [
    {
      "id": "uuid",
      "block_type": "heading",
      "text": "第3章 Q-learning",
      "page_number": null,
      "slide_number": null,
      "section_path": "第3章 Q-learning"
    },
    {
      "id": "uuid",
      "block_type": "paragraph",
      "text": "Q-learning 是一种无模型的时序差分控制算法...",
      "page_number": 12,
      "slide_number": null,
      "section_path": "第3章 Q-learning"
    },
    {
      "id": "uuid",
      "block_type": "table",
      "text": "| 参数 | 值 |\n|---|---|\n| α | 0.1 |",
      "page_number": 13,
      "slide_number": null,
      "section_path": "第3章 Q-learning"
    }
  ]
}
```

**block_type 类型说明：**

| 类型 | 说明 |
|------|------|
| heading | 标题 |
| paragraph | 正文段落 |
| table | 表格（含 structured_data） |
| image | 图片 |
| equation | 公式（LaTeX） |
| code | 代码块 |
| annotation | 批注/定理/证明 |
| transcript | 音频转写段落 |
| video_segment | 视频片段（含时间轴） |
| list | 列表项 |
| metadata | 元数据（脚注等） |

### GET /api/documents/{doc_id}/chunks — 查看文档切片结果

**响应：**

```json
{
  "document_id": "uuid",
  "total": 15,
  "chunks": [
    {
      "id": "uuid",
      "chunk_index": 0,
      "content": "Q-learning 是一种无模型的时序差分控制算法...",
      "token_count": 128,
      "embedding_id": "qdrant_point_id"
    }
  ]
}
```

### GET /api/documents/{doc_id}/assets — 查看文档关联资产

返回文档中提取的所有资产（图片、音频、视频、关键帧等）。

**响应：**

```json
{
  "document_id": "uuid",
  "total": 3,
  "assets": [
    {
      "id": "uuid",
      "asset_type": "image",
      "asset_uri": "minio://localhost:9000/parsed_assets/doc_xxx/asset_abc.png",
      "mime_type": "image/png",
      "file_size": 12345,
      "metadata": {"source": "docx_embedded"}
    }
  ]
}
```

### GET /api/documents/{doc_id}/tables — 查看文档表格

返回文档中提取的所有结构化表格。

**响应：**

```json
{
  "document_id": "uuid",
  "total": 2,
  "tables": [
    {
      "id": "uuid",
      "sheet_name": "Sheet1",
      "table_name": null,
      "row_count": 10,
      "col_count": 4
    }
  ]
}
```

### GET /api/documents/{doc_id}/quality-report — 查看解析质量报告

**响应：**

```json
{
  "document_id": "uuid",
  "parse_quality": {
    "block_count": 42,
    "chunk_count": 15,
    "has_text": true,
    "has_tables": true,
    "has_images": true,
    "ocr_applied": false,
    "warnings": []
  },
  "chunk_quality": {
    "chunk_count": 15
  },
  "overall_status": "green"
}
```

**overall_status 说明：**

| 状态 | 含义 |
|------|------|
| green | 解析完成，质量良好 |
| yellow | 部分完成 |
| red | 解析失败 |
| blue | 进行中/等待中 |

### GET /api/chunks/{chunk_id} — 查看 chunk 详情

返回单个 chunk 的完整内容、所属文档信息、元数据等。

### POST /api/kbs/{kb_id}/reindex — 重新索引整个知识库

### GET /api/kbs/{kb_id}/consistency — 检查 PostgreSQL ↔ Qdrant 一致性

**参数：** `dry_run=true`（默认）仅检查，`dry_run=false` 执行修复。

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
  "max_tokens": 2048,
  "api_key": ""
}
```

### POST /model/embed

```json
{
  "model": "bge-m3",
  "texts": ["文本1", "文本2"],
  "api_key": ""
}
```

### POST /model/rerank

```json
{
  "model": "qwen3-reranker-0.6b",
  "query": "问题",
  "documents": ["候选1", "候选2"],
  "api_key": ""
}
```

### POST /model/tokenize

计算文本的 token 数量，用于预估 LLM 调用成本和上下文长度管理。

**请求：**

```json
{
  "text": "需要计算token数量的文本",
  "model": ""
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | string | 是 | 需要计算 token 的文本 |
| model | string | 否 | 模型名称（当前统一使用 cl100k_base 编码） |

**响应：**

```json
{
  "token_count": 42,
  "model": "cl100k_base"
}
```

**说明：**
- 使用 tiktoken 库的 `cl100k_base` 编码器计算 token 数
- 如 tiktoken 不可用，回退到字符数 / 4 的粗略估算
- 适用于任何需要预估 token 数的场景（切片前预估、上下文窗口检查等）

### GET /model/status

返回所有 provider 的状态和可用模型列表。

**响应：**

```json
{
  "providers": [
    {
      "name": "ollama",
      "status": "ok",
      "models": ["qwen3:8b", "bge-m3"],
      "base_url": "http://localhost:11434"
    },
    {
      "name": "dashscope",
      "status": "ok",
      "models": ["qwen-plus", "qwen-turbo"],
      "has_api_key": true,
      "base_url_masked": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    },
    {
      "name": "openai_compatible",
      "status": "ok",
      "models": ["deepseek-v4-flash"],
      "has_api_key": true,
      "base_url_masked": "https://api.deepseek.com/v1"
    }
  ]
}
```

## 导出脚本

项目提供两个导出脚本，用于生成模型微调数据集：

### export_sft_dataset.py

从数据库导出 SFT（Supervised Fine-Tuning）微调数据集。

```bash
# 导出到 stdout
python scripts/export_sft_dataset.py

# 导出到文件
python scripts/export_sft_dataset.py -o datasets/sft/train.jsonl

# 自定义最低评分阈值
python scripts/export_sft_dataset.py -o datasets/sft/train.jsonl --min-rating 4
```

**输出格式：** JSONL，每行一条 instruction/input/output 记录

```json
{
  "instruction": "根据知识库回答问题，并给出引用。",
  "input": "问题：Q-learning是什么？\n资料：Q-learning更新公式...",
  "output": "Q-learning是一种无模型的时序差分控制算法..."
}
```

**数据来源：** conversations + messages + feedback 表，筛选 rating >= min_rating 的高质量对话。

### export_rerank_dataset.py

导出 Reranker 微调数据集。

```bash
python scripts/export_rerank_dataset.py
```

**输出格式：** JSONL，query-positive-negative 三元组

```json
{
  "query": "Q-learning 的更新公式是什么？",
  "positive": "Q-learning 更新公式为 Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]",
  "negative": "蒙特卡洛方法通过完整轨迹估计回报..."
}
```

**输出路径：** `datasets/rerank/rerank_train.jsonl`
