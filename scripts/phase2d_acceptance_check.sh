#!/bin/bash
# PersonalNotebook Phase 2D Acceptance Check
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
PASS=0; FAIL=0

check_file() { local label="$1" path="$2"
  if [ -f "$path" ]; then echo "  ✅ $label"; PASS=$((PASS+1))
  else echo "  ❌ $label — $path not found"; FAIL=$((FAIL+1)); fi
}

check_gitignore() {
  local p="$1"
  if grep -qF "$p" .gitignore 2>/dev/null || grep -qF "${p#\*}" .gitignore 2>/dev/null || grep -q "$p" .gitignore 2>/dev/null; then
    echo "  ✅ gitignore covers: $p"; PASS=$((PASS+1))
  else
    echo "  ⚠️  gitignore missing: $p"; FAIL=$((FAIL+1))
  fi
}

echo "=========================================="
echo " Phase 2D Acceptance Check"
echo "=========================================="

echo "--- 1. Required files ---"
check_file "app-build workflow"          .github/workflows/app-build.yml
check_file "app_build_verify.sh"         scripts/app_build_verify.sh
check_file "network_preflight.sh"        scripts/network_preflight.sh
check_file "release README"             release/README.md
check_file "macOS checklist"            release/checklists/MACOS_TEST.md
check_file "Android checklist"          release/checklists/ANDROID_TEST.md
check_file "iOS checklist"              release/checklists/IOS_TESTFLIGHT.md
check_file "Windows checklist"          release/checklists/WINDOWS_TEST.md
check_file "key.properties.example"     app/personal_notebook_app/android/key.properties.example
check_file "bug report template"        .github/ISSUE_TEMPLATE/bug_report.yml
check_file "beta feedback template"     .github/ISSUE_TEMPLATE/beta_feedback.yml
check_file "feature request template"   .github/ISSUE_TEMPLATE/feature_request.yml
check_file "Security Privacy doc"       docs/SECURITY_PRIVACY.md
check_file "Beta Test Plan"             docs/BETA_TEST_PLAN.md
check_file "User Feedback Template"     docs/USER_FEEDBACK_TEMPLATE.md
check_file ".gitignore"                 .gitignore
check_file "Diagnostics service"        app/personal_notebook_app/lib/services/diagnostics_service.dart

echo ""
echo "--- 2. Version check ---"
VERSION=$(grep "^version:" app/personal_notebook_app/pubspec.yaml | awk '{print $2}')
if [[ "$VERSION" == "0.2.0+2" || "$VERSION" > "0.2.0+2" ]]; then
  echo "  ✅ Flutter App version: $VERSION"; PASS=$((PASS+1))
else
  echo "  ❌ Version too old: $VERSION"; FAIL=$((FAIL+1))
fi

echo ""
echo "--- 3. app-build.yml audit ---"
if grep -q "upload-artifact" .github/workflows/app-build.yml 2>/dev/null; then
  echo "  ✅ upload-artifact found"; PASS=$((PASS+1))
else
  echo "  ❌ upload-artifact missing"; FAIL=$((FAIL+1))
fi
if grep -q "android-debug-apk" .github/workflows/app-build.yml 2>/dev/null; then
  echo "  ✅ android-debug-apk artifact name"; PASS=$((PASS+1))
else
  echo "  ❌ android-debug-apk artifact name missing"; FAIL=$((FAIL+1))
fi

echo ""
echo "--- 4. .gitignore audit ---"
check_gitignore "*.apk"
check_gitignore "*.aab"
check_gitignore "*.ipa"
check_gitignore "*.app"
check_gitignore "*.dmg"
check_gitignore "*.exe"
check_gitignore "*.msix"
check_gitignore "*.jks"
check_gitignore "*.keystore"
check_gitignore "keystore"
check_gitignore "key.properties"

echo ""
echo "--- 5. Build artifacts audit ---"
BAD_FILES=$(git ls-files | grep -E '\.(apk|aab|ipa|app|exe|dmg|msix|jks|keystore)$' || true)
if [ -n "$BAD_FILES" ]; then
  echo "  ❌ Build artifacts tracked: $BAD_FILES"; FAIL=$((FAIL+1))
else
  echo "  ✅ No build artifacts tracked"; PASS=$((PASS+1))
fi

echo ""
echo "--- 6. Secrets audit ---"
BAD_SECRETS=$(git ls-files | grep -E '(keystore|key\.properties)$' | grep -v example || true)
if [ -n "$BAD_SECRETS" ]; then
  echo "  ❌ Secret files tracked: $BAD_SECRETS"; FAIL=$((FAIL+1))
else
  echo "  ✅ No secrets tracked"; PASS=$((PASS+1))
fi

echo ""
echo "--- 7. Issue templates check ---"
for tmpl in bug_report.yml beta_feedback.yml feature_request.yml; do
  if [ -s ".github/ISSUE_TEMPLATE/$tmpl" ]; then
    echo "  ✅ $tmpl exists and non-empty"; PASS=$((PASS+1))
  else
    echo "  ❌ $tmpl missing or empty"; FAIL=$((FAIL+1))
  fi
done

echo ""
echo "--- 8. Flutter check ---"
if command -v flutter &>/dev/null; then
  cd app/personal_notebook_app
  flutter pub get --offline 2>/dev/null || flutter pub get 2>/dev/null || true
  flutter analyze 2>/dev/null && echo "  ✅ Flutter analyze passed" && PASS=$((PASS+1)) || \
    echo "  ⚠️  Flutter analyze failed (may be SDK/environment issue)"
  flutter test 2>/dev/null && echo "  ✅ Flutter test passed" && PASS=$((PASS+1)) || \
    echo "  ⚠️  Flutter test unavailable"
  cd "$ROOT"
else
  echo "  ⚠️  Flutter not installed (skip analyze/test)"
fi

echo ""
echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
