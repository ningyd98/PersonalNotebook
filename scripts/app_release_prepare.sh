#!/bin/bash
# PersonalNotebook App Release Prepare — Phase 2C
# 发布前检查：版本号、git clean、无密钥泄漏
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
echo "=========================================="
echo " App Release Prepare"
echo "=========================================="

# 1. Version check
VERSION=$(grep "^version:" "$ROOT/app/personal_notebook_app/pubspec.yaml" | awk '{print $2}')
echo "Flutter App version: $VERSION"
echo "Backend version:     0.2.0"

# 2. Git clean check
cd "$ROOT"
if ! git diff --quiet; then
  echo "⚠️  Uncommitted changes detected:"
  git diff --stat
else
  echo "✅ Git working tree clean"
fi

# 3. No secrets
echo "--- Secret scan ---"
SECRETS_FOUND=false
for pattern in 'PRIVATE KEY' 'BEGIN RSA' 'keystore' '\.jks' '\.p12' 'certificate'; do
  hits=$(git ls-files | xargs grep -l "$pattern" 2>/dev/null | grep -v '.gitignore' | grep -v 'example' | grep -v 'docs/' || true)
  if [ -n "$hits" ]; then
    echo "⚠️  Files matching '$pattern': $hits"
    SECRETS_FOUND=true
  fi
done
if ! $SECRETS_FOUND; then echo "✅ No secrets detected"; fi

# 4. No build artifacts
if git ls-files | grep -qE '\.(apk|ipa|app|exe|dmg|aab|jks|keystore)'; then
  echo "⚠️  Build artifacts tracked in git!"
  git ls-files | grep -E '\.(apk|ipa|app|exe|dmg|aab|jks|keystore)'
else
  echo "✅ No build artifacts in git"
fi

echo ""
echo "--- Platform build commands ---"
echo "macOS:   flutter build macos --release"
echo "Windows: flutter build windows --release"
echo "Android: flutter build apk --release"
echo "         flutter build appbundle --release"
echo "iOS:     flutter build ipa --release  (需 Xcode + 证书)"
echo ""
echo "✅ Release prepare complete"
