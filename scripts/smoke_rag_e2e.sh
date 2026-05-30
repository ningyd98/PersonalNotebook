#!/bin/bash
# Phase 3D: RAG E2E Smoke Test
# Usage: CORE_URL=http://localhost:8000 bash scripts/smoke_rag_e2e.sh
set +e

CORE="${CORE_URL:-http://localhost:8000}"
MODEL_GW="${MODEL_GW_URL:-http://localhost:8900}"
PASS=0; FAIL=0; SKIP=0

check() { local l="$1" c="$2" d="$3"
  if eval "$c" 2>/dev/null; then echo "  ✅ $l"; PASS=$((PASS+1))
  else echo "  ⚠️ $l — $d"; FAIL=$((FAIL+1)); fi
}
json_val() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d${1})" 2>/dev/null; }
http_code() { curl -sf -o /dev/null -w "%{http_code}" "$@"; }

echo "=========================================="
echo " RAG E2E Smoke Test"
echo " Core: $CORE  Gateway: $MODEL_GW"
echo "=========================================="

# 1. Health checks
echo ""; echo "--- 1. Services ---"
check "core health" 'curl -sf "$CORE/health" > /dev/null' "Core unreachable"
GW_STATUS=$(curl -sf "$MODEL_GW/health" 2>/dev/null || echo '{}')
if [ "$(echo "$GW_STATUS" | json_val '["status"]')" = "ok" ]; then
  echo "  ✅ model-gateway health"; PASS=$((PASS+1))
else
  echo "  ⚠️ model-gateway not running"; FAIL=$((FAIL+1))
fi

# 2. Pairing
echo ""; echo "--- 2. Pairing ---"
PAIR=$(curl -sf -X POST "$CORE/auth/pair/create" -H "Content-Type: application/json" -d '{"tenant_id":"default","device_name":"smoke-test"}' || echo '{}')
TOKEN=$(echo "$PAIR" | json_val '["token"]')
check "pair create" '[ -n "$TOKEN" ]'

# 3. KB + Doc
echo ""; echo "--- 3. KB + Upload ---"
KB=$(curl -sf -X POST "$CORE/api/kbs" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"smoke-test-kb"}' | json_val '["id"]')
check "create kb" '[ -n "$KB" ]'

TMP_MD=$(mktemp /tmp/smoke_test_XXXX.md)
cat > "$TMP_MD" << 'EOF'
# PersonalNotebook 系统简介

PersonalNotebook 是一个本地部署的个人知识库系统，支持 Markdown/PDF/图片等多种格式。

## 核心组件

- PostgreSQL: 存储文档元数据、用户、会话信息
- Qdrant: 向量数据库,存储文档切片的 embedding
- MinIO: 对象存储,保存原始文件和解析产物
- Redis: 缓存和 Celery 任务队列
- Celery: 异步处理文档解析、切片、嵌入生成

## RAG 问答流程

1. 用户上传文档
2. 文档解析: 提取文本、表格、代码块
3. 文档切片: 按段落/语义切分为 chunks
4. 嵌入生成: 每个 chunk 生成向量
5. 索引: 向量存入 Qdrant
6. 检索: 用户提问 → 向量检索 + BM25 → Rerank
7. 生成: 检索结果 → LLM 生成回答
EOF

DOC=$(curl -sf -X POST "$CORE/api/kbs/$KB/documents/upload" -H "Authorization: Bearer $TOKEN" -F "file=@$TMP_MD" | json_val '["document_id"]')
rm -f "$TMP_MD"
check "upload doc" '[ -n "$DOC" ]'

# 4. Wait READY
echo ""; echo "--- 4. Wait READY ---"
READY=0; S=""
for i in $(seq 1 30); do
  S=$(curl -sf -H "Authorization: Bearer $TOKEN" "$CORE/api/documents/$DOC" | json_val '["status"]')
  [ "$S" = "READY" ] && { READY=1; break; }
  echo "  [$i] status=$S"; sleep 2
done
check "doc READY" '[ "$READY" = "1" ]' "status=$S"

