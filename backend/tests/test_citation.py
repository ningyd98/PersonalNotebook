"""
引用格式测试

测试内容：
- 不同来源类型的引用格式化
- 文档引用、PPT引用、Excel引用、图片引用、音频引用、视频引用、代码引用
- 引用验证（_verify_citations）
- Citation 对象构建

运行: pytest tests/test_citation.py -v
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# 引用格式化 — 基于 source_type 的引用信息
# ============================================================
class TestCitationFormatting:
    """不同来源类型的引用格式化"""

    def test_document_citation(self):
        """文档引用应包含 filename / page / section_path"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "source_type": "text",
                "filename": "report.pdf",
                "content": "这是文档内容",
                "score": 0.9,
                "page_number": 5,
                "section_path": "第一章 > 1.1 概述",
            },
        ]

        # LLM 返回正确 evidence_id
        generated = [{"evidence_id": "ev_000"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        cit = verified[0]
        assert cit["document_id"] == doc_id
        assert cit["filename"] == "report.pdf"
        assert cit["source_type"] == "text"

    def test_ppt_citation(self):
        """PPT 引用应包含 slide_number"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_001",
                "document_id": doc_id,
                "source_type": "text",
                "filename": "presentation.pptx",
                "content": "幻灯片内容",
                "score": 0.85,
                "slide_number": 3,
            },
        ]

        generated = [{"evidence_id": "ev_001"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["filename"] == "presentation.pptx"
        assert verified[0].get("page_number") is None or verified[0].get("slide_number") == 3

    def test_excel_citation(self):
        """Excel 引用应包含 sheet_name / cell_range 信息（如果有）"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_002",
                "document_id": doc_id,
                "source_type": "table",
                "filename": "data.xlsx",
                "content": "表格数据内容",
                "score": 0.88,
                "section_path": "Sheet1",
            },
        ]

        generated = [{"evidence_id": "ev_002"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["source_type"] == "table"
        assert verified[0]["filename"] == "data.xlsx"

    def test_image_citation(self):
        """图片引用应标记 source_type=image"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_003",
                "document_id": doc_id,
                "source_type": "image",
                "filename": "diagram.png",
                "content": "[OCR] 架构图中的组件关系",
                "score": 0.75,
            },
        ]

        generated = [{"evidence_id": "ev_003"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["source_type"] == "image"
        assert "OCR" in verified[0]["content_preview"] or "OCR" in verified[0].get("evidence_text", "")

    def test_audio_citation(self):
        """音频引用应标记 source_type=audio"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_004",
                "document_id": doc_id,
                "source_type": "audio",
                "filename": "meeting.mp3",
                "content": "转写文本：会议讨论了项目进度",
                "score": 0.82,
            },
        ]

        generated = [{"evidence_id": "ev_004"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["source_type"] == "audio"

    def test_video_citation(self):
        """视频引用应标记 source_type=video"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_005",
                "document_id": doc_id,
                "source_type": "video",
                "filename": "lecture.mp4",
                "content": "视频转写：讲座内容",
                "score": 0.79,
            },
        ]

        generated = [{"evidence_id": "ev_005"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["source_type"] == "video"

    def test_code_citation(self):
        """代码引用应标记 source_type=code"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_006",
                "document_id": doc_id,
                "source_type": "code",
                "filename": "main.py",
                "content": "def hello():\n    print('Hello')",
                "score": 0.91,
            },
        ]

        generated = [{"evidence_id": "ev_006"}]
        verified = _verify_citations(generated, evidence_pack)

        assert len(verified) == 1
        assert verified[0]["source_type"] == "code"


