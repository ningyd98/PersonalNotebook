# Personal-KB

> 个人本地知识库系统 — 多源数据接入、多模态解析、中文优化 RAG、引用溯源

## 概述

Personal-KB 是一个支持本地/私有化部署的个人知识库系统。Phase 1.5 完成了完整的基础闭环：**创建知识库 → 上传文档 → 异步解析(7步DAG) → 向量索引 → RAG问答 → 引用溯源 → 会话管理 → 反馈收集**。

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 14 + React 18 + TypeScript + Tailwind CSS |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Alembic |
| 异步任务 | Redis + Celery (7步 DAG) |
| 存储 | PostgreSQL 16 + MinIO |
| 向量检索 | Qdrant |
| 模型服务 | model-gateway (Ollama / vLLM / OpenAI-compatible) |

### 默认模型建议

| 模型类型 | 推荐模型 | 向量维度 |
|---------|---------|---------|
| LLM | Qwen3-8B-Instruct / Qwen3-14B-Instruct | — |
| Embedding | bge-m3 | 1024 |
| Embedding | Qwen3-Embedding-0.6B | 1024 |
| Rerank | Qwen3-Reranker-0.6B | — |

## 环境要求

| 软件 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.11+ | 后端 + model-gateway |
| Node.js | 18+ | 前端 (Next.js) |
| Docker | 24.0+ | 基础服务 (PostgreSQL/Redis/Qdrant/MinIO) |
| Docker Compose | 2.0+ | 一键启动 |
| Ollama | latest | 本地 LLM 服务 (可选) |

## 从零到问答：完整步骤

### 1. 克隆并配置

```bash
git clone <repo-url> personal-kb
cd personal-kb
cp .env.example .env
# 编辑 .env，至少修改 SECRET_KEY 和数据库密码
```

### 2. 启动基础设施 (Docker)

```bash
cd infra
docker compose up -d

# 验证服务 (等待 10-15 秒让服务就绪)
docker compose ps
# 应该看到 postgres/redis/qdrant/minio/nginx 均为 Up 状态
```

### 3. 安装 Python 依赖

```bash
# 后端
cd backend
pip install -e .

# Model Gateway
cd ../model-gateway
pip install -e .
cd ..
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 5. 初始化数据库

```bash
cd backend
alembic upgrade head
cd ..
```

### 6. 拉取 Ollama 模型 (如果使用 Ollama)

```bash
# 安装 Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen3:8b        # LLM (~5GB)
ollama pull bge-m3          # Embedding (~1.5GB)

# 注意: Reranker 模型 Ollama 可能不原生支持，
# 此时 rerank 会 fallback 到 chat API 模拟打分。
# 如使用 vLLM 或 OpenAI API 则无需此步骤。
```

### 7. 启动所有服务

在 4 个终端窗口中分别运行：

```bash
# 终端 1: Model Gateway (端口 8900)
cd model-gateway
uvicorn main:app --host 0.0.0.0 --port 8900 --reload

# 终端 2: 后端 API (端口 8000)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端 3: Celery Worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# 终端 4: 前端 (端口 3000)
cd frontend
npm run dev
```

### 8. 验证系统

1. 打开浏览器访问 **http://localhost:3000**
2. 检查仪表盘是否显示 model-gateway 状态为"可用"
3. 前往「知识库」页面，创建一个知识库（记录其 UUID）
4. 前往「文档」页面，选择该知识库，上传一个 Markdown/TXT/PDF 文件
5. 等待几秒，刷新文档列表，检查 `parse_status` 是否变为 `completed`
6. 前往「问答」页面，选择知识库，输入问题
7. 查看回答是否包含引用卡片

### 9. 验证 API (curl)

```bash
# 创建知识库
curl -X POST http://localhost:8000/api/kbs \
  -H "Content-Type: application/json" \
  -d '{"name":"测试库","description":"我的知识库"}'

# 上传文档 (需要真实文件)
curl -X POST http://localhost:8000/api/kbs/<KB_ID>/documents/upload \
  -F "file=@/path/to/your/notes.md"

# 查看文档列表
curl http://localhost:8000/api/kbs/<KB_ID>/documents

# 查看任务状态
curl http://localhost:8000/api/kbs/<KB_ID>/jobs

