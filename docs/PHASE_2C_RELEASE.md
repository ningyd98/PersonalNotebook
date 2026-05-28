# Phase 2C Release Notes

## 目标
将 PersonalNotebook 从"可运行 App 工程"推进到"可在真实设备上安装、配对、连接 Core、完成知识库核心流程"。

## 支持平台矩阵

| 平台 | 代码 | 构建脚本 | 真机实测 | 备注 |
|------|------|---------|---------|------|
| macOS 桌面 | ✅ | ✅ `flutter build macos` | ⚠️ 待验证 | 需 Flutter SDK + Xcode CLT |
| Windows 桌面 | ✅ | ✅ `flutter build windows` | ⚠️ 待验证 | 需 VS 2022 + Flutter |
| Android | ✅ | ✅ `flutter build apk` | ⚠️ 待验证 | 需 Android SDK; 签名配置见下文 |
| iOS | ✅ | ✅ `flutter build ios --no-codesign` | ⚠️ 待验证 | 需 Xcode; 真机需证书 |

**状态说明:**
- ✅ = 代码和脚本就绪，在开发机上通过 build/test
- ⚠️ = 未在真实设备实测，需在对应构建环境验证
- ❌ = 不支持

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

## 构建检查脚本

| 脚本 | 模式 | 说明 |
|------|------|------|
| `scripts/app_build_check.sh` | **宽松** | 跳过不可用平台 (Flutter 未安装不退出) |
| `scripts/app_build_verify.sh` | **严格** | Flutter 未安装退出 1; 平台构建失败退出 1 |

## 签名说明

### Android Release 签名
1. 创建 keystore: `keytool -genkey -v -keystore upload-keystore.jks -alias upload -keyalg RSA -keysize 2048 -validity 10000`
2. 创建 `app/personal_notebook_app/android/key.properties`
3. 不提交 `upload-keystore.jks`、`key.properties` 到 git

### iOS 签名
- 需要 Apple Developer Program 会员
- 或使用 `--no-codesign` 构建开发版本

## 各平台限制

### Android
- 本机局域网连接 Core: 使用 `http://192.168.x.x:8000` 而非 `localhost`
- Android 9+ 需 `android:usesCleartextTraffic="true"`

### iOS
- 本地网络权限: `NSLocalNetworkUsageDescription`
- 相机权限: `NSCameraUsageDescription`

## 真机验证 Checklist

- [ ] `flutter pub get && flutter analyze && flutter test` 通过
- [ ] macOS App 启动 → 显示 PairingScreen
- [ ] 输入 Core URL → 连接成功 → 进入 Dashboard
- [ ] Dashboard 显示 KB 数量、coreUrl、tenantId、deviceId
- [ ] KB 创建成功
- [ ] 文档上传成功 → 状态流转到 READY
- [ ] Chat 返回回答 + citations
- [ ] 撤销 token → App 检测 401 → 重新配对成功
- [ ] Android APK 安装 → 扫码配对 → 聊天闭环
- [ ] iOS 构建成功 (no-codesign)

## 发布前 Checklist

- [ ] `bash scripts/app_release_prepare.sh` 通过
- [ ] `bash scripts/app_build_verify.sh` 通过
- [ ] 无密钥/证书/token 提交
- [ ] 无构建产物提交
