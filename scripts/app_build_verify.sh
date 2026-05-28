#!/bin/bash
# PersonalNotebook App Build Verify — Phase 2C-B (STRICT)
# 与 app_build_check.sh 的区别：verify 必须失败即退出，不跳过可用平台
set -e

echo "=========================================="
echo " App Build Verify (STRICT)"
echo "=========================================="

if ! command -v flutter &>/dev/null; then
  echo "❌ Flutter SDK not found — cannot proceed"
  exit 1
fi
echo "✅ Flutter SDK detected"

cd app/personal_notebook_app

echo "--- 1. flutter pub get ---"
flutter pub get

echo "--- 2. flutter analyze ---"
flutter analyze

echo "--- 3. flutter test ---"
flutter test

# Platform builds (fail if SDK available but build fails)
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "--- 4. flutter build macos --release ---"
  flutter build macos --release
  echo "✅ macOS build passed"
fi

if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  echo "--- 4. flutter build windows --release ---"
  flutter build windows --release
  echo "✅ Windows build passed"
fi

if command -v adb &>/dev/null || [ -n "$ANDROID_HOME" ]; then
  echo "--- 5. flutter build apk --debug ---"
  flutter build apk --debug
  echo "✅ Android build passed"
fi

echo ""
echo "✅ Build verify complete"
