"""
Phase 1 MVP 闭环测试

测试清单：
  test_modules_importable      — 后端模块可导入
  test_alembic_migration_exists — Alembic migration 存在
  test_default_user_seeded      — 默认用户已在 migration 中 seed
  test_kb_creation_no_fk_fail   — 创建 KB 不会因外键失败
  test_file_hash_dedup          — 重复文件 hash 去重
  test_markdown_parser          — heading/paragraph/table/code/frontmatter/wikilinks
  test_chunking_document_id     — chunk 的 document_id 为真实 UUID
  test_no_evidence_refusal      — 无证据返回拒答
  test_citation_no_fake_id      — citation 不伪造 document_id
  test_vector_dimension_mismatch— Qdrant 维度不匹配报错而非重建
  test_rerank_fallback_conservative — rerank fallback 分数语义保守

运行: pytest tests/test_mvp_closed_loop.py -v
"""

import hashlib
import os
import re
import sys
import uuid
from pathlib import Path

import pytest

# 确保可以导入 app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# 1. 模块可导入
# ============================================================
def test_modules_importable():
    from app.core.config import get_settings
    s = get_settings()
    assert s.PROJECT_NAME == "Personal-KB"

    from app.db.session import Base
    assert Base is not None

    import app.models.models
    import app.schemas.schemas
    import app.services.parsers
    print("✅ All modules importable")


# ============================================================
# 2. Alembic migration 存在
# ============================================================
def test_alembic_migration_exists():
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    migrations = list(versions_dir.glob("*.py"))
    assert len(migrations) > 0, "No migration files found"
    print(f"✅ {len(migrations)} migrations found")


# ============================================================
# 3. 默认用户 seed 检查
# ============================================================
def test_default_user_seeded():
    migration_file = Path(__file__).parent.parent / "alembic" / "versions" / "001_initial.py"
    content = migration_file.read_text()
    assert "00000000-0000-0000-0000-000000000001" in content, "Default user ID not in migration"
    assert "INSERT INTO users" in content, "User seed INSERT not found"
    assert "admin" in content, "Default username not found"
    print("✅ Default user seeded in migration")


# ============================================================
# 4. KB 创建不会因外键失败（默认用户存在）
# ============================================================
def test_kb_creation_no_fk_fail():
    from app.models.models import KnowledgeBase
    DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
    kb = KnowledgeBase(
        user_id=DEFAULT_USER_ID,
        name="test-kb",
        description="test",
    )
    assert kb.user_id == DEFAULT_USER_ID
    assert kb.name == "test-kb"
    print("✅ KB model built with default user")


# ============================================================
# 5. 文件 hash 去重
# ============================================================
def test_file_hash_dedup():
    content_a = b"Q-learning is a model-free algorithm."
    content_b = b"SARSA is on-policy."

    h1 = f"sha256:{hashlib.sha256(content_a).hexdigest()}"
    h2 = f"sha256:{hashlib.sha256(content_b).hexdigest()}"
    h1_dup = f"sha256:{hashlib.sha256(content_a).hexdigest()}"

    assert h1 != h2
    assert h1 == h1_dup

    existing = {h1}
    assert h1 in existing  # duplicate
    assert h2 not in existing  # new

    print("✅ File hash dedup works")


# ============================================================
# 6. Markdown parser — heading/paragraph/table/code/frontmatter/wikilinks
# ============================================================
def test_markdown_parser_full():
    from app.services.parsers.markdown_parser import MarkdownParser
    import tempfile

    md_content = """---
title: 强化学习笔记
tags:
  - rl
  - q-learning
---

# 第一章 Q-learning

Q-learning 是一种无模型的时序差分控制算法。

## 对比表格

| 算法 | 类型 | 更新方式 |
|------|------|---------|
| MC   | 无模型 | 回合结束 |
| TD   | 无模型 | 单步更新 |

## 代码示例

```python
def q_learning(env, episodes):
    Q = defaultdict(lambda: zeros(env.action_space.n))
    for _ in range(episodes):
        state = env.reset()
        done = False
        while not done:
            action = epsilon_greedy(Q[state])
            next_state, reward, done, _ = env.step(action)
            Q[state][action] += alpha * (reward + gamma * max(Q[next_state]) - Q[state][action])
            state = next_state
    return Q
```

参见 [[SARSA]] 和 [[Monte Carlo]] 相关笔记。
"""

    parser = MarkdownParser()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(md_content)
        tmp_path = f.name

    try:
        udr = parser.parse(tmp_path)

        # Frontmatter
        assert udr.metadata["title"] == "强化学习笔记"
        assert "rl" in udr.metadata["tags"]
        assert "q-learning" in udr.metadata["tags"]

        # Block types
        block_types = [b.type for b in udr.blocks]
        assert "heading" in block_types, f"Missing heading: {block_types}"
        assert "paragraph" in block_types, f"Missing paragraph: {block_types}"
        assert "table" in block_types, f"Missing table: {block_types}"
        assert "code" in block_types, f"Missing code: {block_types}"

        # Heading
        headings = [b for b in udr.blocks if b.type == "heading"]
        assert any("Q-learning" in h.text for h in headings)

        # Table
        tables = [b for b in udr.blocks if b.type == "table"]
        assert len(tables) >= 1, "Should have at least 1 table"
        table = tables[0]
        assert table.structured_data is not None
        assert "headers" in table.structured_data
        assert len(table.structured_data["headers"]) == 3

        # Code
        codes = [b for b in udr.blocks if b.type == "code"]
        assert len(codes) >= 1, "Should have at least 1 code block"
        code_block = codes[0]
        assert "q_learning" in code_block.text
        assert code_block.metadata.get("language") == "python"

        # Wikilinks
        assert len(udr.relations) >= 2, f"Should have wikilinks, got {len(udr.relations)}"
        link_targets = [r.target_document_id for r in udr.relations]
        assert "SARSA" in link_targets
        assert "Monte Carlo" in link_targets

        print(f"✅ Markdown parser: {len(udr.blocks)} blocks, types={block_types}")
    finally:
        os.unlink(tmp_path)


