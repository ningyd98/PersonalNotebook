# PersonalNotebook 系统简介

PersonalNotebook 是一个本地部署的个人知识库系统，支持 Markdown、PDF、图片、表格等多种格式。

## 核心组件

| 组件 | 用途 | 版本 |
|------|------|------|
| PostgreSQL | 存储文档元数据、用户、会话 | 16 |
| Qdrant | 向量数据库,存储文档切片的 embedding | latest |
| MinIO | 对象存储,保存原始文件和解析产物 | latest |
| Redis | 缓存和 Celery 任务队列 | 7 |
| Celery | 异步处理文档解析、切片、嵌入 | 5.x |
| FastAPI | 后端 API 服务 | 0.100+ |
| Flutter | 跨平台 App 前端 | 3.x |

## RAG 问答流程

文档上传后会经历以下阶段：
1. 上传 (UPLOADED)
2. 解析 (PARSING → PARSED)
3. 切片 (CHUNKING)
4. 嵌入生成 (EMBEDDING)
5. 向量索引 (INDEXING)
6. 就绪 (READY)

索引完成后即可进行 RAG 问答检索。

## 部署模式

### Local 模式
所有数据不离开本机，使用 Ollama 本地模型。

### Hybrid 模式
Core 本地运行，生成使用 DeepSeek API。
