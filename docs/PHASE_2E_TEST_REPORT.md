# Phase 2E Test Report

## 测试摘要

| 项目 | 结果 | 说明 |
|------|------|------|
| macOS App 构建 | ⚠️ 未测 | `flutter build macos` 需完整 GUI 会话 |
| macOS App 运行 | ⚠️ 未测 | 需 `flutter run -d macos` |
| Android 真机 | ❌ 未测 | 无 Android 设备连接 (`adb devices` 为空) |
| iOS no-codesign | ⚠️ 未测 | Xcode 26.5 可用 |
| Windows build | ❌ 未测 | 无 Windows 机器 |
| Core 局域网访问 | ✅ 通过 | Docker 正常, 所有服务健康 |
| Pairing | ✅ 通过 | create + verify 通过 |
| Pairing 401 保护 | ✅ 通过 | 无 token 返回 401 (3 项检查) |
| KB 创建 | ✅ 通过 | |
| 文档上传 | ✅ 通过 | |
| 文档 READY | ✅ 通过 | Celery 正常处理 (parsing → chunking → embedding → indexing) |
| Chat citations | ⚠️ 部分 | 模型网关未运行 (Ollama 不可用)，回答无引用 |
| Reindex | ✅ 通过 | active_version 从 1 更新到 2 |
| Token revoke | ✅ 通过 | 撤消后 3 项 401 检查全部通过 |
| 诊断脱敏 | ✅ 通过 | 代码验证 |
| E2E 总通过 | **16/17** | 仅模型网关相关项未通过 |

## 测试环境

| 环境项 | 值 |
|--------|-----|
| macOS | 26.4.1 (darwin-arm64) |
| Flutter | 3.44.0 stable |
| Xcode | 26.5 (Build 17F42) |
| Docker | 29.5.2 |
| Docker Compose | v5.1.3 |
| PostgreSQL | 16 (Docker, healthy) |
| Qdrant | latest (Docker, healthy) |
| MinIO | latest (Docker, healthy) |
| Redis | 7-alpine (Docker, healthy) |
| Backend | v0.2.0, uvicorn 0.48.0 |
| Celery | worker running |
| 局域网 IP | 192.168.3.107 |
| App Version | 0.2.0+2 |

## 执行命令

```bash
# ✅ 通过
docker compose -f infra/docker-compose.yml up -d
curl http://localhost:8000/health  # {"status":"ok","postgres":"ok","qdrant":"ok","minio":"ok","redis":"ok"}
bash scripts/network_preflight.sh  # 局域网 IP: 192.168.3.107
bash scripts/app_e2e_check.sh      # 16/17 passed

# 🔧 环境修复
python3 -m pip install --break-system-packages fastapi uvicorn sqlalchemy alembic qdrant-client minio redis celery python-frontmatter greenlet
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
celery -A app.workers.celery_app worker &
```

## 真实结果

```
✅ Health: ok (postgres/qdrant/minio/redis all healthy)
✅ Pairing Create + Verify
✅ No auth → 401 (3 checks passed)
✅ KB create + upload
✅ Celery: document UPLOADED → PARSING → PARSED → CHUNKING → EMBEDDING → INDEXING → READY
✅ Reindex: active_version 1 → 2
✅ Revoke + revoked → 401 (3 checks passed)
⚠️ Chat citations: model-gateway not running (no Ollama)
```

## 发现的问题

| 编号 | 严重程度 | 问题 | 状态 |
|------|---------|------|------|
| 1 | P2 | Model gateway / Ollama 未运行 → Chat 无引用 | 需 `ollama serve` |
| 2 | P2 | Flutter 3.44.0 analyze crash | SDK 已知 bug |
| 3 | P2 | Android SDK 34 → 需 36 | APK 未构建 |
| 4 | P3 | 无 Android 真机连接 | 移动端未测 |
| 5 | P3 | Flutter build macOS 超时 (非GUI环境) | 需桌面会话 |

## 已修复问题

| 编号 | 严重程度 | 问题 | 修复 |
|------|---------|------|------|
| 1 | P1 | Docker 未安装 | `brew install --cask docker` → Docker 29.5.2 |
| 2 | P1 | Backend 依赖缺失 | `pip install` greenlet/python-frontmatter/aiofiles |
| 3 | P1 | Celery worker 未启动 | `celery -A app.workers.celery_app worker` |

## 未修复风险

| 风险 | 影响 |
|------|------|
| 无模型网关 | Chat 无 LLM 回答和引用 |
| 无 Android 真机 | 移动端未实测 |