# RAG 问答
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"kb_id":"<KB_ID>","question":"你的问题","strict_citation":true}'

# 查看会话
curl http://localhost:8000/api/conversations

# 提交反馈
curl -X POST http://localhost:8000/api/messages/<MSG_ID>/feedback \
  -H "Content-Type: application/json" \
  -d '{"rating":4,"error_type":"useful"}'
```

## 数据库管理

```bash
# 初始化数据库
cd backend
alembic upgrade head

# 创建新 migration (修改模型后)
alembic revision --autogenerate -m "描述变更"

# 回滚
alembic downgrade -1

# 查看当前版本
alembic current
```

## 测试

```bash
cd backend
pip install -e ".[dev]"

# 基础单元测试
pytest tests/test_basic.py -v

# E2E 集成测试
pytest tests/test_e2e_mvp.py -v

# 全部测试
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Celery Worker

```bash
# 启动 worker
cd backend
celery -A app.workers.celery_app worker --loglevel=info

# 查看任务状态 (通过 API)
curl http://localhost:8000/api/jobs/<JOB_ID>

# Flower 监控 (可选)
pip install flower
celery -A app.workers.celery_app flower
```

## 项目结构

```
personal-kb/
├── frontend/          # Next.js 前端
│   ├── app/           # 页面路由 (Dashboard/KB/Documents/Chat/Eval)
│   ├── components/    # UI 组件 (Sidebar)
│   └── lib/           # API 客户端 + 工具
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # API 路由 (6 组)
│   │   ├── core/      # 配置 (Settings)
│   │   ├── db/        # 数据库会话
│   │   ├── models/    # SQLAlchemy 模型 (15 张表)
│   │   ├── schemas/   # Pydantic 模式
│   │   ├── services/  # 业务服务
│   │   │   ├── connectors/  # 数据源 (Upload/Local/NAS/Obsidian)
│   │   │   ├── parsers/     # 解析器 (Markdown/TXT/PDF/Fallback)
│   │   │   ├── chunking/    # 智能切片
│   │   │   ├── retrieval/   # 多路检索
│   │   │   ├── rerank/      # 重排序 + EvidencePack
│   │   │   └── generation/  # LLM 生成 + 引用验证
│   │   └── workers/   # Celery 任务 (7步 DAG)
│   ├── alembic/       # 数据库迁移
│   └── tests/         # 测试
├── model-gateway/     # 模型网关
│   ├── providers/     # Ollama/vLLM/OpenAI 适配器
│   └── main.py
├── infra/             # Docker Compose + Nginx + PostgreSQL
├── scripts/           # 导入/重建索引/导出数据脚本
├── datasets/          # 评测/微调数据集
└── docs/              # 7 篇技术文档
```

## PyMuPDF (PDF 解析) 说明

PyMuPDF 在 `pyproject.toml` 的依赖中列出。如果安装失败 (常见于 ARM Mac / 某些 Linux 发行版)，不影响系统运行，PDF 文件会自动 fallback 到纯文本兜底解析。

```bash
# 可选：跳过 PyMuPDF 安装
pip install -e ".[dev]" --no-deps
pip install fastapi uvicorn sqlalchemy asyncpg alembic ...  # 手动安装其他依赖
```

## MinIO Bucket 说明

MinIO bucket `kb-assets` 在 docker compose 启动时通过 `minio-create-bucket` 容器自动创建。如需手动创建：

```bash
# 访问 MinIO Console
open http://localhost:9001
# 登录: minioadmin / minioadmin
# 手动创建名为 kb-assets 的 bucket
```

## 开发阶段

### Phase 1.5 (当前) ✅
- ✅ 完整 Celery 7步 DAG (detect→parse→chunk→embed→index→check→complete)
- ✅ 真实文件上传链路 (hash→dedup→MinIO→document→job→Celery)
- ✅ 真实 API 数据库查询 (KB/Document/Job/Conversation/Message)
- ✅ Chat 持久化 (会话管理 + 消息历史)
- ✅ Citation Verification (引用验证 + 低置信度拒答)
- ✅ E2E 集成测试 (7 个测试用例)
- ✅ 前端真实数据接入

### Phase 2 (规划)
- DOCX/PPTX/XLSX/LaTeX/Image 解析器
- 文档详情页多 Tabs
- 解析质量报告可视化

## 许可证

MIT