# ============================================================
# 引用验证
# ============================================================
class TestCitationVerification:
    """引用验证逻辑测试"""

    def test_correct_evidence_id(self):
        """正确的 evidence_id 应通过验证"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "real.md",
                "content": "Real content",
                "score": 0.9,
                "source_type": "text",
            },
        ]

        generated = [{"evidence_id": "ev_000"}]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 1
        assert verified[0]["document_id"] == doc_id
        assert verified[0]["filename"] == "real.md"

    def test_fake_document_id_corrected(self):
        """LLM 伪造的 document_id 应被纠正为 evidence_pack 中的真实 ID"""
        from app.api.chat_routes import _verify_citations

        real_doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": real_doc_id,
                "filename": "real.md",
                "content": "Real content",
                "score": 0.9,
                "source_type": "text",
            },
        ]

        generated = [
            {
                "evidence_id": "ev_000",
                "document_id": "fake-id",
                "filename": "fake.md",
            }
        ]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 1
        assert verified[0]["document_id"] == real_doc_id
        assert verified[0]["filename"] == "real.md"

    def test_nonexistent_evidence_id_filtered(self):
        """不存在的 evidence_id 应被过滤"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "real.md",
                "content": "Real content",
                "score": 0.9,
                "source_type": "text",
            },
        ]

        generated = [{"evidence_id": "ev_nonexistent"}]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 0

    def test_mixed_valid_and_invalid(self):
        """混合有效和无效 evidence_id"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "doc1.md",
                "content": "Content 1",
                "score": 0.9,
                "source_type": "text",
            },
            {
                "evidence_id": "ev_001",
                "document_id": doc_id,
                "filename": "doc2.md",
                "content": "Content 2",
                "score": 0.8,
                "source_type": "text",
            },
        ]

        generated = [
            {"evidence_id": "ev_000"},
            {"evidence_id": "ev_999"},  # 无效
            {"evidence_id": "ev_001"},
        ]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 2
        verified_ids = [v["evidence_id"] for v in verified]
        assert "ev_000" in verified_ids
        assert "ev_001" in verified_ids

    def test_empty_generated_citations_auto_construct(self):
        """空 generated_citations 时应自动从 evidence_pack 构造"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "auto.md",
                "content": "Auto constructed content",
                "score": 0.9,
                "source_type": "text",
            },
            {
                "evidence_id": "ev_001",
                "document_id": doc_id,
                "filename": "auto2.md",
                "content": "More content",
                "score": 0.8,
                "source_type": "text",
            },
        ]

        verified = _verify_citations([], evidence_pack)
        # 应自动构造引用
        assert len(verified) >= 1
        assert all("evidence_id" in v for v in verified)

    def test_empty_evidence_pack(self):
        """空 evidence_pack 应返回空"""
        from app.api.chat_routes import _verify_citations

        verified = _verify_citations([{"evidence_id": "ev_000"}], [])
        assert len(verified) == 0

    def test_content_preview_truncated(self):
        """content_preview 应被截断到 200 字符"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        long_content = "A" * 1000
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "long.md",
                "content": long_content,
                "score": 0.9,
                "source_type": "text",
            },
        ]

        generated = [{"evidence_id": "ev_000"}]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 1
        assert len(verified[0]["content_preview"]) <= 200

    def test_evidence_text_truncated(self):
        """evidence_text 应被截断到 500 字符"""
        from app.api.chat_routes import _verify_citations

        doc_id = str(uuid.uuid4())
        long_content = "B" * 1000
        evidence_pack = [
            {
                "evidence_id": "ev_000",
                "document_id": doc_id,
                "filename": "long.md",
                "content": long_content,
                "score": 0.9,
                "source_type": "text",
            },
        ]

        generated = [{"evidence_id": "ev_000"}]
        verified = _verify_citations(generated, evidence_pack)
        assert len(verified) == 1
        assert len(verified[0].get("evidence_text", "")) <= 500


# ============================================================
# EvidencePackBuilder
# ============================================================
class TestEvidencePackBuilder:
    """EvidencePackBuilder 测试"""

    def test_build_evidence_pack(self):
        from app.services.rerank.reranker import EvidencePackBuilder

        hits = [
            {
                "content": "文档内容一",
                "document_id": str(uuid.uuid4()),
                "filename": "doc1.md",
                "score": 0.9,
                "source_type": "text",
                "section_path": "第一章",
                "page_number": 1,
            },
            {
                "content": "文档内容二",
                "document_id": str(uuid.uuid4()),
                "filename": "doc2.md",
                "score": 0.8,
                "source_type": "text",
            },
        ]

        pack = EvidencePackBuilder.build(hits, top_k=8)
        assert len(pack) == 2
        assert pack[0]["evidence_id"] == "ev_000"
        assert pack[1]["evidence_id"] == "ev_001"
        assert pack[0]["score"] == 0.9

    def test_top_k_limit(self):
        from app.services.rerank.reranker import EvidencePackBuilder

        hits = [{"content": f"doc{i}", "document_id": str(uuid.uuid4()), "filename": f"f{i}.md", "score": 0.5} for i in range(20)]
        pack = EvidencePackBuilder.build(hits, top_k=5)
        assert len(pack) == 5

    def test_empty_hits(self):
        from app.services.rerank.reranker import EvidencePackBuilder

        pack = EvidencePackBuilder.build([], top_k=8)
        assert len(pack) == 0

    def test_rerank_score_preferred(self):
        """有 rerank_score 时应优先使用"""
        from app.services.rerank.reranker import EvidencePackBuilder

        hits = [
            {
                "content": "内容",
                "document_id": str(uuid.uuid4()),
                "filename": "doc.md",
                "score": 0.9,
                "rerank_score": 0.95,
                "source_type": "text",
            },
        ]

        pack = EvidencePackBuilder.build(hits, top_k=8)
        assert pack[0]["score"] == 0.95


# ============================================================
# 拒答评估
# ============================================================
class TestRefusalEvaluation:
    """拒答评估测试"""

    def test_evaluate_refusal_no_evidence(self):
        from app.api.chat_routes import _evaluate_refusal

        result = _evaluate_refusal([], "some answer", [])
        assert result["should_refuse"] is True
        assert result["reason"] == "no_evidence"

    def test_evaluate_refusal_empty_answer(self):
        from app.api.chat_routes import _evaluate_refusal

        evidence = [{"score": 0.9}]
        result = _evaluate_refusal(evidence, "", [])
        assert result["should_refuse"] is True
        assert result["reason"] == "empty_answer"

    def test_evaluate_refusal_no_citations(self):
        from app.api.chat_routes import _evaluate_refusal

        evidence = [{"score": 0.9}]
        result = _evaluate_refusal(evidence, "some answer", [])
        assert result["should_refuse"] is True
        assert result["reason"] == "no_verified_citations"

    def test_evaluate_refusal_low_confidence(self):
        from app.api.chat_routes import _evaluate_refusal

        evidence = [{"score": 0.9}]
        citations = [{"score": 0.1, "rerank_score": 0.1}]
        result = _evaluate_refusal(evidence, "some answer", citations)
        assert result["should_refuse"] is True
        assert result["reason"] == "low_confidence_citations"

    def test_evaluate_refusal_normal(self):
        from app.api.chat_routes import _evaluate_refusal

        evidence = [{"score": 0.9}]
        citations = [{"score": 0.9, "rerank_score": 0.85}]
        result = _evaluate_refusal(evidence, "这是一个正常的回答", citations)
        assert result["should_refuse"] is False
        assert result["confidence"] >= 0.6
