# PersonalNotebook

> 个人本地知识库系统 — 多源数据接入、多模态解析、中文优化 RAG、引用溯源

## 概述

Personal-KB 是一个支持本地/私有化部署的个人知识库系统。Phase 1.5 完成了完整的基础闭环：**创建知识库 → 上传文档 → 异步解析(7步DAG) → 向量索引 → RAG问答 → 引用溯源 → 会话管理 → 反馈收集**。

### 技术栈

| 层       | 技术                                                     |
| -------- | -------------------------------------------------------- |
| 前端     | Next.js 14 + React 18 + TypeScript + Tailwind CSS        |
| 后端     | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + Alembic |
| 异步任务 | Redis + Celery (7步 DAG)                                 |
| 存储     | PostgreSQL 16 + MinIO                                    |
| 向量检索 | Qdrant                                                   |
| 模型服务 | model-gateway (Ollama / vLLM / OpenAI-compatible)        |

### 部署模式

PersonalNotebook 支持两种模式：

| 模式 | 生成模型 | 检索/索引 | 数据隐私 |
|------|---------|----------|---------|
| **Local** | 本地 Ollama (qwen2.5:7b) | 本地 Core | 全本地 |
| **Hybrid** | DeepSeek API (deepseek-v4-flash) | 本地 Core | evidence chunks 发送到 API |

详见 [docs/model.md](docs/model.md)。

### 默认模型

| 模式 | LLM | Embedding | Rerank |
|------|-----|-----------|--------|
| Local | qwen2.5:7b | bge-m3 | qwen3-reranker-0.6b |
| Hybrid | deepseek-v4-flash | text-embedding-3-small | deepseek-v4-flash |

## 环境要求

| 软件           | 最低版本 | 说明                                     |
| -------------- | -------- | ---------------------------------------- |
| Python         | 3.11+    | 后端 + model-gateway                     |
| Node.js        | 18+      | 前端 (Next.js)                           |
| Docker         | 24.0+    | 基础服务 (PostgreSQL/Redis/Qdrant/MinIO) |
| Docker Compose | 2.0+     | 一键启动                                 |
| Ollama         | latest   | 本地 LLM 服务 (可选)                     |

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

### Phase 2A (当前) ✅

- ✅ 前端管理台 7 页面 (Dashboard/KB/Documents/Chat/Debug/Eval/Status)
- ✅ Debug Trace 页 (dense/rerank/EvidencePack/claims 可视化)
- ✅ 系统健康检查 (PG/Qdrant/MinIO/Redis)
- ✅ E2E Smoke Test (scripts/e2e_smoke_test.sh)
- ✅ Qdrant is_active 过滤 + 双缓冲 reindex
- ✅ 文档状态机 + 版本管理
- ✅ Enhanced EvidencePack + 多因子拒答

### Phase 1.7 ✅

- ✅ 状态机 + 双缓冲 reindex + active_version

### Phase 2 (规划)

- DOCX/PPTX/XLSX/LaTeX/Image 解析器
- Query Rewriter + Hybrid Search + BM25

## 故障排查

| 问题                             | 解决                                                         |
| -------------------------------- | ------------------------------------------------------------ |
| `alembic upgrade head` 失败    | 确认 PostgreSQL 运行且 .env 中密码正确                       |
| Qdrant 维度不匹配                | 更新 `QDRANT_VECTOR_SIZE` 匹配 embedding 模型              |
| Celery worker 不启动             | 确认 Redis 运行，`celery -A app.workers.celery_app worker` |
| Chat 返回"未找到可靠依据"        | 确认文档状态为 READY，active_version > 0                     |
| 前端上传失败                     | 检查 MinIO bucket `kb-assets` 是否存在                     |
| `MatchValue(is_active)` 无结果 | 旧数据无 is_active 字段，需 `POST /kbs/{id}/reindex`       |

## E2E 验收

```bash
bash scripts/e2e_smoke_test.sh
```

## Phase 2B — Flutter App 验收

### Flutter App 运行

```bash
cd app/personal_notebook_app
flutter pub get
flutter run -d macos   # macOS
flutter run -d windows # Windows
flutter run -d android # Android (需连接设备)
flutter run -d ios     # iOS (需 macOS + Xcode)
```

### Phase 2B 验收命令

```bash
# Backend
pytest backend/tests/test_pairing.py -q   # 10 tests
bash scripts/ci_check.sh                  # compileall + status check + flutter analyze

# E2E (需 Docker + Core 运行)
bash scripts/app_e2e_check.sh             # 17 steps incl. Bearer auth + 401 checks
```

### Mobile Pairing 流程

1. 桌面端启动 Core: `docker compose up -d`
2. 桌面端 `POST /auth/pair/create` → 获取 token
3. 桌面端生成二维码 `{type, core_base_url, token, tenant_id, expires_at}`
4. 移动端扫码 OR 手动输入 URL + Token
5. 移动端 `POST /auth/pair/verify` 验证
6. 后续请求 `Authorization: Bearer {token}`
7. Token 撤销: `DELETE /auth/devices/{device_id}` (仅 localhost)

### Desktop Runtime Manager

