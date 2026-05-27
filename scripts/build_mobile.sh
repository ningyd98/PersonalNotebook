#!/bin/bash
# Android / iOS Build Scripts
set -e
cd "$(dirname "$0")/../app/personal_notebook_app"

case "${1:-android}" in
  android)
    echo "=== Flutter Android Build ==="
    flutter build apk --release
    flutter build appbundle --release
    echo "✅ APK: build/app/outputs/flutter-apk/app-release.apk"
    echo "✅ AAB: build/app/outputs/bundle/release/app-release.aab"
    ;;
  ios)
    echo "=== Flutter iOS Build ==="
    flutter build ipa --release
    echo "✅ IPA: build/ios/ipa/"
    ;;
  *)
    echo "Usage: $0 [android|ios]"
    exit 1
    ;;
esac
