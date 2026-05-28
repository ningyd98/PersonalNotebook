#!/bin/bash
# PersonalNotebook App E2E Acceptance — Phase 2B
set +e

API="${API_URL:-http://localhost:8000}"
PASS=0; FAIL=0; TOKEN=""

check() { local l="$1" c="$2" d="$3"
  if eval "$c" 2>/dev/null; then echo "  ✅ $l"; ((PASS++))
  else echo "  ❌ $l — $d"; ((FAIL++)); fi
}
json_val() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d${1})" 2>/dev/null; }
http_code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }
api_get()  { curl -sf -H "Authorization: Bearer $TOKEN" "$@" 2>/dev/null || echo '{}'; }
api_post() { curl -sf -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" "$@" 2>/dev/null || echo '{}'; }

echo "=========================================="
echo " PersonalNotebook App E2E Acceptance"
echo " API: $API"
echo "=========================================="

echo; echo "--- 1. Health ---"
H=$(curl -sf "$API/health" 2>/dev/null || echo '{"status":"error"}')
check "health ok" '[ "$(echo "$H" | json_val "[\"status\"]")" = "ok" ]' "$H"

echo; echo "--- 2. Pairing Create ---"
PAIR=$(curl -sf -X POST "$API/auth/pair/create" -H "Content-Type: application/json" -d '{"tenant_id":"default","device_name":"e2e-test","expires_hours":1}' 2>/dev/null || echo '{}')
TOKEN=$(echo "$PAIR" | json_val "[\"token\"]")
DID=$(echo "$PAIR" | json_val "[\"device_id\"]")
check "pair create" '[ -n "$TOKEN" ]' "resp=$PAIR"

echo; echo "--- 3. Pairing Verify ---"
VERIFY=$(curl -sf -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\",\"device_name\":\"e2e-phone\"}" 2>/dev/null || echo '{}')
check "pair verify" '[ "$(echo "$VERIFY" | json_val "[\"verified\"]")" = "True" ]' "$VERIFY"
check "no token_hash_prefix" '[ -z "$(echo "$VERIFY" | json_val "[\"token_hash_prefix\"]")" ]'

echo; echo "--- 4. No auth → 401 ---"
CODE=$(http_code "$API/api/kbs")
check "GET /kbs no auth → 401" '[ "$CODE" = "401" ]' "got $CODE"

echo; echo "--- 5. Create KB (Bearer) ---"
KB=$(api_post "$API/api/kbs" -d '{"name":"e2e-app-test"}')
KB_ID=$(echo "$KB" | json_val "[\"id\"]")
check "create kb" '[ -n "$KB_ID" ]'

echo; echo "--- 6. Upload ---"
TMP_MD=$(mktemp /tmp/e2e_app_XXXX.md)
cat > "$TMP_MD" << 'MDEOF'
---
title: E2E App Test
---
# Q-learning
Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]
MDEOF
UP=$(curl -sf -X POST "$API/api/kbs/$KB_ID/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$TMP_MD" 2>/dev/null || echo '{}')
DOC_ID=$(echo "$UP" | json_val "[\"document_id\"]")
check "upload" '[ -n "$DOC_ID" ]'
rm -f "$TMP_MD"

echo; echo "--- 7. Wait READY ---"
READY=0; S=""
for i in $(seq 1 30); do
  S=$(api_get "$API/api/documents/$DOC_ID" | json_val "[\"status\"]")
  [ "$S" = "READY" ] && { READY=1; break; }
  sleep 2
done
check "doc READY" '[ "$READY" = "1" ]' "status=$S"

echo; echo "--- 8. Chat (Bearer) ---"
CHAT=$(api_post "$API/api/chat" -d '{"kb_id":"'"$KB_ID"'","question":"What is Q-learning?","top_k":8,"use_rerank":true,"strict_citation":true}')
CIT=$(echo "$CHAT" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('citations',[])))" 2>/dev/null || echo 0)
check "chat citations > 0" '[ "$CIT" -gt 0 ]' "citations=$CIT"

echo; echo "--- 9. Reindex ---"
api_post "$API/api/documents/$DOC_ID/reindex" > /dev/null
sleep 6
AV=$(api_get "$API/api/documents/$DOC_ID" | json_val "[\"active_version\"]")
check "active_version >= 2" '[ "$AV" -ge 2 ]' "av=$AV"

echo; echo "--- 10. Citation version check ---"
CHAT2=$(api_post "$API/api/chat" -d '{"kb_id":"'"$KB_ID"'","question":"What is Q-learning?","top_k":8,"use_rerank":true,"strict_citation":true}')
CV=$(echo "$CHAT2" | python3 -c "import sys,json;cs=json.load(sys.stdin).get('citations',[]);print(cs[0].get('version_id','?') if cs else '?')" 2>/dev/null)
check "citation v$CV == active v$AV" '[ "$CV" = "$AV" ]'

echo; echo "--- 11. Revoke ---"
REV=$(curl -sf -X DELETE "$API/auth/devices/$DID" 2>/dev/null || echo '{}')
check "device revoked" '[ "$(echo "$REV" | json_val "[\"revoked\"]")" = "True" ]'

echo; echo "--- 12. Revoked verify → 401 ---"
CODE=$(http_code -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\"}")
check "revoked verify → 401" '[ "$CODE" = "401" ]' "got $CODE"

echo; echo "--- 13. Revoked GET /kbs → 401 ---"
CODE2=$(http_code -H "Authorization: Bearer $TOKEN" "$API/api/kbs")
check "revoked GET /kbs → 401" '[ "$CODE2" = "401" ]' "got $CODE2"

echo; echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