```dart
// app/personal_notebook_app/lib/services/runtime_manager.dart
final rm = RuntimeManager();
await rm.dockerVersion();            // docker --version
await rm.startCore();                // docker compose up -d
await rm.stopCore();                 // docker compose down
await rm.composePs();                // docker compose ps
await rm.composeLogs();              // docker compose logs --tail=200
```

## Phase 2C — 设备联调与打包

### 版本对应

| 组件 | 版本 |
|------|------|
| Flutter App | 0.2.0+2 |
| Backend API | 0.2.0 |

### 桌面端运行

```bash
# macOS / Windows / Linux
cd app/personal_notebook_app
flutter run -d macos     # macOS
flutter run -d windows   # Windows
flutter run -d linux     # Linux (optional)
```

### Android 安装

```bash
cd app/personal_notebook_app
flutter build apk --debug
adb install build/app/outputs/flutter-apk/app-debug.apk
```

### iOS 构建

```bash
cd app/personal_notebook_app
flutter build ios --no-codesign   # 开发调试 (需 Xcode)
# 发布: flutter build ipa --release (需证书)
```

### Pairing 使用流程

1. 桌面端启动 Core: `docker compose up -d`
2. 桌面端 `POST /auth/pair/create` → 获取 token
3. 桌面端生成二维码 `{type, core_base_url, token, tenant_id, expires_at}`
4. 移动端扫码 OR 手动输入 URL + Token
5. 移动端 `POST /auth/pair/verify` 验证
6. 成功后进入 Dashboard，所有请求自动带 Bearer token

### Token 撤销后重新配对

1. App 收到 401 → 自动跳转 PairingScreen
2. Settings → 断开连接 → 清除本地 secure storage
3. 桌面端重新 `POST /auth/pair/create`
4. 重新扫码配对

### Runtime Manager 支持

| 平台 | 支持 |
|------|------|
| macOS / Windows / Linux | ✅ `docker compose up/down/logs/ps` |
| Android / iOS | ❌ 移动端隐藏 Runtime Manager 入口 |

### 常见问题

见 [docs/APP_TROUBLESHOOTING.md](docs/APP_TROUBLESHOOTING.md)

### Phase 2C 验收

```bash
# Backend
bash scripts/ci_check.sh
pytest backend/tests/test_pairing.py -q

# App
cd app/personal_notebook_app && flutter pub get && flutter analyze && flutter test

# Build (macOS)
cd app/personal_notebook_app && flutter build macos --release

# Device smoke test
bash scripts/app_device_smoke_test.sh
```

## Phase 2D — 内测发布与真机验证

### 状态
Flutter App `0.2.0+2`, Backend `0.2.0`。代码/脚本就绪，真机实测待进行。

### 真机验证入口
详见 [release/checklists/](release/checklists/):
- [macOS](release/checklists/MACOS_TEST.md)
- [Android](release/checklists/ANDROID_TEST.md)
- [iOS](release/checklists/IOS_TESTFLIGHT.md)
- [Windows](release/checklists/WINDOWS_TEST.md)

### Android Debug APK
```bash
flutter build apk --debug
adb install build/app/outputs/flutter-apk/app-debug.apk
```

### 网络预检
```bash
bash scripts/network_preflight.sh
```

### 反馈入口
Settings → 反馈问题 → 复制诊断信息 → 提交到 [GitHub Issues](https://github.com/ningyd98/PersonalNotebook/issues/new/choose)

### 文档索引
- [Beta Test Plan](docs/BETA_TEST_PLAN.md)
- [Security & Privacy](docs/SECURITY_PRIVACY.md)
- [User Feedback Template](docs/USER_FEEDBACK_TEMPLATE.md)
- [App Troubleshooting](docs/APP_TROUBLESHOOTING.md)
- [Phase 2C Release](docs/PHASE_2C_RELEASE.md)

### Phase 2D 验收
```bash
bash scripts/phase2d_acceptance_check.sh
```

## Phase 2E — 真实设备实测

### 状态
⚠️ Docker 未安装 (非交互环境)。需手动：

```bash
brew install --cask docker
open -a Docker
docker compose up -d
flutter run -d macos
```

### 测试报告
[docs/PHASE_2E_TEST_REPORT.md](docs/PHASE_2E_TEST_REPORT.md)

### 环境报告
```bash
bash scripts/phase2e_device_test_report.sh
```

### 已验证通过
- ✅ `phase2d_acceptance_check.sh`: 37 passed
- ✅ `app_release_prepare.sh`: passed
- ✅ `flutter test`: All tests passed
- ✅ DiagnosticsService 脱敏

### 阻塞项
- ❌ Docker 安装需 sudo 密码 (非交互环境不可用)
- ❌ `flutter build macos` 超时 (需完整 GUI 会话)
- ❌ Android 真机未连接

### 手动闭环步骤
1. `brew install --cask docker && open -a Docker`
2. `docker compose up -d && curl localhost:8000/health`
3. `flutter run -d macos` → Pairing → KB → Chat → revoke → 诊断脱敏

### 待完成
- ❌ `brew install --cask docker` — Core 前置依赖
- ❌ Android SDK 36 升级 — Flutter 3.44 要求
- ❌ Android 真机连接 — 移动端测试
- ❌ `flutter run -d macos` — 桌面端配对闭环

## 许可证

MIT
