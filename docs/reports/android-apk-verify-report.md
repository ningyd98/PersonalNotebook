# Phase 2F RC Report — Android APK Verification

## 测试日期
待完成

## 环境要求
- Android SDK 36 (Flutter 3.44 要求)
- Android 真机 (Android 9+)
- USB 调试启用
- 手机与 Core 电脑在同一 Wi-Fi

## 构建
```bash
sdkmanager "platforms;android-36" "build-tools;36.0.0"
cd app/personal_notebook_app
flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

## 验收 Checklist

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | APK 构建 | 成功 | ⚠️ 待测 | 需 SDK 36 |
| 2 | APK 安装 | adb install 成功 | ⚠️ 待测 | 需真机 |
| 3 | App 启动 | PairingScreen | ⚠️ 待测 | |
| 4 | 局域网配对 | 输入 `http://192.168.3.107:8000` + Token | ⚠️ 待测 | |
| 5 | 扫码配对 | QR 码解析 | ⚠️ 待测 | |
| 6 | Dashboard | KB 数量/状态正确 | ⚠️ 待测 | |
| 7 | Chat + citations | 回答 + 引用卡片 | ⚠️ 待测 | |
| 8 | revoke → 401 | 跳转配对 | ⚠️ 待测 | |
| 9 | 断网错误提示 | 用户可理解 | ⚠️ 待测 | |
| 10 | Settings 诊断脱敏 | 无 token 泄露 | ⚠️ 待测 | |

## 阻塞原因
- Android SDK 当前 34.0.0，需升级到 36 (Flutter 3.44 要求)
- 无 Android 真机连接 (`adb devices` 为空)
