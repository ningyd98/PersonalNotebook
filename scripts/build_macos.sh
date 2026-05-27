#!/bin/bash
# PersonalNotebook macOS Build
set -e
cd "$(dirname "$0")/../app/personal_notebook_app"
echo "=== Flutter macOS Build ==="
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build macos --release
echo "macOS .app built at: build/macos/Build/Products/Release/personal_notebook_app.app"
# Generate .dmg
hdiutil create -volname PersonalNotebook -srcfolder build/macos/Build/Products/Release/personal_notebook_app.app -ov -format UDZO ../installers/macos/PersonalNotebook.dmg 2>/dev/null || echo "DMG creation skipped (installers/macos/ dir may not exist)"
echo "✅ macOS build complete"
