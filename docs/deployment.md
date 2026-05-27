# Personal-KB 部署文档

## 环境要求

- **操作系统**: Ubuntu 20.04+ / macOS (开发)
- **Docker**: 24.0+
- **Python**: 3.11+
- **Node.js**: 18+
- **Ollama**: 推荐用于本地模型

## Docker 部署

### 1. 启动基础设施

```bash
cd infra
docker compose up -d
```

### 2. 验证服务

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

### 3. 启动应用服务

见 README.md 快速开始章节。

## NAS 挂载

```bash
# 挂载 NAS 到服务器
sudo mount -t nfs 192.168.1.100:/volume1/knowledge /mnt/nas

# 或使用 CIFS/SMB
sudo mount -t cifs //192.168.1.100/knowledge /mnt/nas -o username=user,password=pass
```

## 环境变量配置

详见 `.env.example`，关键配置项：

- `DATABASE_URL`: PostgreSQL 连接字符串
- `MODEL_GATEWAY_URL`: 模型网关地址
- `QDRANT_VECTOR_SIZE`: 向量维度（需与 embedding 模型匹配）
- `MINIO_*`: MinIO 对象存储配置

## 生产部署建议

1. 使用 Nginx 反向代理统一入口
2. 启用 PostgreSQL WAL 归档
3. 定期备份 PostgreSQL + Qdrant + MinIO
4. 设置 systemd 守护进程
5. 配置防火墙仅开放 80/443 端口
