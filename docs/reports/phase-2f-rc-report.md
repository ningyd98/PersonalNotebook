# Phase 2F Release Candidate Report

## 版本

| 组件 | 版本 |
|------|------|
| Flutter App | 0.2.0+2 |
| Backend | 0.2.0 |
| Model Gateway | — |

## 测试日期
2026-05-28

## 测试环境

| 组件 | 版本/状态 |
|------|----------|
| macOS | 26.4.1 darwin-arm64 |
| Flutter | 3.44.0 stable |
| Xcode | 26.5 (Build 17F42) |
| Docker | 29.5.2 |
| Docker Compose | v5.1.3 |
| PostgreSQL | 16 (healthy) |
| Qdrant | latest (healthy) |
| Redis | 7-alpine (healthy) |
| MinIO | latest (healthy) |
| Backend | FastAPI + uvicorn 0.48.0 |
| Celery | 5.6.3 (worker running) |
| Model Gateway | uvicorn running (Ollama 后端不可用) |
| Ollama | 未安装/未运行 |
| Android SDK | 34.0.0 (需 36) |
| Android 真机 | 未连接 |

## 验收结果矩阵

| 验收项 | 状态 | 详情 |
|--------|------|------|
| **Core Services** | ✅ | PG/Qdrant/Redis/MinIO 全部 healthy |
| **Backend /health** | ✅ | `{"status":"ok"}` |
| **安全闭环** | ✅ | 16/16 安全测试通过 |
| **Pairing** | ✅ | create/verify/revoke 全部正常 |
| **Token 存 SHA256** | ✅ | 明文仅返回一次 |
| **KB 创建** | ✅ | |
| **文档上传** | ✅ | |
| **Celery 文档处理** | ✅ | UPLOADED → READY (15s) |
| **Reindex** | ✅ | active_version 更新 |
| **E2E 验收** | **16/17** | Chat citations 因无 Ollama 未通过 |
| **Chat citations** | ❌ | Model Gateway → Ollama 不可用 (503) |
| **macOS App GUI** | ⚠️ | 需完整桌面会话 `flutter run -d macos` |
| **Android APK** | ⚠️ | 需 SDK 36 + 真机 |
| **诊断脱敏** | ✅ | 代码验证通过 |
| **日志脱敏** | ✅ | Backend `_sanitize()` + Flutter DiagnosticsService |

## 仅剩 1 个未完成项

| # | 项目 | 需要 |
|---|------|------|
| 1 | Chat citations | `ollama pull qwen2.5:7b && ollama serve` |
| 2 | macOS App GUI | `flutter run -d macos` (完整桌面会话) |
| 3 | Android APK | SDK 36 + 真机 |

## 执行命令

```bash
# ✅ Phase 2D Acceptance
bash scripts/phase2d_acceptance_check.sh  # 37 passed

# ✅ E2E Smoke
bash scripts/app_e2e_check.sh             # 16/17 passed

# ✅ RC Verify (新)
bash scripts/e2e_rc_verify.sh

# ⚠️ 需要 Ollama
ollama serve && ollama pull qwen2.5:7b
bash scripts/e2e_rc_verify.sh  # → 预期 17/17
```

## 是否建议进入 Phase 3
**建议**：在 Ollama 安装后可进入 Phase 3。安全闭环、文档处理、Token 管理全部就绪，仅 LLM 依赖未满足。

## 子报告
- [Security & Auth](security-auth-report.md) — ✅ 16/16
- [macOS App GUI](app-gui-verify-report.md) — ⚠️ 待测
- [Android APK](android-apk-verify-report.md) — ⚠️ 待测
