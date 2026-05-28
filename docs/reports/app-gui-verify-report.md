# Phase 2F RC Report — macOS App GUI Verification

## 测试日期
待完成

## 环境要求
- macOS 26.4.1
- Flutter 3.44.0 stable
- Xcode 26.5
- Docker running (Core services healthy)
- Backend + Celery + Model Gateway running

## 构建
```bash
cd app/personal_notebook_app
flutter run -d macos
```

## 验收 Checklist

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | App 启动 | SplashScreen → PairingScreen | ⚠️ 待测 | |
| 2 | 输入 Core URL + Token | 格式校验通过 | ⚠️ 待测 | |
| 3 | 点击"连接" | 进入 Dashboard | ⚠️ 待测 | |
| 4 | Dashboard 显示 coreUrl | 正确 | ⚠️ 待测 | |
| 5 | Dashboard 显示 tenantId | default | ⚠️ 待测 | |
| 6 | Dashboard 显示 deviceId | 前8位 | ⚠️ 待测 | |
| 7 | Dashboard 显示 KB 数量 | >=0 | ⚠️ 待测 | |
| 8 | 知识库列表 | 可打开 | ⚠️ 待测 | |
| 9 | 创建知识库 | 成功 | ⚠️ 待测 | |
| 10 | 上传 markdown | 文件选择 + 上传成功 | ⚠️ 待测 | |
| 11 | 文档 READY | 状态流转 | ⚠️ 待测 | |
| 12 | Chat + citations | 回答 + 引用卡片 | ⚠️ 待测 | |
| 13 | revoke → 401 | 跳转 Pairing | ⚠️ 待测 | |
| 14 | 重新配对 | 成功恢复 | ⚠️ 待测 | |
| 15 | Settings 诊断信息 | 无 token/deviceId 完整值 | ⚠️ 待测 | |
| 16 | 网络错误提示 | 用户可理解 | ⚠️ 待测 | |
| 17 | Token 错误提示 | 401 → 清晰提示 | ⚠️ 待测 | |

## 阻塞原因
`flutter build macos` 在非交互/非 GUI 会话中超时。需在完整 macOS 桌面会话中手动执行 `flutter run -d macos`。
