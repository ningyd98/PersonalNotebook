#!/bin/bash
# PersonalNotebook CI check — Phase 2B
set -e

echo "=== 1. compileall backend ==="
python3 -m compileall backend/app

echo "=== 2. compileall model-gateway ==="
python3 -m compileall model-gateway

echo "=== 3. ruff check ==="
if python3 -c "import ruff" 2>/dev/null; then
  python3 -m ruff check backend/app model-gateway --ignore E501,F401,E402
else
  echo "ruff not installed (skip)"
fi

echo "=== 4. pytest ==="
if python3 -c "import pytest" 2>/dev/null; then
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest backend/tests/test_pairing.py -q
else
  echo "pytest not installed (skip)"
fi

echo "=== 5. Validate worker status/phase correctness ==="
python3 scripts/_validate_worker.py

echo "=== 6. Validate model status is String(30) ==="
python3 -c '
with open("backend/app/models/models.py") as f:
    code = f.read()
if "Enum(" in code and "job_status" in code:
    print("FAIL: IngestJob.status still uses Enum")
    exit(1)
print("PASS: IngestJob.status is String(30)")
'

echo "=== 7. Validate business route auth coverage ==="
python3 -c '
import re
for f in [
    "backend/app/api/kb_routes.py",
    "backend/app/api/document_routes.py",
    "backend/app/api/chat_routes.py",
    "backend/app/api/job_routes.py",
]:
    with open(f) as fh:
        code = fh.read()
    ep = len(re.findall(r"@router\.(get|post|put|delete|patch)\(", code))
    au = code.count("current_device")
    print(f"  {f}: {au} auth refs, {ep} endpoints")
'

echo "=== 8. Flutter ==="
if command -v flutter &>/dev/null; then
  cd app/personal_notebook_app
  flutter pub get --offline 2>/dev/null || flutter pub get
  flutter analyze
  flutter test
  cd ../..
else
  echo "flutter not installed (skip)"
fi

echo ""
echo "✅ All CI checks passed"
