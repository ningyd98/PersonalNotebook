# iOS TestFlight / Build Checklist

## 环境要求
- macOS + Xcode 15+
- Apple Developer 账号 (真机安装必需)
- Flutter SDK 3.16+ with iOS support

## 构建 (no-codesign)
```bash
cd app/personal_notebook_app
flutter pub get
flutter build ios --no-codesign
```

## Info.plist 权限检查
- `NSCameraUsageDescription`: 扫码配对需要
- `NSLocalNetworkUsageDescription`: 局域网连接 Core
- `NSBonjourServices`: 可选，局域网发现

## TestFlight 发布路径 (需付费 Apple Developer 账号)
1. Xcode → Signing & Capabilities → 选择 Team
2. Product → Archive
3. Window → Organizer → Distribute App → TestFlight
4. App Store Connect → TestFlight → 添加内测人员

## 测试项目

| # | 测试项 | 预期 | 结果 | 备注 |
|---|--------|------|------|------|
| 1 | `flutter build ios --no-codesign` 成功 | 编译通过 | | |
| 2 | Xcode 运行到模拟器 | App 启动 | | |
| 3 | 真机安装 (需证书) | App 可用 | | |
| 4 | 局域网配对 | 可连接 Core | | |
| 5 | 扫码配对 | 解析 QR 码 | | |
| 6 | Chat + citations | 功能正常 | | |
| 7 | 网络权限弹窗 | 用户允许后可用 | | |
| 8 | 撤销 token → 401 | 跳转配对页 | | |

## 注意事项
- 真机调试需在 Xcode 中配置 Signing Team
- 首次真机安装需信任开发者证书: Settings → General → Device Management
- iOS 14+ 局域网权限需用户主动授权

## 测试结论
- 测试人：
- 日期：
- 设备型号 / iOS 版本：
- 通过 / 失败：
- 备注：
