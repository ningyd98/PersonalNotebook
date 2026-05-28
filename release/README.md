# Internal Beta Release — 0.2.0+2

## 当前版本
Flutter App: `0.2.0+2`
Backend: `0.2.0`

## 支持平台

| 平台 | 状态 | 构建命令 |
|------|------|---------|
| macOS 桌面 | 代码/脚本就绪 | `flutter build macos --release` |
| Android | 代码/脚本就绪 | `flutter build apk --debug` |
| iOS | 代码/脚本就绪 | `flutter build ios --no-codesign` |
| Windows | 代码/脚本就绪 | `flutter build windows --release` |

## 构建产物位置

| 平台 | 路径 |
|------|------|
| macOS | `app/personal_notebook_app/build/macos/Build/Products/Release/PersonalNotebook.app` |
| Android debug | `app/personal_notebook_app/build/app/outputs/flutter-apk/app-debug.apk` |
| Android release | `app/personal_notebook_app/build/app/outputs/flutter-apk/app-release.apk` (需签名) |
| iOS | `app/personal_notebook_app/build/ios/ipa/` (需 Xcode + 证书) |
| Windows | `app/personal_notebook_app/build/windows/runner/Release/` |

## 重要说明
- **本目录不提交任何二进制构建产物**
- `.apk`, `.ipa`, `.app`, `.exe`, `.dmg`, `.msix`, `.jks` 不应出现在 git 中
- Release APK 签名需开发者自行生成 keystore

## 发布前检查
```bash
bash scripts/app_release_prepare.sh
```

## 测试 Checklist
- [macOS](checklists/MACOS_TEST.md)
- [Android](checklists/ANDROID_TEST.md)
- [iOS TestFlight](checklists/IOS_TESTFLIGHT.md)
- [Windows](checklists/WINDOWS_TEST.md)
