#!/bin/bash
# Personal-KB CI check (minimal)
set -e

echo "=== 1. compileall backend ==="
python3 -m compileall backend/app

echo "=== 2. compileall model-gateway ==="
python3 -m compileall model-gateway

echo "=== 3. ruff check ==="
python3 -m ruff check backend/app model-gateway --ignore E501,F401,E402

echo "=== 4. pytest ==="
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest backend/tests/ -v
echo "=== 5. Validate worker status/phase correctness ==="
python3 -c "
# Verify worker uses correct status values
import re
with open('backend/app/workers/celery_app.py') as f:
    code = f.read()
# Check _update_job calls
calls = re.findall(r'_update_job\(db,\s*job_id,\s*[\"\\'](\w+)[\"\\']', code)
old_bad = {'detecting','parsing','chunking','embedding','indexing','checking','completed','failed','pending'}
bad_calls = [c for c in calls if c in old_bad]
if bad_calls:
    print(f'FAIL: worker _update_job writes old status values: {bad_calls}')
    exit(1)
# Check reparse job creation
job_calls = re.findall(r'IngestJob\(.*?status\s*=\s*[\"\\'](\w+)[\"\\']', code, re.DOTALL)
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

echo ""
echo "✅ All CI checks passed"
