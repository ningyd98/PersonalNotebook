# Personal-KB 架构文档

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                           │
│  Dashboard │ KB管理 │ 文档导入 │ Chat问答 │ 评测                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP / REST API
┌─────────────────────▼───────────────────────────────────────────┐
│                    后端 API (FastAPI)                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │ KB API   │ Doc API  │ Job API  │ Chat API │ Eval API     │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    服务层 (Services)                       │  │
│  │  Connector → Parser → Chunking → Embedding → Qdrant      │  │
│  │  Retrieval → Rerank → EvidencePack → Generation          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    异步任务 (Celery)                             │
│  DetectFileType → ParseToUDR → Chunk → Embed → Index → Check   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    基础设施 (Docker)                             │
│  PostgreSQL │ Redis │ Qdrant │ MinIO │ Nginx                    │
└─────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  Model Gateway (独立服务)                        │
│  Ollama │ vLLM │ OpenAI-compatible │ DashScope                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心数据流

### 文档导入流

```
文件上传/扫描
  → Connector.scan() → FileObject[]
  → ParserRegistry.get_parser() → BaseParser
  → parser.parse() → UnifiedDocument
  → ChunkingService.chunk_udr() → chunks[]
  → EmbeddingService.embed_chunks() → chunks[].embedding
  → QdrantService.upsert_chunks() → qdrant
  → PostgreSQL 写入 blocks/chunks/assets
```

### 音视频导入流

```
音频/视频上传
  → ParserRegistry.get_parser() → AudioParser / VideoParser
  → ffmpeg 音频轨道抽取 (视频)
  → faster-whisper ASR 转写 → transcript blocks (30~90秒分段)
  → ffmpeg 关键帧抽取 (视频, 每 N 秒一帧)
  → OCR / Caption 生成 (预留)
  → 时间轴合并 → video_segment blocks
  → 切片 → 向量索引
```

### RAG 问答流

```
用户问题
  → RetrievalService.retrieve()
    → QueryUnderstanding (query type 分类)
    → EmbeddingService.embed_text()
    → QdrantService.search()
  → RerankService.rerank()
  → EvidencePackBuilder.build()
  → GenerationService.generate()
    → LLM prompt 构造
    → model-gateway /model/chat
  → Citation extraction & verification
  → 返回 answer + citations + trace
```

## 统一文档表示 (UDR)

所有文件解析后先转换为 UnifiedDocument，包含：
- source: 文件来源信息
- metadata: 元数据（标题、作者、标签）
- blocks: 统一文档块（heading/paragraph/table/image/equation/code/transcript/video_segment 等）
- assets: 关联资产（图片/音频/视频/关键帧/附件）
- relations: 文档间关系（Obsidian 双链、LaTeX 引用 \cite）

## Parser 列表

| Parser | 文件类型 | 工具依赖 | 状态 |
|--------|---------|---------|------|
| MarkdownParser | .md | — | ✅ |
| TXTParser | .txt | — | ✅ |
| PDFParser | .pdf | PyMuPDF | ✅ 基础 |
| DOCXParser | .docx | python-docx | ✅ |
| PPTXParser | .pptx | python-pptx | ✅ |
| LaTeXParser | .tex, .latex | — | ✅ |
| AudioParser | .mp3/.wav/.m4a/.aac/.flac/.ogg/.wma | ffmpeg + faster-whisper | ✅ |
| VideoParser | .mp4/.mov/.mkv/.avi/.webm/.flv/.wmv | ffmpeg + faster-whisper | ✅ |
| ImageParser | .jpg/.png/.webp | — | 🔜 Phase 4 |
| XLSXParser | .xlsx | — | 🔜 Phase 4 |
| CodeParser | .py/.js/.ts/.go 等 | — | 🔜 Phase 4 |
| ArchiveParser | .zip/.tar.gz | — | 🔜 Phase 6 |

## Model Gateway Providers

| Provider | 适用模型 | 特点 |
|----------|---------|------|
| Ollama | qwen3:8b, bge-m3 等 | 本地部署，数据不出机器 |
| vLLM | 自托管模型 | 高吞吐推理 |
| OpenAI-compatible | deepseek, gpt-4o 等 | 兼容 OpenAI API 格式 |
| DashScope | qwen, gte-rerank 等 | 阿里云通义千问，Chat/Embedding 走 OpenAI 兼容模式，Rerank 走专用 API |

## 多索引设计

| 索引 | 存储 | 状态 |
|------|------|------|
| 文本向量索引 | Qdrant | ✅ 已实现 |
| 全文索引 (BM25) | PostgreSQL/ES | 🔜 Phase 4 |
| 表格索引 | PostgreSQL | ✅ 已实现 |
| 图片索引 | Qdrant (via OCR text) | 🔜 Phase 4 |
| 时间轴索引 | PostgreSQL (media_segments) | ✅ 已实现 |
| 元数据索引 | PostgreSQL | ✅ 已实现 |
| 图谱索引 | PostgreSQL (document_relations) | 🔜 Phase 6 |

## 项目阶段

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 核心闭环：KB → 文档导入 → 解析 → 向量索引 → RAG问答 | ✅ |
| Phase 1.5 | 完整基础闭环 + 引用溯源 + 会话管理 + 反馈收集 | ✅ |
| Phase 2A | 前端管理台 + Debug Trace + 状态机 + 双缓冲 reindex | ✅ |
| Phase 2B | Flutter App + Pairing 认证 | ✅ |
| Phase 2C | 设备联调与打包 | ✅ |
| Phase 2D | 内测发布与真机验证 | ✅ |
| Phase 2E | 真实设备实测 | ✅ |
| Phase 3 | 多模态解析器 (DOCX/PPTX/LaTeX/Audio/Video) + DashScope Provider + 导出脚本 | ✅ |
| Phase 4 | BM25 混合检索 + Image/XLSX/Code 解析器 + Query Rewriter | 🔜 |
| Phase 5 | 高级 RAG 优化 | 🔜 |
| Phase 6 | Git/URL Connector + Archive 解析器 + 图谱索引 | 🔜 |
