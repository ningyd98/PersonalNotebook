# PersonalNotebook 项目记忆

## 项目概况
个人知识库RAG系统，支持多源数据接入、多模态解析、中文优化RAG、引用溯源。
- 仓库: https://github.com/ningyd98/PersonalNotebook.git
- 技术栈: FastAPI + Next.js + Flutter + PostgreSQL + Qdrant + MinIO + Redis + Celery

## 当前阶段: Phase 3 已完成 (2026-05-30)

### 已实现的解析器
Markdown, TXT, PDF, Fallback (Phase 1)
DOCX, PPTX, XLSX, LaTeX, Image, Code, Archive, Audio, Video (Phase 3)

### Model Gateway Providers
Ollama, OpenAI-compatible (DeepSeek), vLLM, DashScope (Phase 3)

### 微调数据导出脚本
export_rerank_dataset, export_sft_dataset, export_query_router_dataset, export_table_qa_dataset, export_video_retrieval_dataset, export_ocr_correction_dataset, export_asr_correction_dataset

### 下一步 (Phase 4-6 待实现)
- Query Rewriter + Hybrid Search (BM25/Elasticsearch)
- 表格问答 (Text-to-SQL)
- NAS 定时同步
- Obsidian 双链图谱
- Git 仓库导入
- 全文检索 (Elasticsearch/OpenSearch)
- 备份恢复
- 多用户权限

### 关键架构决策
- 所有解析器继承 BaseParser + ParserRegistry 自动注册
- UDR (UnifiedDocument) 统一中间表示
- 双缓冲 reindex (active_version 切换)
- 文档状态机: UPLOADED→PARSING→PARSED→CHUNKING→EMBEDDING→INDEXING→READY
- 增强证据包 + 多因子拒答引擎 (EnhancedEvidencePack + RefusalEngine)
- Claim级引用验证 (ClaimVerifier, 中文bigram)
