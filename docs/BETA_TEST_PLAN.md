# Beta Test Plan

## 内测目标
验证 PersonalNotebook 0.2.0+2 在真实设备上的基础可用性：
配对 → KB 管理 → 文档上传 → 问答 → Token 撤销 → 重新配对。

## 内测范围

| 范围 | 说明 |
|------|------|
| 包含 | 配对、KB CRUD、文档上传/索引/状态、Chat 问答+引用、Token 管理、诊断信息 |
| 不包含 | 多模态 OCR/ASR、EvalSet 高级评分、Agent 工作流、多用户 RBAC |

## 参与角色
- 开发者 (Core 部署方)
- 内测用户 1-3 人 (macOS / Android / iOS 各一)

## 测试周期
- 第一轮: 2026-05-28 ~ 2026-06-04 (配对 + KB + Chat)
- 第二轮: 2026-06-05 ~ 2026-06-11 (全平台 + 反馈整改)

## 测试环境

| 组件 | 要求 |
|------|------|
| Core | Docker Compose 或手动启动; 监听 0.0.0.0:8000 |
| 数据库 | PostgreSQL + Qdrant + MinIO + Redis (Docker) |
| 网络 | Core 与移动设备在同一局域网 |

## 测试任务

1. 下载/构建 App
2. 获取配对 Token
3. 完成配对
4. 创建知识库
5. 上传文档 (Markdown/TXT/PDF)
6. 等待文档 READY
7. 发起问答 → 确认 citations 非空
8. 撤销 Token → 确认 App 提示重新配对
9. 重新配对 → 恢复使用
10. Settings → 复制诊断信息

## 数据隐私
- 内测反馈不包含 Token、deviceId 完整值、文档内容、密码
- 见 [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md)

## 反馈收集
- GitHub Issues: [Bug Report](https://github.com/ningyd98/PersonalNotebook/issues/new?template=bug_report.yml)
- GitHub Issues: [Beta Feedback](https://github.com/ningyd98/PersonalNotebook/issues/new?template=beta_feedback.yml)

## 退出标准
- 所有 P0/P1 缺陷修复完毕
- 至少 2 个平台通过完整测试 checklist
- 核心流程 (配对→问答→重配对) 无阻塞
