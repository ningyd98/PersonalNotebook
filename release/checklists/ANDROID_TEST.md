# Android Device Test Checklist

## 环境要求
- Android 真机 (Android 9+)
- USB 调试已启用
- ADB 已安装 (`adb devices` 可见设备)
- 手机与 Core 电脑在同一 Wi-Fi
- Core 监听 `0.0.0.0:8000`

## 构建与安装
```bash
cd app/personal_notebook_app
flutter pub get
flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

## 配对
- Core URL 使用局域网 IP: `http://192.168.x.x:8000`
- 执行 `scripts/network_preflight.sh` 获取 IP
- 手机浏览器访问 `http://192.168.x.x:8000/health` 确认可达

## 测试项目

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | APK 安装成功 | App 图标出现 | | |
| 2 | App 启动 | PairingScreen | | |
| 3 | 输入 Core URL (局域网 IP) | 格式校验通过 | | |
| 4 | 输入 Token | 连接成功→Dashboard | | |
| 5 | 扫码配对 | 解析 QR 码 | | |
| 6 | Dashboard | KB 数量等正确 | | |
| 7 | 知识库列表 | 可打开 | | |
| 8 | Chat 问答 + 引用 | citations 非空 | | |
| 9 | 断网重连 | 错误提示清晰 | | |
| 10 | 撤销 token → 401 | 跳转配对页 | | |
| 11 | 重新配对 | 成功恢复 | | |
| 12 | Settings → 诊断 | 不含敏感信息 | | |

## 常见失败

| 现象 | 排查 |
|------|------|
| 连接超时 | 手机浏览器访问 `http://IP:8000/health` 确认可达 |
| Cleartext 错误 | AndroidManifest `usesCleartextTraffic=true` |
| 扫码不可用 | 手动输入 fallback; 确认相机权限 |
| 配对 401 | token 过期/撤销; 重新生成 |

## 测试结论
- 测试人：
- 日期：
- 设备型号 / 系统版本：
- 通过 / 失败：
- 备注：
