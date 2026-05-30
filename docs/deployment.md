# Personal-KB 部署文档

## 环境要求

- **操作系统**: Ubuntu 20.04+ / macOS (开发)
- **Docker**: 24.0+
- **Python**: 3.11+
- **Node.js**: 18+
- **Ollama**: 推荐用于本地模型
- **ffmpeg**: 音视频解析必需（系统 PATH 或通过 FFMPEG_PATH 指定）

## Docker 部署

### 1. 克隆并配置

```bash
git clone <repo-url> personal-kb
cd personal-kb
cp .env.example .env
# 编辑 .env，至少修改 SECRET_KEY 和数据库密码
```

### 2. 启动基础设施

```bash
cd infra
docker compose up -d
```

### 3. 验证服务

```bash
# PostgreSQL
docker exec kb-postgres pg_isready -U kb_user -d personal_kb

# Redis
docker exec kb-redis redis-cli ping

# Qdrant
curl http://localhost:6333/health

# MinIO
curl http://localhost:9000/minio/health/live
```

### 4. 安装 Python 依赖

```bash
# 后端
cd backend
pip install -e .

# Model Gateway
cd ../model-gateway
pip install -e .
cd ..
```

### 5. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 6. 初始化数据库

```bash
cd backend
alembic upgrade head
cd ..
```

### 7. 拉取 Ollama 模型（如果使用 Ollama）

```bash
ollama serve
ollama pull qwen3:8b
ollama pull bge-m3
```

### 8. 启动所有服务

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

## 环境变量配置

详见 `.env.example`，关键配置项：

### 项目配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PROJECT_NAME | Personal-KB | 项目名称 |
| ENVIRONMENT | development | 环境：development/production |
| DEBUG | true | 调试模式 |
| SECRET_KEY | change-me-... | 必须修改为随机字符串 |

### PostgreSQL

| 变量 | 默认值 | 说明 |
|------|--------|------|
| POSTGRES_HOST | localhost | 数据库主机 |
| POSTGRES_PORT | 5432 | 数据库端口 |
| POSTGRES_DB | personal_kb | 数据库名 |
| POSTGRES_USER | kb_user | 数据库用户 |
| POSTGRES_PASSWORD | kb_password | 必须修改 |

### Redis

| 变量 | 默认值 | 说明 |
|------|--------|------|
| REDIS_HOST | localhost | Redis 主机 |
| REDIS_PORT | 6379 | Redis 端口 |
| REDIS_PASSWORD | | Redis 密码 |
| REDIS_DB | 0 | Redis DB 编号 |

### MinIO

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MINIO_ENDPOINT | localhost:9000 | MinIO 端点 |
| MINIO_ACCESS_KEY | minioadmin | 访问密钥 |
| MINIO_SECRET_KEY | minioadmin | 必须修改 |
| MINIO_BUCKET | kb-assets | 存储桶名称 |
| MINIO_SECURE | false | 是否 HTTPS |
| MINIO_PUBLIC_URL | http://localhost:9000 | 公开访问 URL |

### Qdrant

| 变量 | 默认值 | 说明 |
|------|--------|------|
| QDRANT_HOST | localhost | Qdrant 主机 |
| QDRANT_PORT | 6333 | Qdrant 端口 |
| QDRANT_API_KEY | | API 密钥 |
| QDRANT_COLLECTION | kb_chunks | 集合名称 |
| QDRANT_VECTOR_SIZE | 1024 | 向量维度（需与 embedding 模型匹配） |

### Model Gateway

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MODEL_GATEWAY_URL | http://localhost:8900 | 模型网关地址 |
| MODEL_PROVIDER | | 默认 provider：ollama/dashscope/openai_compatible/vllm |
| DEFAULT_LLM | qwen3:8b | 默认 LLM 模型 |
| DEFAULT_EMBEDDING | bge-m3 | 默认嵌入模型 |
| DEFAULT_RERANK | qwen3-reranker-0.6b | 默认重排序模型 |

### DashScope 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DASHSCOPE_API_KEY | | DashScope API 密钥（必填才能使用 DashScope） |
| DASHSCOPE_BASE_URL | https://dashscope.aliyuncs.com/api/v1 | DashScope API 基础 URL |

### OCR / ASR

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PADDLEOCR_LANG | ch | OCR 语言 |
| WHISPER_MODEL | medium | ASR 模型：tiny/base/small/medium/large |
| FFMPEG_PATH | ffmpeg | ffmpeg 可执行文件路径 |

### 切片参数

| 变量 | 默认值 | 说明 |
|------|--------|------|
| CHUNK_SIZE | 800 | 切片最大 token 数 |
| CHUNK_OVERLAP | 120 | 切片重叠 token 数 |
| VECTOR_TOP_K | 40 | 向量检索返回数 |
| BM25_TOP_K | 40 | BM25 检索返回数 |
| RERANK_TOP_K | 8 | 重排序后保留数 |
| MAX_CONTEXT_TOKENS | 6000 | LLM 上下文最大 token 数 |

### JWT

| 变量 | 默认值 | 说明 |
|------|--------|------|
| JWT_SECRET_KEY | change-me-jwt-secret | 必须修改 |
| JWT_ALGORITHM | HS256 | JWT 算法 |
| JWT_EXPIRE_MINUTES | 1440 | Token 过期时间（分钟） |

## NAS 挂载

```bash
# 挂载 NAS 到服务器
sudo mount -t nfs 192.168.1.100:/volume1/knowledge /mnt/nas

# 或使用 CIFS/SMB
sudo mount -t cifs //192.168.1.100/knowledge /mnt/nas -o username=user,password=pass
```

## 音视频解析依赖安装

音视频解析需要额外安装 ffmpeg 和 faster-whisper：

```bash
# macOS
brew install ffmpeg
pip install faster-whisper

# Ubuntu
sudo apt install ffmpeg
pip install faster-whisper

# 验证 ffmpeg
ffmpeg -version
ffprobe -version

# 下载 ASR 模型（首次运行时自动下载，也可预先下载）
python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"
```

## 生产部署建议

1. 使用 Nginx 反向代理统一入口
2. 启用 PostgreSQL WAL 归档
3. 定期备份 PostgreSQL + Qdrant + MinIO
4. 设置 systemd 守护进程
5. 配置防火墙仅开放 80/443 端口
6. 修改所有默认密码和 SECRET_KEY
7. 如使用 DashScope，确保 DASHSCOPE_API_KEY 安全存储
8. 音视频处理建议使用独立 Celery Worker，避免阻塞文本解析任务
