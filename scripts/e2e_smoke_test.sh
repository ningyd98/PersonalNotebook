#!/bin/bash
# Personal-KB E2E Smoke Test
# 自动完成：创建 KB → 上传 → 等待 READY → 问答 → reindex → consistency
# 用法: bash scripts/e2e_smoke_test.sh

set -e

API="${API_URL:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
  local label="$1" condition="$2" detail="$3"
  if eval "$condition"; then
    echo "  ✅ $label"
    ((PASS++))
  else
    echo "  ❌ $label — $detail"
    ((FAIL++))
  fi
}

echo "=========================================="
echo " Personal-KB E2E Smoke Test"
echo " API: $API"
echo "=========================================="

# 1. Health check
echo ""
echo "--- 1. Health ---"
HEALTH=$(curl -sf "$API/health" 2>/dev/null || echo '{"status":"error"}')
check "Backend health" '[ "$(echo "$HEALTH" | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))" 2>/dev/null)" = "ok" ]' "$HEALTH"

# 2. Create KB
echo ""
echo "--- 2. Create KB ---"
KB_NAME="e2e-test-$(date +%s)"
KB_RESP=$(curl -sf -X POST "$API/api/kbs" -H "Content-Type: application/json" -d "{\"name\":\"$KB_NAME\"}" 2>/dev/null || echo '{}')
KB_ID=$(echo "$KB_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
check "Created KB" '[ -n "$KB_ID" ]' "KB_RESP=$KB_RESP"
echo "  KB_ID=$KB_ID"

# 3. Upload sample markdown
echo ""
echo "--- 3. Upload Markdown ---"
TMP_MD=$(mktemp /tmp/e2e_test_XXXX.md)
cat > "$TMP_MD" << 'MDEOF'
---
title: E2E Test
tags: [test, e2e]
---

# Q-learning

Q-learning 是一种无模型的时序差分控制算法，由 Watkins 于 1989 年提出。

## 更新公式

Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]

## 关键特性

- 无模型 (Model-free)
- Off-policy
- 单步更新
MDEOF

UPLOAD_RESP=$(curl -sf -X POST "$API/api/kbs/$KB_ID/documents/upload" -F "file=@$TMP_MD" 2>/dev/null || echo '{}')
DOC_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('document_id',''))" 2>/dev/null)
check "Upload markdown" '[ -n "$DOC_ID" ]' "UPLOAD_RESP=$UPLOAD_RESP"
echo "  DOC_ID=$DOC_ID"
rm -f "$TMP_MD"

# 4. Wait for READY (poll 30s)
echo ""
echo "--- 4. Wait READY ---"
READY=0
for i in $(seq 1 30); do
  DOC_STATUS=$(curl -sf "$API/api/documents/$DOC_ID" 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
  echo "  [$i] status=$DOC_STATUS"
  if [ "$DOC_STATUS" = "READY" ]; then
    READY=1
    break
  fi
  sleep 2
done
check "Document READY" '[ "$READY" = "1" ]' "Final status=$DOC_STATUS"

# 5. Chat
echo ""
echo "--- 5. Chat ---"
CHAT_RESP=$(curl -sf -X POST "$API/api/chat" -H "Content-Type: application/json" \
  -d "{\"kb_id\":\"$KB_ID\",\"question\":\"什么是 Q-learning？\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" 2>/dev/null || echo '{}')
CHAT_ANSWER=$(echo "$CHAT_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('answer','')[:100])" 2>/dev/null)
CITATIONS=$(echo "$CHAT_RESP" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('citations',[])))" 2>/dev/null)
check "Chat answered" '[ -n "$CHAT_ANSWER" ]' "Answer: ${CHAT_ANSWER:0:80}"
check "Chat has citations" '[ "$CITATIONS" -gt 0 ]' "Citations=$CITATIONS"

# 6. Reindex
echo ""
echo "--- 6. Reindex ---"
REIDX_RESP=$(curl -sf -X POST "$API/api/documents/$DOC_ID/reindex" 2>/dev/null || echo '{}')
JOB_ID=$(echo "$REIDX_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
check "Reindex submitted" '[ -n "$JOB_ID" ]'

# Wait for reindex to complete
sleep 5
DOC_AFTER=$(curl -sf "$API/api/documents/$DOC_ID" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('active_version',0))" 2>/dev/null)
check "Active version updated" '[ "$DOC_AFTER" -ge 2 ]' "active_version=$DOC_AFTER"

# 7. Consistency check
echo ""
echo "--- 7. Consistency ---"
CONS_RESP=$(curl -sf "$API/api/kbs/$KB_ID/consistency?dry_run=true" 2>/dev/null || echo '{}')
CONS_OK=$(echo "$CONS_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('report',{}).get('is_consistent',False))" 2>/dev/null)
check "Consistency check" '[ "$CONS_OK" = "True" ]' "$CONS_RESP"

# Final
echo ""
echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