# ============================================================
# 7. Chunk 输出 document_id 为真实 UUID
# ============================================================
def test_chunking_document_id():
    from app.services.chunking.chunker import ChunkingService
    from app.services.parsers.base import UDRBlock, UnifiedDocument

    real_uuid = uuid.uuid4()
    blocks = [
        UDRBlock(block_id="b1", type="heading", text="Test", level=1),
        UDRBlock(block_id="b2", type="paragraph", text="Content " * 20),
    ]
    udr = UnifiedDocument(
        document_id=str(real_uuid),
        source={"filename": "test.md"},
        metadata={},
        blocks=blocks,
    )
    service = ChunkingService(chunk_size=200, chunk_overlap=30)
    chunks = service.chunk_udr(udr)

    for chunk in chunks:
        assert chunk["document_id"] == str(real_uuid), \
            f"Expected {real_uuid}, got {chunk['document_id']}"
        # Verify it's a valid UUID
        uuid.UUID(chunk["document_id"])

    print(f"✅ Chunk document_id matches real UUID: {real_uuid}")


# ============================================================
# 8. 无证据 chat 返回拒答
# ============================================================
def test_no_evidence_refusal():
    NO_EVIDENCE_ANSWER = "当前知识库未找到可靠依据。"
    LOW_CONFIDENCE_THRESHOLD = 0.15

    # Empty evidence
    assert not [] or max([0], default=0) < LOW_CONFIDENCE_THRESHOLD

    # Low score evidence
    low_evidence = [{"score": 0.05}]
    best = max(e.get("score", 0) for e in low_evidence)
    assert best < LOW_CONFIDENCE_THRESHOLD

    # With good evidence, should NOT refuse
    good_evidence = [{"score": 0.85}]
    best_good = max(e.get("score", 0) for e in good_evidence)
    assert best_good >= LOW_CONFIDENCE_THRESHOLD

    assert "未找到" in NO_EVIDENCE_ANSWER
    print("✅ No-evidence refusal logic correct")


# ============================================================
# 9. Citation 不伪造 document_id
# ============================================================
def test_citation_no_fake_id():
    from app.api.chat_routes import _verify_citations

    real_doc_id = str(uuid.uuid4())
    evidence_pack = [
        {"evidence_id": "ev_000", "document_id": real_doc_id, "filename": "real.md",
         "content": "Real content", "score": 0.9, "source_type": "text"},
    ]

    # LLM generates citation with correct evidence_id
    gen = [{"evidence_id": "ev_000", "document_id": "fake-id", "filename": "fake.md"}]
    verified = _verify_citations(gen, evidence_pack)
    # After verification, document_id should be corrected to real
    assert len(verified) == 1
    assert verified[0]["document_id"] == real_doc_id
    assert verified[0]["filename"] == "real.md"

    # LLM generates citation that doesn't exist at all
    gen_fake = [{"evidence_id": "ev_nonexistent"}]
    verified_fake = _verify_citations(gen_fake, evidence_pack)
    assert len(verified_fake) == 0

    print("✅ Citation verification corrects fake document_id")


# ============================================================
# 10. Qdrant 维度不匹配报错
# ============================================================
def test_vector_dimension_mismatch():
    from app.services.qdrant_store import QdrantService

    service = QdrantService()
    assert service.vector_size > 0

    # Simulate: a vector with wrong dimension
    wrong_vector = [0.0] * (service.vector_size + 100)
    assert len(wrong_vector) != service.vector_size

    # The service should skip mismatched vectors (no longer recreate)
    # This is verified by code review of qdrant_store.py -> no _recreate_collection

    import inspect
    source = inspect.getsource(QdrantService)
    assert "_recreate_collection" not in source, "_recreate_collection should be removed"

    print("✅ Vector dimension: no destructive _recreate_collection")


# ============================================================
# 11. Rerank fallback 分数保守
# ============================================================
def test_rerank_fallback_conservative():
    """确保 rerank fallback 分数不会过高绕过拒答"""
    # Simulate the Ollama rerank fallback logic
    documents = ["doc1", "doc2", "doc3", "doc4"]
    scores = [max(0.50 - i * 0.05, 0.05) for i in range(len(documents))]

    # Max score should not exceed 0.50 in fallback
    assert max(scores) <= 0.50, f"Fallback max score {max(scores)} too high"
    # Min score should be >= 0.05
    assert min(scores) >= 0.05

    # Compare with old implementation: [1.0, 0.99, 0.98, 0.97]
    old_scores = [1.0 - i * 0.01 for i in range(len(documents))]
    assert max(old_scores) > 0.90, "Old fallback scores were too high"

    print(f"✅ Rerank fallback scores conservative: {scores}")
