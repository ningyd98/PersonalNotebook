#!/usr/bin/env python3
"""Validate worker status/phase correctness"""
import re
import sys

with open("backend/app/workers/celery_app.py") as f:
    code = f.read()

# Check _update_job calls use correct status values
calls = re.findall(r'_update_job\(db,\s*job_id,\s*"(\w+)"', code)
calls += re.findall(r"_update_job\(db,\s*job_id,\s*'(\w+)'", code)
old_bad = {"detecting","parsing","chunking","embedding","indexing","checking","completed","failed","pending"}
bad_calls = [c for c in calls if c in old_bad]
if bad_calls:
    print(f"FAIL: worker _update_job writes old status values: {bad_calls}")
    sys.exit(1)
print("PASS: all worker status values correct")
