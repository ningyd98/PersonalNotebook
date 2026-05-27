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
│  Ollama │ vLLM │ OpenAI-compatible │ DashScope (预留)           │
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
- blocks: 统一文档块（heading/paragraph/table/image/equation/code 等）
- assets: 关联资产（图片/音频/视频/附件）
- relations: 文档间关系（Obsidian 双链、LaTeX 引用）

## 多索引设计

| 索引 | 存储 | 状态 |
|------|------|------|
| 文本向量索引 | Qdrant | ✅ 已实现 |
| 全文索引 (BM25) | PostgreSQL/ES | 🔜 Phase 4 |
| 表格索引 | PostgreSQL | 🔜 Phase 4 |
| 图片索引 | Qdrant (via OCR text) | 🔜 Phase 2 |
| 时间轴索引 | PostgreSQL (media_segments) | 🔜 Phase 3 |
| 元数据索引 | PostgreSQL | ✅ 已实现 |
| 图谱索引 | PostgreSQL (document_relations) | 🔜 Phase 6 |
