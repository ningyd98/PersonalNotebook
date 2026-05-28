#!/bin/bash
# PersonalNotebook Phase 2E Device Test Environment Report
set -e

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
OUT="tmp/phase2e_env_report.txt"
mkdir -p tmp

{
echo "=== Phase 2E Environment Report ==="
echo "Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

echo "--- Git ---"
echo "commit: $(git rev-parse HEAD)"
echo "branch: $(git branch --show-current)"
echo ""

echo "--- Flutter ---"
if command -v flutter &>/dev/null; then
  flutter --version 2>/dev/null | head -3
  echo "devices:"
  flutter devices 2>/dev/null | grep '•' || echo "  (none)"
else
  echo "Flutter: NOT INSTALLED"
fi
echo ""

echo "--- Docker ---"
if command -v docker &>/dev/null; then
  docker --version
else
  echo "Docker: NOT INSTALLED"
fi
echo ""

echo "--- Core Health ---"
HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo 'unreachable')
echo "http://localhost:8000/health: $HEALTH"
echo ""

echo "--- Network ---"
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Local IPs:"
  ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{printf "  %s\n", $2}'
fi
echo ""

echo "--- App Version ---"
grep "^version:" app/personal_notebook_app/pubspec.yaml || echo "unknown"
echo ""

echo "--- Issue Templates ---"
ls .github/ISSUE_TEMPLATE/*.yml 2>/dev/null || echo "NONE"
echo ""

echo "=== End Report ==="
} > "$OUT"

echo "✅ Report written to $OUT"
cat "$OUT"
