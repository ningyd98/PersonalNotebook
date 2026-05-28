# Phase 2C Release Notes

## 目标
将 PersonalNotebook 从"可运行 App 工程"推进到"可在真实设备上安装、配对、连接 Core、完成知识库核心流程"。

## 支持平台矩阵

| 平台 | run | build | pairing | chat | runtime manager | 状态 |
|------|-----|-------|---------|------|-----------------|------|
| macOS 桌面 | ✅ | ✅ (macOS runner) | ✅ | ✅ | ✅ (Docker 管理) | **已就绪** |
| Windows 桌面 | ✅ | ✅ (Windows runner) | ✅ | ✅ | ✅ (Docker 管理) | **已就绪** |
| Linux 桌面 | ✅ | ✅ (optional) | ✅ | ✅ | ✅ (Docker 管理) | 可选 |
| Android 移动 | ✅ | ✅ APK+AAB | ✅ (扫码配对) | ✅ | ❌ (隐藏入口) | **构建就绪** |
| iOS 移动 | ✅ | ✅ (需 Xcode) | ✅ (扫码配对) | ✅ | ❌ (隐藏入口) | **构建就绪** |

## 构建命令

```bash
# macOS
flutter build macos --release

# Windows
flutter build windows --release

# Android
flutter build apk --debug       # 开发调试
flutter build apk --release     # 发布 (需签名)
flutter build appbundle --release

# iOS
flutter build ios --no-codesign # 开发调试
flutter build ipa --release     # 发布 (需 Xcode + 证书)
```

## 签名说明

### Android Release 签名
1. 创建 keystore: `keytool -genkey -v -keystore upload-keystore.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000`
2. 创建 `app/personal_notebook_app/android/key.properties`:
   ```
   storePassword=xxx
   keyPassword=xxx
   keyAlias=upload
   storeFile=../upload-keystore.jks
   ```
3. 不提交 `upload-keystore.jks`、`key.properties` 到 git

### iOS 签名
- 需要 Apple Developer Program 会员
- Xcode: Signing & Capabilities → 选择 Team
- 或使用 `--no-codesign` 构建开发版本

## 各平台限制

### macOS
- 需要 Xcode Command Line Tools + Flutter macOS 支持
- 首次构建需 `flutter config --enable-macos-desktop`

### Windows
- 需要 Visual Studio 2022 with "Desktop development with C++"
- 需要 Docker Desktop for Windows
- `flutter config --enable-windows-desktop`

### Android
- 需要 Android SDK + Android Studio
- 本机局域网访问 Core: 使用 `http://192.168.x.x:8000` 而非 `localhost`
- Android 9+ 需要 `android:usesCleartextTraffic="true"` 用于 HTTP 访问

### iOS
- 需要 Xcode + Apple Developer 账号
- 本地网络权限: 需在 Info.plist 中声明 `NSLocalNetworkUsageDescription`
- 相机权限: `NSCameraUsageDescription`
- iOS 14+ 局域网发现需要 `NSBonjourServices`

## 真实设备联调 Checklist

- [ ] `flutter pub get` 成功
- [ ] `flutter analyze` 通过
- [ ] `flutter test` 通过
- [ ] 桌面端 App 启动
- [ ] Pairing: 输入 Core URL + Token
- [ ] 调用 `/health` 获得响应
- [ ] 配对 verify 成功
- [ ] Dashboard 显示 KB 列表
- [ ] KB 创建成功
- [ ] 文档上传成功
- [ ] 文档进入 READY 状态
- [ ] Chat 返回带引用的回答
- [ ] 撤消 token 后 App 提示 401
- [ ] 重新配对成功
- [ ] Android APK 安装成功
- [ ] iOS 构建成功 (no-codesign)

## 发布前 Checklist

- [ ] `bash scripts/app_release_prepare.sh` 通过
- [ ] `bash scripts/app_build_check.sh` 通过
- [ ] `bash scripts/app_device_smoke_test.sh` 通过
- [ ] 版本号一致 (Flutter / Backend)
- [ ] 无密钥/证书/token 提交
- [ ] 无构建产物提交
- [ ] README 更新
