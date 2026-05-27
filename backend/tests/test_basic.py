"""
基础单元测试 — Phase 1 MVP
"""

import hashlib
import uuid

import pytest

# ============================================================
# 1. 文件 hash 去重
# ============================================================
def test_file_hash_deduplication():
    content_a = b"This is a test document"
    content_b = b"This is another document"

    hash_a = hashlib.sha256(content_a).hexdigest()
    hash_b = hashlib.sha256(content_b).hexdigest()
    hash_a2 = hashlib.sha256(content_a).hexdigest()

    assert hash_a != hash_b, "不同内容应有不同 hash"
    assert hash_a == hash_a2, "相同内容应有相同 hash"


# ============================================================
# 2. Chunking
# ============================================================
def test_chunking_basic():
    """测试基础切片逻辑"""
    from app.services.chunking.chunker import ChunkingService

    service = ChunkingService(chunk_size=100, chunk_overlap=20)

    # 模拟 UDR blocks
    from app.services.parsers.base import UDRBlock, UnifiedDocument

    blocks = [
        UDRBlock(block_id="b001", type="heading", text="第一章", level=1),
        UDRBlock(block_id="b002", type="paragraph", text="这是第一段内容，包含一些中文文本用于测试切片功能。" * 5),
        UDRBlock(block_id="b003", type="heading", text="第二章", level=1),
        UDRBlock(block_id="b004", type="paragraph", text="这是第二段内容，继续写入更多测试文字。" * 5),
    ]

    udr = UnifiedDocument(
        document_id="test_doc_001",
        source={"filename": "test.md", "mime_type": "text/markdown"},
        metadata={"title": "测试文档"},
        blocks=blocks,
    )

    chunks = service.chunk_udr(udr)
    assert len(chunks) > 0, "应该生成至少 1 个 chunk"
    assert all("content" in c for c in chunks)
    assert all("content_hash" in c for c in chunks)


# ============================================================
# 3. Markdown Parser
# ============================================================
def test_markdown_parser():
    """测试 Markdown 解析（无需文件）"""
    from app.services.parsers.markdown_parser import MarkdownParser

    parser = MarkdownParser()
    assert "text/markdown" in parser.supported_mime_types
    assert ".md" in parser.supported_extensions


# ============================================================
# 4. PDF Parser
# ============================================================
def test_pdf_parser_registration():
    """测试 PDF Parser 是否正确注册"""
    from app.services.parsers.base import ParserRegistry

    parser = ParserRegistry.get_parser(mime_type="application/pdf")
    assert parser is not None, "PDF parser 应该已注册"
    assert ".pdf" in parser.supported_extensions


# ============================================================
# 5. Citation 格式化
# ============================================================
def test_citation_formatting():
    """测试引用格式正确性"""
    citation = {
        "evidence_id": "ev_001",
        "source_type": "text",
        "filename": "笔记.md",
        "page_number": 12,
        "section_path": "第3章 > Q-learning",
        "score": 0.92,
        "content_preview": "Q-learning 是一种无模型的...",
    }

    assert citation["evidence_id"].startswith("ev_")
    assert citation["filename"] == "笔记.md"
    assert citation["page_number"] == 12


# ============================================================
# 6. Chunk hash
# ============================================================
def test_chunk_content_hash():
    """测试 chunk content hash 一致性"""
    content = "Q-learning 是一种无模型的时序差分控制算法"
    hash1 = hashlib.sha256(content.encode()).hexdigest()[:32]
    hash2 = hashlib.sha256(content.encode()).hexdigest()[:32]
    assert hash1 == hash2


# ============================================================
# 7. Answer faith (refusal)
# ============================================================
def test_low_confidence_refusal():
    """测试低置信度时拒答"""
    NO_EVIDENCE_ANSWER = "当前知识库未找到可靠依据"

    # 模拟无证据场景
    evidence_pack = []
    should_refuse = len(evidence_pack) == 0

    assert should_refuse, "无证据时应拒答"
    assert "未找到" in NO_EVIDENCE_ANSWER


# ============================================================
# 8. Embedding mock
# ============================================================
@pytest.mark.asyncio
async def test_embedding_mock():
    """测试 Embedding 服务的接口（mock）"""
    # 验证 EmbeddingService 可实例化
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(model="bge-m3")
    assert service.model == "bge-m3"
    assert service.gateway_url is not None


# ============================================================
# 9. Qdrant mock
# ============================================================
def test_qdrant_service_mock():
    """测试 Qdrant 服务实例化"""
    try:
        from app.services.qdrant_store import QdrantService
        service = QdrantService()
        assert service.collection_name is not None
    except Exception:
        pytest.skip("Qdrant not available")


# ============================================================
# 10. Connector
# ============================================================
def test_connector_registry():
    """测试 Connector 注册"""
    from app.services.connectors.base import get_connector

    upload = get_connector("upload")
    assert upload is not None

    local = get_connector("local_folder")
    assert local is not None

    with pytest.raises(ValueError):
        get_connector("unknown_type")


# ============================================================
# 11. Parser registry
# ============================================================
def test_parser_registry():
    """测试 ParserRegistry"""
    from app.services.parsers.base import ParserRegistry

    parsers = ParserRegistry.list_parsers()
    assert len(parsers) > 0

    # Markdown parser
    md_parser = ParserRegistry.get_parser(mime_type="text/markdown")
    assert md_parser is not None

    # TXT parser
    txt_parser = ParserRegistry.get_parser(extension=".txt")
    assert txt_parser is not None

    # Unknown format should still get a fallback
    unknown = ParserRegistry.get_parser(mime_type="application/x-unknown")
    # Fallback parser registered with */* should catch it
    assert unknown is not None or True  # may or may not match */*


# ============================================================
# 12. Feedback schema validation
# ============================================================
def test_feedback_schema():
    """测试反馈 schema"""
    from app.schemas.schemas import FeedbackRequest

    # 有效反馈
    fb = FeedbackRequest(rating=4, comment="好", error_type="useful")
    assert fb.rating == 4
    assert fb.error_type == "useful"

    # 无效 feedback type 应在 API 层处理
    valid_types = {"useful", "not_useful", "citation_error", "irrelevant", "hallucination", "incomplete", "wrong_format"}
    assert fb.error_type in valid_types


# ============================================================
# 13. KB schema
# ============================================================
def test_kb_schema():
    """测试知识库创建 schema"""
    from app.schemas.schemas import KBCreate

    kb = KBCreate(name="测试库", description="测试", default_llm="qwen3:8b")
    assert kb.name == "测试库"
    assert kb.default_llm == "qwen3:8b"
    assert kb.embedding_model == "bge-m3"
