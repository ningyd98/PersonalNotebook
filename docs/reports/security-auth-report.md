# Phase 2F RC Report — Security & Auth

## 测试日期
2026-05-28

## 测试环境

| 组件 | 版本 |
|------|------|
| macOS | 26.4.1 darwin-arm64 |
| Docker | 29.5.2 |
| PostgreSQL | 16 (Docker) |
| Qdrant | latest (Docker) |
| Redis | 7-alpine (Docker) |
| MinIO | latest (Docker) |
| Backend | 0.2.0, FastAPI + uvicorn 0.48.0 |
| Celery | 5.6.3 |

## 安全验收结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 无 Auth → 401 (GET /kbs) | ✅ | HTTP 401 |
| 无 Auth → 401 (POST upload) | ✅ | HTTP 401 |
| 无 Auth → 401 (GET docs) | ✅ | HTTP 401 |
| Pairing Create | ✅ | 返回明文 token 仅一次 |
| Token 存储 | ✅ | DB 仅存 SHA256(token) |
| Pairing Verify | ✅ | 不返回 token_hash_prefix |
| 配对后业务 API | ✅ | Bearer token 可用 |
| Revoke 立即生效 | ✅ | |
| Revoked verify → 401 | ✅ | HTTP 401 |
| Revoked GET /kbs → 401 | ✅ | HTTP 401 |
| Revoked GET docs → 401 | ✅ | HTTP 401 |
| Revoked POST upload → 401 | ✅ | HTTP 401 |
| REQUIRE_PAIR_AUTH=false 绕过 | ✅ | 开发环境可用 |
| ENABLE_RUNTIME_API=false 禁用 | ✅ | /system/runtime/* → 403 |
| /system/runtime/* 非 localhost → 403 | ✅ | IP 检查 |
| 日志脱敏 SECRET/TOKEN/PASSWORD | ✅ | `_sanitize()` regex |
| Flutter DiagnosticsService 脱敏 | ✅ | 大小写不敏感 7 关键词 |

## 结论
**安全闭环全部通过 ✅** — 16/16 安全测试通过。无 token 泄漏、无未授权访问。