# 5. Chat (with evidence)
echo ""; echo "--- 5. Chat (evidence) ---"
CHAT=$(curl -sf -X POST "$CORE/api/chat" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"kb_id\":\"$KB\",\"question\":\"PersonalNotebook 使用什么组件做向量检索?\",\"top_k\":8,\"use_rerank\":true,\"strict_citation\":true}" || echo '{}')
ANSWER=$(echo "$CHAT" | json_val '["answer"]')
CIT_COUNT=$(echo "$CHAT" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('citations',[])))" 2>/dev/null || echo 0)
CONF=$(echo "$CHAT" | json_val '["confidence"]')
COV=$(echo "$CHAT" | json_val '["citation_coverage"]')
MODEL_ERR=$(echo "$CHAT" | json_val '["model_error"]')

if [ -n "$ANSWER" ] && [ "$ANSWER" != "null" ]; then
  check "answer non-empty" true
  echo "    answer: ${ANSWER:0:80}..."
else
  check "answer non-empty" false "empty answer"
fi

if [ "$CIT_COUNT" -gt 0 ] 2>/dev/null; then
  echo "  ✅ citations: $CIT_COUNT"; PASS=$((PASS+1))
  CID=$(echo "$CHAT" | python3 -c "import sys,json;cs=json.load(sys.stdin).get('citations',[]);print(cs[0].get('chunk_id','') if cs else '')" 2>/dev/null)
  echo "    first chunk_id: $CID"
  if [ -n "$CID" ] && [ "$CID" != "null" ]; then
    echo "  ✅ chunk_id exists"; PASS=$((PASS+1))
  fi
else
  if echo "$CHAT" | python3 -c "import sys,json;d=json.load(sys.stdin);e=d.get('model_error')" 2>/dev/null | grep -q "type"; then
    ET=$(echo "$CHAT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['model_error']['type'])" 2>/dev/null)
    echo "  ⚠️ INFRASTRUCTURE_BLOCKER: model_error type=$ET"
    FAIL=$((FAIL+1))
  else
    echo "  ⚠️ citations=0 (no model or no evidence)"; FAIL=$((FAIL+1))
  fi
fi

# 6. Chunk expand
echo ""; echo "--- 6. Chunk Expand ---"
if [ -n "$CID" ] && [ "$CID" != "null" ] && [ "$CID" != "" ]; then
  CHUNK=$(curl -sf -H "Authorization: Bearer $TOKEN" "$CORE/api/chunks/$CID" || echo '{}')
  CONTENT=$(echo "$CHUNK" | json_val '["content"]')
  DOCNAME=$(echo "$CHUNK" | json_val '["document_name"]')
  HAS_SP=$(echo "$CHUNK" | grep -c "storage_path" || echo 0)
  if [ -n "$CONTENT" ] && [ "$CONTENT" != "null" ]; then
    echo "  ✅ chunk content (len=${#CONTENT})"; PASS=$((PASS+1))
  else
    echo "  ❌ chunk content empty"; FAIL=$((FAIL+1))
  fi
  check "no storage_path in chunk" '[ "$HAS_SP" = "0" ]' "leaked storage_path"
fi

# 7. No-evidence question
echo ""; echo "--- 7. No-evidence refusal ---"
REFUSAL=$(curl -sf -X POST "$CORE/api/chat" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "{\"kb_id\":\"$KB\",\"question\":\"火星基地预算 2027 年具体金额\",\"top_k\":4,\"strict_citation\":true}" || echo '{}')
REF=$(echo "$REFUSAL" | json_val '["refusal"]')
SHOULD_REF=$(echo "$REFUSAL" | json_val '["should_refuse"]')
SUGGESTED=$(echo "$REFUSAL" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('suggested_actions',[])))" 2>/dev/null || echo 0)
if [ "$REF" = "True" ] || [ "$SHOULD_REF" = "True" ]; then
  echo "  ✅ refusal=$REF should_refuse=$SHOULD_REF"; PASS=$((PASS+1))
else
  echo "  ⚠️ refusal not triggered (maybe model generated answer?)"; FAIL=$((FAIL+1))
fi
check "suggested_actions" '[ "$SUGGESTED" -gt 0 ]' "no suggested actions"

# Summary
echo ""; echo "=========================================="
echo " Results: $PASS passed, $FAIL failed, $SKIP skipped"
echo "=========================================="
if [ "$FAIL" -gt 0 ]; then
  echo "INFRASTRUCTURE_BLOCKER: Some checks failed — review above"
fi
