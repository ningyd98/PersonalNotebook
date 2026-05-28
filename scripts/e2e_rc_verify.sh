#!/bin/bash
# PersonalNotebook RC Verification — Phase 2F
# 全链路验收: Core → Security → Chat → Citations
set +e

API="${API_URL:-http://localhost:8000}"
MODEL_GW="${MODEL_GW_URL:-http://localhost:8900}"
PASS=0; FAIL=0; TOKEN=""; KB_ID=""; DOC_ID=""; DID=""

check() { local l="$1" c="$2" d="$3"
  if eval "$c" 2>/dev/null; then echo "  ✅ $l"; PASS=$((PASS+1))
  else echo "  ❌ $l — $d"; FAIL=$((FAIL+1)); fi
}
json_val() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d${1})" 2>/dev/null; }
http_code() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "=========================================="
echo " PersonalNotebook RC Verification"
echo " API: $API  ModelGW: $MODEL_GW"
echo "=========================================="

# ── Phase 1: Services ─────────────────────────────
echo ""; echo "--- Phase 1: Service Health ---"
CORES=$(curl -sf "$API/health" 2>/dev/null | json_val '["status"]')
check "core health" '[ "$CORES" = "ok" ]' "got $CORES"
GW=$(curl -sf "$MODEL_GW/health" 2>/dev/null | json_val '["status"]')
check "model-gateway" '[ "$GW" = "ok" ]' "got $GW"

# ── Phase 2: Security ─────────────────────────────
echo ""; echo "--- Phase 2: Security ---"
# No auth → 401
C1=$(http_code "$API/api/kbs")
check "GET /kbs no auth → 401" '[ "$C1" = "401" ]' "got $C1"

# Pairing
PAIR=$(curl -sf -X POST "$API/auth/pair/create" -H "Content-Type: application/json" -d '{"tenant_id":"default","device_name":"rc-verify","expires_hours":1}' 2>/dev/null || echo '{}')
TOKEN=$(echo "$PAIR" | json_val '["token"]')
DID=$(echo "$PAIR" | json_val '["device_id"]')
check "pair create" '[ -n "$TOKEN" ]'

VERIFY=$(curl -sf -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\"}" 2>/dev/null || echo '{}')
check "pair verify" '[ "$(echo "$VERIFY" | json_val '["verified"]')" = "True" ]'
check "no token_hash in verify" '[ -z "$(echo "$VERIFY" | json_val '["token_hash_prefix"]')" ]'

# Auth token → 200
C2=$(http_code -H "Authorization: Bearer $TOKEN" "$API/api/kbs")
check "GET /kbs with token → 200" '[ "$C2" = "200" ]' "got $C2"

# Revoke
REV=$(curl -sf -X DELETE "$API/auth/devices/$DID" 2>/dev/null || echo '{}')
check "revoke" '[ "$(echo "$REV" | json_val '["revoked"]')" = "True" ]'
C3=$(http_code -H "Authorization: Bearer $TOKEN" "$API/api/kbs")
check "revoked GET /kbs → 401" '[ "$C3" = "401" ]' "got $C3"

# ── Phase 3: KB + Document ────────────────────────
echo ""; echo "--- Phase 3: KB + Document ---"
# Get fresh token
PAIR2=$(curl -sf -X POST "$API/auth/pair/create" -H "Content-Type: application/json" -d '{"tenant_id":"default","device_name":"rc-verify2","expires_hours":1}' 2>/dev/null || echo '{}')
TOKEN=$(echo "$PAIR2" | json_val '["token"]')
DID=$(echo "$PAIR2" | json_val '["device_id"]')
curl -sf -X POST "$API/auth/pair/verify" -H "Content-Type: application/json" -d "{\"token\":\"$TOKEN\"}" > /dev/null 2>&1

KB=$(curl -sf -X POST "$API/api/kbs" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"name":"rc-verify-kb"}' 2>/dev/null || echo '{}')
KB_ID=$(echo "$KB" | json_val '["id"]')
check "create kb" '[ -n "$KB_ID" ]'

TMP_MD=$(mktemp /tmp/rc_verify_XXXX.md)
cat > "$TMP_MD" << 'MDEOF'
---
title: RC Verification
tags: [rc, verify]
---
# Q-learning
Q-learning is a model-free reinforcement learning algorithm by Watkins 1989.
Q(s,a) ← Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
MDEOF
UP=$(curl -sf -X POST "$API/api/kbs/$KB_ID/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$TMP_MD" 2>/dev/null || echo '{}')
DOC_ID=$(echo "$UP" | json_val '["document_id"]')
check "upload doc" '[ -n "$DOC_ID" ]'
rm -f "$TMP_MD"

READY=0; S=""
for i in $(seq 1 30); do
  S=$(curl -sf "$API/api/documents/$DOC_ID" -H "Authorization: Bearer $TOKEN" 2>/dev/null | json_val '["status"]')
  [ "$S" = "READY" ] && { READY=1; break; }
  sleep 2
done
check "doc READY" '[ "$READY" = "1" ]' "status=$S"

# ── Phase 4: Chat + Citations ─────────────────────
echo ""; echo "--- Phase 4: Chat + Citations ---"
CHAT=$(curl -sf -X POST "$API/api/chat" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"kb_id\":\"$KB_ID\",\"question\":\"What is Q-learning?\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" 2>/dev/null || echo '{}')
ANSWER=$(echo "$CHAT" | json_val '["answer"]')
check "chat answer non-empty" '[ -n "$ANSWER" ]' "len=${#ANSWER}"
CIT=$(echo "$CHAT" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('citations',[])))" 2>/dev/null || echo 0)
check "chat citations > 0" '[ "$CIT" -gt 0 ]' "citations=$CIT"
VER_ID=$(echo "$CHAT" | python3 -c "import sys,json;cs=json.load(sys.stdin).get('citations',[]);print(cs[0].get('version_id','?') if cs else '?')" 2>/dev/null)
AV=$(curl -sf "$API/api/documents/$DOC_ID" -H "Authorization: Bearer $TOKEN" 2>/dev/null | json_val '["active_version"]')
check "citation version matches active" '[ "$VER_ID" = "$AV" ]' "citation=$VER_ID active=$AV"

# ── Phase 5: Diagnostics ──────────────────────────
echo ""; echo "--- Phase 5: Diagnostics ---"
DIAG=$(curl -sf -X POST "$API/api/chat/debug" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"kb_id\":\"$KB_ID\",\"question\":\"What is Q-learning?\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" 2>/dev/null || echo '{}')
COV=$(echo "$DIAG" | json_val '["citation_coverage"]')
check "debug citation_coverage > 0" '[ "$COV" != "null" ]' "coverage=$COV"

echo ""; echo "=========================================="
echo " RC Results: $PASS passed, $FAIL failed"
echo "=========================================="
[ "$FAIL" -eq 0 ]
