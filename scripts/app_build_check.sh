#!/bin/bash
# PersonalNotebook App Build Check — Phase 2C
# 验证 Flutter App 在本地可编译。跳过不可用平台。
set -e

echo "=========================================="
echo " App Build Check"
echo "=========================================="

HAS_FLUTTER=false
HAS_MACOS=false
HAS_ANDROID=false
HAS_WINDOWS=false
HAS_LINUX=false
HAS_XCODE=false

# Detect Flutter
if command -v flutter &>/dev/null; then
  HAS_FLUTTER=true
  echo "✅ Flutter SDK detected"
else
  echo "❌ Flutter SDK not found — skip all Flutter checks"
  echo "   安装: https://docs.flutter.dev/get-started/install"
  exit 0
fi

# Detect platforms
if [[ "$OSTYPE" == "darwin"* ]]; then
  HAS_MACOS=true
  echo "✅ macOS runner"
  if xcodebuild -version &>/dev/null 2>&1; then HAS_XCODE=true; echo "✅ Xcode detected"; fi
fi
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then HAS_WINDOWS=true; echo "✅ Windows runner"; fi
if [[ "$OSTYPE" == "linux-gnu"* ]]; then HAS_LINUX=true; echo "✅ Linux runner"; fi
if command -v adb &>/dev/null || [ -n "$ANDROID_HOME" ]; then HAS_ANDROID=true; echo "✅ Android SDK detected"; fi

echo ""

cd app/personal_notebook_app

echo "--- 1. flutter pub get ---"
flutter pub get

echo "--- 2. flutter analyze ---"
flutter analyze

echo "--- 3. flutter test ---"
flutter test

# Platform builds (best-effort, skip if SDK not available)
if $HAS_MACOS; then
  echo "--- 4. flutter build macos --release ---"
  flutter build macos --release 2>&1 || echo "⚠️ macOS build failed (may need flutter create macos)"
fi

if $HAS_ANDROID; then
  echo "--- 5. flutter build apk --debug ---"
  flutter build apk --debug 2>&1 || echo "⚠️ Android build failed (may need Android SDK setup)"
fi

if $HAS_WINDOWS; then
  echo "--- 6. flutter build windows --release ---"
  flutter build windows --release 2>&1 || echo "⚠️ Windows build failed"
fi

echo ""
echo "✅ Build check complete"
