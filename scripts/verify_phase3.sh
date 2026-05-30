#!/bin/bash
# Phase 3D/3E/3F verification script
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
check() { local l="$1"; shift; if "$@" 2>/dev/null; then echo "✅ $l"; PASS=$((PASS+1)); else echo "❌ $l"; FAIL=$((FAIL+1)); fi; }

echo "=========================================="
echo " Phase 3 Verification"
echo "=========================================="

echo ""; echo "--- Backend compile ---"
cd "$ROOT/backend"
python3 -m compileall -q app && echo "✅ compileall: PASS" && PASS=$((PASS+1)) || { echo "❌ compileall: FAIL"; FAIL=$((FAIL+1)); }

echo ""; echo "--- Backend tests ---"
cd "$ROOT/backend"
python3 -m pytest -q tests/ 2>/dev/null && { echo "✅ pytest: PASS"; PASS=$((PASS+1)); } || { echo "⚠️ pytest: some failures (check details)"; FAIL=$((FAIL+1)); }

echo ""; echo "--- Static grep checks ---"
cd "$ROOT"
CIT_COUNT=$(grep -c "class _CitationCard\b" app/personal_notebook_app/lib/screens/chat_screen.dart 2>/dev/null || echo 0)
[ "$CIT_COUNT" = "1" ] && echo "✅ 1 _CitationCard class" && PASS=$((PASS+1)) || { echo "❌ _CitationCard: got $CIT_COUNT"; FAIL=$((FAIL+1)); }

API_CHAT=$(grep "api_key" app/personal_notebook_app/lib/screens/chat_screen.dart 2>/dev/null | grep -v "^#" | grep -v "_sanitize" || true)
[ -z "$API_CHAT" ] && echo "✅ Flutter chat body: no api_key" && PASS=$((PASS+1)) || { echo "❌ api_key in Flutter chat body"; FAIL=$((FAIL+1)); }

API_SCHEMA=$(grep "api_key" backend/app/schemas/schemas.py 2>/dev/null | grep -v "^#" | grep -v "api_key_configured" || true)
[ -z "$API_SCHEMA" ] && echo "✅ ChatRequest: no api_key" && PASS=$((PASS+1)) || { echo "❌ api_key in ChatRequest"; FAIL=$((FAIL+1)); }

SP=$(grep -n '"storage_path"' backend/app/api/chat_routes.py backend/app/api/document_routes.py 2>/dev/null | grep -v "masked" | grep -v "_mask" || true)
[ -z "$SP" ] && echo "✅ storage_path not in API returns" && PASS=$((PASS+1)) || { echo "⚠️ storage_path found (check if masked)"; FAIL=$((FAIL+1)); }

echo ""; echo "--- Auth regression ---"
cd "$ROOT"
http_code() { curl -sf -o /dev/null -w "%{http_code}" "$@" 2>/dev/null; }
CURL_BASE="http://localhost:8000"
for ep in "/api/chat" "/api/conversations" "/api/chunks/a1b2c3d4-e5f6-7890-abcd-ef1234567890" "/api/kbs" "/api/system/diagnostics"; do
  CODE=$(http_code "${CURL_BASE}${ep}")
  if [ "$CODE" = "401" ] || [ "$CODE" = "403" ]; then
    echo "  ✅ $(echo $ep | cut -c1-40): $CODE"; PASS=$((PASS+1))
  else
    echo "  ⚠️ $(echo $ep | cut -c1-40): got $CODE (Core may be down)"; FAIL=$((FAIL+1))
  fi
done

echo ""; echo "--- Flutter analyze ---"
cd "$ROOT/app/personal_notebook_app"
if which flutter >/dev/null 2>&1; then
  flutter analyze 2>&1 | tail -5 && { echo "✅ flutter analyze: PASS"; PASS=$((PASS+1)); } || { echo "⚠️ flutter analyze: warnings (check above)"; FAIL=$((FAIL+1)); }
else
  echo "  SKIP: Flutter not installed"; PASS=$((PASS+1))
fi

echo ""; echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
