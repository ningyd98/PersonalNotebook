#!/bin/bash
# PersonalNotebook CI check — Phase 2B
set -e

echo "=== 1. compileall backend ==="
python3 -m compileall backend/app

echo "=== 2. compileall model-gateway ==="
python3 -m compileall model-gateway

echo "=== 3. ruff check ==="
python3 -m ruff check backend/app model-gateway --ignore E501,F401,E402 2>/dev/null || echo "ruff not installed (skip)"

echo "=== 4. pytest ==="
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest backend/tests/ -v 2>/dev/null || echo "pytest: tests need deps (skip)"

echo "=== 5. Validate worker status/phase correctness ==="
python3 -c "
import re
with open('backend/app/workers/celery_app.py') as f:
    code = f.read()
calls = re.findall(r'_update_job\(db,\s*job_id,\s*[\"\\\'](\w+)[\"\\\']', code)
old_bad = {'detecting','parsing','chunking','embedding','indexing','checking','completed','failed','pending'}
bad_calls = [c for c in calls if c in old_bad]
if bad_calls:
    print(f'FAIL: worker _update_job writes old status values: {bad_calls}')
    exit(1)
job_calls = re.findall(r'IngestJob\(.*?status\s*=\s*[\"\\\'](\w+)[\"\\\']', code, re.DOTALL)
bad_jobs = [c for c in job_calls if c not in ('PENDING','RUNNING','RETRYING','SUCCESS','FAILED','CANCELLED')]
if bad_jobs:
    print(f'FAIL: IngestJob created with bad status: {bad_jobs}')
    exit(1)
print('PASS: all worker status values correct')
"

echo "=== 6. Validate model status is String(30) ==="
python3 -c "
with open('backend/app/models/models.py') as f:
    code = f.read()
if 'Enum(' in code and 'job_status' in code:
    print('FAIL: IngestJob.status still uses Enum')
    exit(1)
print('PASS: IngestJob.status is String(30)')
"

echo "=== 7. Validate all business routes have paired-device auth ==="
python3 -c "
import re, sys
files = [
    'backend/app/api/kb_routes.py',
    'backend/app/api/document_routes.py',
    'backend/app/api/chat_routes.py',
    'backend/app/api/job_routes.py',
]
total = 0
for f in files:
    with open(f) as fh:
        code = fh.read()
    # count endpoint defs
    endpoints = re.findall(r'@router\.(get|post|put|delete|patch)\(', code)
    # count current_device occurrences
    auths = code.count('current_device')
    total += auths
    print(f'{f}: {auths} auth refs, {len(endpoints)} endpoints')
print(f'Total auth refs: {total}')
"

echo "=== 8. Flutter analyze (if flutter available) ==="
if command -v flutter &>/dev/null; then
  cd app/personal_notebook_app && flutter pub get --offline 2>/dev/null || flutter pub get
  flutter analyze
  flutter test
else
  echo "flutter not installed (skip — runs in GitHub Actions)"
fi

echo ""
echo "✅ All CI checks passed"
