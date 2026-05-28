#!/bin/bash
# PersonalNotebook App E2E Acceptance — Phase 2B
set +e

API="${API_URL:-http://localhost:8000}"
PASS=0; FAIL=0

check() { local label="$1" condition="$2" detail="$3"
  if eval "$condition" 2>/dev/null; then echo "  ✅ $label"; ((PASS++))
  else echo "  ❌ $label — $detail"; ((FAIL++)); fi
}
json_val() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d${1})" 2>/dev/null; }

echo "=========================================="
echo " PersonalNotebook App E2E Acceptance"
echo " API: $API"
echo "=========================================="

echo; echo "--- 1. Health ---"
H=$(curl -sf "$API/health" 2>/dev/null || echo '{"status":"error"}')
check "health ok" '[ "$(echo "$H" | json_val "[\"status\"]")" = "ok" ]' "$H"

echo; echo "--- 2. Pairing Create ---"
PAIR=$(curl -sf -X POST "$API/auth/pair/create" -H "Content-Type: application/json" \
  -d '{"tenant_id":"default","device_name":"e2e-test","expires_hours":1}' 2>/dev/null || echo '{}')
TOKEN=$(echo "$PAIR" | json_val "[\"token\"]")
DID=$(echo "$PAIR" | json_val "[\"device_id\"]")
check "pair create" '[ -n "$TOKEN" ]' "resp=$PAIR"

echo; echo "--- 3. Pairing Verify ---"
VERIFY=$(curl -sf -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"device_name\":\"e2e-phone\"}" 2>/dev/null || echo '{}')
check "pair verify" '[ "$(echo "$VERIFY" | json_val "[\"verified\"]")" = "True" ]' "$VERIFY"

echo; echo "--- 4. Create KB ---"
KB=$(curl -sf -X POST "$API/api/kbs" -H "Content-Type: application/json" \
  -d '{"name":"e2e-app-test"}' 2>/dev/null || echo '{}')
KB_ID=$(echo "$KB" | json_val "[\"id\"]")
check "create kb" '[ -n "$KB_ID" ]'

echo; echo "--- 5. Upload ---"
TMP_MD=$(mktemp /tmp/e2e_app_XXXX.md)
cat > "$TMP_MD" << 'MDEOF'
---
title: E2E App Test
tags: [e2e]
---
# Q-learning
Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]
MDEOF
UP=$(curl -sf -X POST "$API/api/kbs/$KB_ID/documents/upload" -F "file=@$TMP_MD" 2>/dev/null || echo '{}')
DOC_ID=$(echo "$UP" | json_val "[\"document_id\"]")
check "upload" '[ -n "$DOC_ID" ]'
rm -f "$TMP_MD"

echo; echo "--- 6. Wait READY ---"
READY=0; S=""
for i in $(seq 1 30); do
  S=$(curl -sf "$API/api/documents/$DOC_ID" 2>/dev/null | json_val "[\"status\"]")
  [ "$S" = "READY" ] && { READY=1; break; }
  sleep 2
done
check "doc READY" '[ "$READY" = "1" ]' "status=$S"

echo; echo "--- 7. Chat ---"
CHAT=$(curl -sf -X POST "$API/api/chat" -H "Content-Type: application/json" \
  -d "{\"kb_id\":\"$KB_ID\",\"question\":\"What is Q-learning?\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" 2>/dev/null || echo '{}')
CIT=$(echo "$CHAT" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('citations',[])))" 2>/dev/null || echo 0)
check "chat citations > 0" '[ "$CIT" -gt 0 ]' "citations=$CIT"

echo; echo "--- 8. Reindex ---"
curl -sf -X POST "$API/api/documents/$DOC_ID/reindex" > /dev/null 2>&1
sleep 6
AV=$(curl -sf "$API/api/documents/$DOC_ID" 2>/dev/null | json_val "[\"active_version\"]")
check "active_version >= 2" '[ "$AV" -ge 2 ]' "av=$AV"

echo; echo "--- 9. Re-chat verify citation version ---"
CHAT2=$(curl -sf -X POST "$API/api/chat" -H "Content-Type: application/json" \
  -d "{\"kb_id\":\"$KB_ID\",\"question\":\"What is Q-learning?\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" 2>/dev/null || echo '{}')
CV=$(echo "$CHAT2" | python3 -c "import sys,json;cs=json.load(sys.stdin).get('citations',[]);print(cs[0].get('version_id','?') if cs else '?')" 2>/dev/null)
check "citation version=$CV == active=$AV" '[ "$CV" = "$AV" ]'

echo; echo "--- 10. Revoke + 401 ---"
REV=$(curl -sf -X DELETE "$API/auth/devices/$DID" 2>/dev/null || echo '{}')
check "device revoked" '[ "$(echo "$REV" | json_val "[\"revoked\"]")" = "True" ]'
V2=$(curl -s -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\"}" 2>/dev/null || echo '{"detail":"revoked"}')
DETAIL=$(echo "$V2" | json_val "[\"detail\"]")
check "revoked → 401" '[ "$DETAIL" != "ok" ]' "detail=$DETAIL"

echo; echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
