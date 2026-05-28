#!/bin/bash
# PersonalNotebook App Device Smoke Test — Phase 2C
# 模拟 App 设备验证流程：pairing → verify → KB list → revoke → 401
set +e

API="${API_URL:-http://localhost:8000}"
PASS=0; FAIL=0; TOKEN=""

check() { local l="$1" c="$2" d="$3"
  if eval "$c" 2>/dev/null; then echo "  ✅ $l"; ((PASS++))
  else echo "  ❌ $l — $d"; ((FAIL++)); fi
}
json_val() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d${1})" 2>/dev/null; }
http_code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "=========================================="
echo " App Device Smoke Test"
echo " API: $API"
echo "=========================================="

# 1. Create pairing token
echo; echo "--- 1. Pairing Create ---"
PAIR=$(curl -sf -X POST "$API/auth/pair/create" -H "Content-Type: application/json" \
  -d '{"tenant_id":"default","device_name":"smoke-test-device","expires_hours":1}' 2>/dev/null || echo '{}')
TOKEN=$(echo "$PAIR" | json_val "[\"token\"]")
DID=$(echo "$PAIR" | json_val "[\"device_id\"]")
check "pair create" '[ -n "$TOKEN" ]' "resp=$PAIR"

# 2. Verify token
echo; echo "--- 2. Pairing Verify ---"
VERIFY=$(curl -sf -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" \
  -d "{\"token\":\"$TOKEN\",\"device_name\":\"test-device\"}" 2>/dev/null || echo '{}')
check "pair verify" '[ "$(echo "$VERIFY" | json_val "[\"verified\"]")" = "True" ]'

# 3. List KB with token
echo; echo "--- 3. GET /api/kbs (Bearer) ---"
KB=$(curl -sf -H "Authorization: Bearer $TOKEN" "$API/api/kbs" 2>/dev/null || echo '{}')
KB_COUNT=$(echo "$KB" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('items',[])))" 2>/dev/null || echo 0)
CODE_KBS=$(http_code -H "Authorization: Bearer $TOKEN" "$API/api/kbs")
check "GET /kbs authorized" '[ "$CODE_KBS" = "200" ]' "got $CODE_KBS, $KB_COUNT KBs"

# 4. Without token → 401
echo; echo "--- 4. GET /api/kbs (no auth) → 401 ---"
CODE=$(http_code "$API/api/kbs")
check "no auth → 401" '[ "$CODE" = "401" ]' "got $CODE"

# 5. Revoke device
echo; echo "--- 5. Revoke ---"
REV=$(curl -sf -X DELETE "$API/auth/devices/$DID" 2>/dev/null || echo '{}')
check "device revoked" '[ "$(echo "$REV" | json_val "[\"revoked\"]")" = "True" ]'

# 6. Revoked token → 401
echo; echo "--- 6. Revoked verify → 401 ---"
CODE=$(http_code -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\"}")
check "revoked verify → 401" '[ "$CODE" = "401" ]' "got $CODE"

# 7. Revoked GET /kbs → 401
echo; echo "--- 7. Revoked GET /kbs → 401 ---"
CODE=$(http_code -H "Authorization: Bearer $TOKEN" "$API/api/kbs")
check "revoked GET /kbs → 401" '[ "$CODE" = "401" ]' "got $CODE"

echo; echo "=========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
