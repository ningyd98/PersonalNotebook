# Windows Desktop Test Checklist

## 环境要求
- Windows 10/11
- Flutter SDK 3.16+
- Visual Studio 2022 (Desktop development with C++)
- Docker Desktop for Windows
- `flutter config --enable-windows-desktop`

## 构建
```powershell
cd app/personal_notebook_app
flutter pub get
flutter build windows --release
# 产物: build/windows/runner/Release/
```

## 配对
- 桌面端直接使用 `http://localhost:8000`
- 如需移动端连接，使用 `scripts/network_preflight.sh` 的 Windows 等效 (ipconfig)

## 测试项目

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | App 启动 | PairingScreen | | |
| 2 | 配对成功 | Dashboard | | |
| 3 | Runtime Manager 启动 Core | docker compose up -d | | |
| 4 | Runtime Manager 停止 Core | docker compose down | | |
| 5 | 文档上传 + READY | 状态正常 | | |
| 6 | Chat + citations | 功能正常 | | |
| 7 | 撤销 token → 401 | 跳转配对页 | | |

## 常见失败

| 现象 | 排查 |
|------|------|
| 构建失败 | 确认 VS 2022 C++ workload 已安装 |
| Docker 不可用 | 确认 Docker Desktop 运行；WSL2 后端已配置 |

## 测试结论
- 测试人：
- 日期：
- Windows 版本：
- 通过 / 失败：
- 备注：
