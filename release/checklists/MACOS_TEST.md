# macOS Desktop Test Checklist

## 环境要求
- macOS (Apple Silicon / Intel)
- Flutter SDK 3.16+
- Xcode Command Line Tools (`xcode-select --install`)
- Docker Desktop (for Core services)
- `flutter config --enable-macos-desktop`

## 构建
```bash
cd app/personal_notebook_app
flutter pub get
flutter analyze
flutter test
flutter build macos --release
# 产物: build/macos/Build/Products/Release/PersonalNotebook.app
```

## 安装
- 直接双击 `PersonalNotebook.app` 启动
- 或在终端运行: `flutter run -d macos`

## 测试项目

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | App 启动 | 显示 PairingScreen | | |
| 2 | 输入 Core URL + Token | 格式校验通过 | | |
| 3 | 点击"连接" | 进入 Dashboard | | |
| 4 | Dashboard 显示 coreUrl | 正确显示 | | |
| 5 | Dashboard 显示 tenantId | default | | |
| 6 | Dashboard 显示 deviceId | 前 8 位 | | |
| 7 | Dashboard 显示 KB 数量 | > 0 | | |
| 8 | Dashboard 显示最近任务 | 计数 | | |
| 9 | 知识库列表 | 可打开、刷新 | | |
| 10 | 创建知识库 | 成功返回 | | |
| 11 | 上传 markdown | 文件选择 + 上传 | | |
| 12 | 文档进入 READY | status=READY | | |
| 13 | Chat 回答 + citations | citations 非空 | | |
| 14 | 撤销 token → 刷新 → 401 | 跳转 PairingScreen | | |
| 15 | 重新配对 | 成功恢复 | | |
| 16 | Settings → 诊断信息 | 不含 token | | |
| 17 | Settings → 复制诊断 | 剪贴板内容正确 | | |

## 常见失败

| 现象 | 排查 |
|------|------|
| App 不启动 | `flutter doctor` 检查 macOS 配置 |
| 配对失败 401 | 确认 token 未过期未撤销 |
| 配对超时 | 检查 Core 是否运行 `curl localhost:8000/health` |

## 测试结论

- 测试人：
- 日期：
- 系统版本：
- 通过 / 失败：
- 备注：
