"""
评测模块单元测试

测试内容：
- Recall@K 计算
- MRR (Mean Reciprocal Rank) 计算
- Faithfulness 评估
- Citation Accuracy 计算
- Hallucination Rate 计算
- ClaimVerifier 覆盖率计算
- RefusalEngine 拒答评估

运行: pytest tests/test_evaluation.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# Recall@K
# ============================================================
class TestRecallAtK:
    """Recall@K 计算"""

    @staticmethod
    def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
        """计算 Recall@K"""
        if not relevant_ids:
            return 0.0
        top_k = retrieved_ids[:k]
        hits = len(set(top_k) & relevant_ids)
        return hits / len(relevant_ids)

    def test_perfect_recall(self):
        relevant = {"doc1", "doc2", "doc3"}
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        assert self.recall_at_k(retrieved, relevant, k=5) == 1.0

    def test_partial_recall(self):
        relevant = {"doc1", "doc2", "doc3"}
        retrieved = ["doc1", "doc4", "doc2", "doc5", "doc6"]
        assert self.recall_at_k(retrieved, relevant, k=5) == 2 / 3

    def test_zero_recall(self):
        relevant = {"doc1", "doc2"}
        retrieved = ["doc3", "doc4", "doc5"]
        assert self.recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_recall_at_k1(self):
        relevant = {"doc1", "doc2"}
        retrieved = ["doc1", "doc3", "doc4"]
        assert self.recall_at_k(retrieved, relevant, k=1) == 0.5

    def test_empty_relevant(self):
        assert self.recall_at_k(["doc1"], set(), k=5) == 0.0

    def test_empty_retrieved(self):
        relevant = {"doc1"}
        assert self.recall_at_k([], relevant, k=5) == 0.0

    def test_k_larger_than_retrieved(self):
        relevant = {"doc1"}
        retrieved = ["doc1"]
        assert self.recall_at_k(retrieved, relevant, k=10) == 1.0


# ============================================================
# MRR (Mean Reciprocal Rank)
# ============================================================
class TestMRR:
    """MRR 计算"""

    @staticmethod
    def mrr(queries_results: list[list[str]], relevant_sets: list[set[str]]) -> float:
        """计算 MRR"""
        if not queries_results:
            return 0.0
        rr_sum = 0.0
        for results, relevant in zip(queries_results, relevant_sets):
            for rank, doc_id in enumerate(results, start=1):
                if doc_id in relevant:
                    rr_sum += 1.0 / rank
                    break
        return rr_sum / len(queries_results)

    def test_perfect_mrr(self):
        results = [["doc1", "doc2"], ["doc3", "doc4"]]
        relevant = [{"doc1"}, {"doc3"}]
        assert self.mrr(results, relevant) == 1.0

    def test_second_rank_mrr(self):
        results = [["doc2", "doc1"], ["doc4", "doc3"]]
        relevant = [{"doc1"}, {"doc3"}]
        assert self.mrr(results, relevant) == 0.5  # 1/2 + 1/2 = 1.0, /2 = 0.5

    def test_no_relevant_found(self):
        results = [["doc5", "doc6"]]
        relevant = [{"doc1"}]
        assert self.mrr(results, relevant) == 0.0

    def test_mixed_mrr(self):
        results = [
            ["doc1", "doc2"],       # rank 1 -> 1.0
            ["doc3", "doc4", "doc2"],  # doc4 not relevant, doc2 not in relevant, doc3 rank 1? No, doc3 not in relevant_set
        ]
        relevant = [{"doc1"}, {"doc2"}]
        # Query 1: doc1 at rank 1 -> 1/1 = 1.0
        # Query 2: doc2 at rank 3 -> 1/3 ≈ 0.333
        expected = (1.0 + 1.0 / 3) / 2
        assert abs(self.mrr(results, relevant) - expected) < 0.01

    def test_empty_queries(self):
        assert self.mrr([], []) == 0.0


# ============================================================
# Faithfulness 评估
# ============================================================
class TestFaithfulness:
    """Faithfulness 评估 — 基于 ClaimVerifier"""

    def test_claim_extraction(self):
        from app.services.claims.evidence_pack import ClaimVerifier

        text = "第一句话。第二句话！第三句话？第四句较短"
        claims = ClaimVerifier.extract_claims(text)
        assert len(claims) >= 3
        # 短句应被过滤
        for claim in claims:
            assert len(claim) > 5

    def test_claim_extraction_english(self):
        from app.services.claims.evidence_pack import ClaimVerifier

        text = "First sentence here. Second sentence is longer. Short. Third sentence is the longest."
        claims = ClaimVerifier.extract_claims(text)
        assert len(claims) >= 2

    def test_verify_claim_with_matching_evidence(self):
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(
                evidence_id="ev_0",
                document_id="doc_1",
                content="Q-learning 是一种无模型的强化学习算法，通过时序差分学习策略。",
            ),
        ]
        claim = "Q-learning是一种无模型的强化学习算法。"
        result = ClaimVerifier.verify_claim(claim, evidences)
        assert result is not None

    def test_verify_claim_no_match(self):
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(
                evidence_id="ev_0",
                document_id="doc_1",
                content="今天的天气很好，适合户外运动。",
            ),
        ]
        claim = "量子计算利用量子叠加态实现并行计算。"
        result = ClaimVerifier.verify_claim(claim, evidences)
        assert result is None

    def test_compute_coverage_full(self):
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(
                evidence_id="ev_0",
                document_id="doc_1",
                content="Python是一种编程语言，广泛用于数据科学和机器学习领域。",
            ),
        ]
        answer = "Python是一种编程语言。它广泛用于数据科学和机器学习领域。"
        coverage, supported, unsupported = ClaimVerifier.compute_coverage(answer, evidences)
        assert coverage > 0
        assert len(supported) >= 1

    def test_compute_coverage_partial(self):
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(
                evidence_id="ev_0",
                document_id="doc_1",
                content="Python是一种编程语言。",
            ),
        ]
        answer = "Python是一种编程语言。量子计算机需要在极低温环境下运行。"
        coverage, supported, unsupported = ClaimVerifier.compute_coverage(answer, evidences)
        assert 0 < coverage < 1.0
        assert len(unsupported) >= 1

    def test_compute_coverage_no_evidence(self):
        from app.services.claims.evidence_pack import ClaimVerifier

        answer = "这是一个没有证据支持的声明。"
        coverage, supported, unsupported = ClaimVerifier.compute_coverage(answer, [])
        assert coverage == 0.0

    def test_compute_coverage_empty_answer(self):
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(evidence_id="ev_0", document_id="doc_1", content="内容"),
        ]
        coverage, supported, unsupported = ClaimVerifier.compute_coverage("", evidences)
        assert coverage == 0.0

    def test_tokenize_chinese_bigram(self):
        from app.services.claims.evidence_pack import ClaimVerifier

        tokens = ClaimVerifier._tokenize("强化学习算法")
        # 应包含中文 bigram
        assert "强化" in tokens or "强化学" in tokens or "强化学习算法" in tokens
        # 也应包含完整的中文段落
        assert "强化学习算法" in tokens

    def test_tokenize_english_words(self):
        from app.services.claims.evidence_pack import ClaimVerifier

        tokens = ClaimVerifier._tokenize("machine learning algorithm")
        assert "machine" in tokens
        assert "learning" in tokens
        assert "algorithm" in tokens


# ============================================================
# Citation Accuracy
# ============================================================
class TestCitationAccuracy:
    """Citation Accuracy 计算"""

    @staticmethod
    def citation_accuracy(verified_citations: list[dict], total_claims: int) -> float:
        """计算引用准确率 = 有效引用数 / 总声明数"""
        if total_claims == 0:
            return 0.0
        return len(verified_citations) / total_claims

    def test_perfect_accuracy(self):
        citations = [{"evidence_id": f"ev_{i}"} for i in range(5)]
        assert self.citation_accuracy(citations, total_claims=5) == 1.0

    def test_partial_accuracy(self):
        citations = [{"evidence_id": f"ev_{i}"} for i in range(3)]
        assert self.citation_accuracy(citations, total_claims=5) == 0.6

    def test_zero_accuracy(self):
        assert self.citation_accuracy([], total_claims=5) == 0.0

    def test_no_claims(self):
        assert self.citation_accuracy([], total_claims=0) == 0.0

    def test_citation_coverage_from_evidence_pack(self):
        """测试证据包引用覆盖率计算"""
        # 模拟 evidence_pack 和 verified_citations
        evidence_pack = [
            {"evidence_id": f"ev_{i:03d}"} for i in range(10)
        ]
        verified = evidence_pack[:6]  # 6/10 被引用

        coverage = len(verified) / len(evidence_pack) if evidence_pack else 0.0
        assert abs(coverage - 0.6) < 0.01


# ============================================================
# Hallucination Rate
# ============================================================
class TestHallucinationRate:
    """Hallucination Rate 计算"""

    @staticmethod
    def hallucination_rate(unsupported_claims: list[str], total_claims: list[str]) -> float:
        """幻觉率 = 无证据支持的声明数 / 总声明数"""
        if not total_claims:
            return 0.0
        return len(unsupported_claims) / len(total_claims)

    def test_no_hallucination(self):
        claims = ["claim1", "claim2", "claim3"]
        unsupported = []
        assert self.hallucination_rate(unsupported, claims) == 0.0

    def test_full_hallucination(self):
        claims = ["claim1", "claim2"]
        unsupported = ["claim1", "claim2"]
        assert self.hallucination_rate(unsupported, claims) == 1.0

    def test_partial_hallucination(self):
        claims = ["claim1", "claim2", "claim3", "claim4"]
        unsupported = ["claim2", "claim4"]
        assert self.hallucination_rate(unsupported, claims) == 0.5

    def test_no_claims(self):
        assert self.hallucination_rate([], []) == 0.0

    def test_hallucination_from_claim_verifier(self):
        """使用 ClaimVerifier 计算幻觉率"""
        from app.services.claims.evidence_pack import ClaimVerifier, Evidence

        evidences = [
            Evidence(
                evidence_id="ev_0",
                document_id="doc_1",
                content="太阳从东方升起。地球围绕太阳公转。",
            ),
        ]
        answer = "太阳从东方升起。月亮是奶酪做的。"
        coverage, supported, unsupported = ClaimVerifier.compute_coverage(answer, evidences)

        all_claims = ClaimVerifier.extract_claims(answer)
        if all_claims:
            hallucination = len(unsupported) / len(all_claims)
            assert hallucination >= 0.0
            assert hallucination <= 1.0


# ============================================================
# RefusalEngine
# ============================================================
class TestRefusalEngine:
    """拒答引擎测试"""

    def test_no_evidence_refusal(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack

        pack = EnhancedEvidencePack(query="测试", query_type="text", evidences=[])
        should_refuse, reason = RefusalEngine.evaluate(pack)
        assert should_refuse is True
        assert "no_evidence" in reason

    def test_low_score_refusal(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack, Evidence

        low_evidence = Evidence(
            evidence_id="ev_0", document_id="doc_1",
            final_score=0.05, confidence=0.05,
        )
        pack = EnhancedEvidencePack(
            query="测试", query_type="text",
            evidences=[low_evidence],
        )
        should_refuse, reason = RefusalEngine.evaluate(pack)
        assert should_refuse is True
        assert "low_score" in reason

    def test_sufficient_evidence_no_refusal(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack, Evidence

        good_evidences = [
            Evidence(evidence_id=f"ev_{i}", document_id=f"doc_{i}",
                     final_score=0.8, confidence=0.8)
            for i in range(3)
        ]
        pack = EnhancedEvidencePack(
            query="测试", query_type="text",
            evidences=good_evidences,
        )
        should_refuse, reason = RefusalEngine.evaluate(pack, citation_coverage=0.8)
        assert should_refuse is False

    def test_type_mismatch_refusal(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack, Evidence

        # 查询要求表格，但证据都是文本
        text_evidences = [
            Evidence(evidence_id=f"ev_{i}", document_id=f"doc_{i}",
                     final_score=0.7, confidence=0.7, source_type="text")
            for i in range(3)
        ]
        pack = EnhancedEvidencePack(
            query="表格查询", query_type="table",
            evidences=text_evidences,
        )
        should_refuse, reason = RefusalEngine.evaluate(pack, citation_coverage=0.8)
        assert should_refuse is True
        assert "type_mismatch" in reason

    def test_insufficient_evidence_count(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack, Evidence

        # 只有1条证据（低于 MIN_EVIDENCE_COUNT=2）
        pack = EnhancedEvidencePack(
            query="测试", query_type="text",
            evidences=[Evidence(evidence_id="ev_0", document_id="doc_1",
                                final_score=0.5, confidence=0.5)],
        )
        should_refuse, reason = RefusalEngine.evaluate(pack)
        assert should_refuse is True
        assert "insufficient_evidence" in reason

    def test_low_citation_coverage(self):
        from app.services.claims.evidence_pack import RefusalEngine, EnhancedEvidencePack, Evidence

        good_evidences = [
            Evidence(evidence_id=f"ev_{i}", document_id=f"doc_{i}",
                     final_score=0.7, confidence=0.7)
            for i in range(3)
        ]
        pack = EnhancedEvidencePack(
            query="测试", query_type="text",
            evidences=good_evidences,
        )
        # 引用覆盖率过低
        should_refuse, reason = RefusalEngine.evaluate(pack, citation_coverage=0.3)
        assert should_refuse is True
        assert "low_citation_coverage" in reason


# ============================================================
# EnhancedEvidencePackBuilder
# ============================================================
class TestEnhancedEvidencePackBuilder:
    """EnhancedEvidencePackBuilder 测试"""

    def test_build_basic(self):
        from app.services.claims.evidence_pack import EnhancedEvidencePackBuilder

        retrieval_hits = [
            {
                "id": "chunk_1",
                "document_id": "doc_1",
                "filename": "test.md",
                "content": "内容一",
                "score": 0.9,
                "source_type": "text",
                "section_path": "第一章",
            },
        ]
        reranked_hits = [
            {
                "id": "chunk_1",
                "document_id": "doc_1",
                "filename": "test.md",
                "content": "内容一",
                "rerank_score": 0.95,
            },
        ]

        pack = EnhancedEvidencePackBuilder.build(
            query="测试查询",
            retrieval_hits=retrieval_hits,
            reranked_hits=reranked_hits,
            query_type="text",
        )

        assert pack.query == "测试查询"
        assert pack.query_type == "text"
        assert len(pack.evidences) == 1
        assert pack.evidences[0].dense_score == 0.9
        assert pack.evidences[0].rerank_score == 0.95
        assert pack.evidences[0].final_score == 0.95
        assert pack.coverage.has_direct_answer is True
        assert pack.dense_results_count == 1

    def test_build_empty(self):
        from app.services.claims.evidence_pack import EnhancedEvidencePackBuilder

        pack = EnhancedEvidencePackBuilder.build(
            query="空查询",
            retrieval_hits=[],
            reranked_hits=[],
        )

        assert len(pack.evidences) == 0
        assert pack.coverage.has_direct_answer is False

    def test_build_without_rerank(self):
        from app.services.claims.evidence_pack import EnhancedEvidencePackBuilder

        retrieval_hits = [
            {
                "id": "chunk_1",
                "document_id": "doc_1",
                "filename": "test.md",
                "content": "内容",
                "score": 0.85,
                "source_type": "text",
            },
        ]

        pack = EnhancedEvidencePackBuilder.build(
            query="测试",
            retrieval_hits=retrieval_hits,
            reranked_hits=[],
        )

        assert len(pack.evidences) == 1
        # 没有 rerank 时 final_score 应等于 dense_score
        assert pack.evidences[0].final_score == 0.85

    def test_to_dict(self):
        from app.services.claims.evidence_pack import EnhancedEvidencePackBuilder

        retrieval_hits = [
            {
                "id": "chunk_1",
                "document_id": "doc_1",
                "filename": "test.md",
                "content": "内容",
                "score": 0.9,
                "source_type": "text",
            },
        ]

        pack = EnhancedEvidencePackBuilder.build(
            query="测试",
            retrieval_hits=retrieval_hits,
            reranked_hits=[],
        )

        d = pack.to_dict()
        assert "query" in d
        assert "evidences" in d
        assert "coverage" in d
        assert len(d["evidences"]) == 1


# ============================================================
# Evidence dataclass
# ============================================================
class TestEvidenceDataclass:
    """Evidence 数据类测试"""

    def test_evidence_to_dict(self):
        from app.services.claims.evidence_pack import Evidence

        ev = Evidence(
            evidence_id="ev_000",
            document_id="doc_1",
            document_title="测试文档",
            content="测试内容",
            dense_score=0.9,
            rerank_score=0.95,
            final_score=0.95,
            confidence=0.95,
            source_type="text",
        )

        d = ev.to_dict()
        assert d["evidence_id"] == "ev_000"
        assert d["document_id"] == "doc_1"
        assert d["dense_score"] == 0.9
        assert d["rerank_score"] == 0.95
        assert d["final_score"] == 0.95
        assert d["source_type"] == "text"

    def test_coverage_to_dict(self):
        from app.services.claims.evidence_pack import Coverage

        cov = Coverage(
            has_direct_answer=True,
            has_conflict=False,
            missing_info=["表格数据"],
        )

        d = cov.to_dict()
        assert d["has_direct_answer"] is True
        assert d["has_conflict"] is False
        assert "表格数据" in d["missing_info"]
