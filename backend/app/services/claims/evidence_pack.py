"""
Enhanced EvidencePack + 低置信拒答 + Claim 级引用验证 — Phase 1.6
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Evidence:
    """增强证据项"""
    evidence_id: str
    document_id: str
    document_title: str = ""
    version_id: int = 1
    chunk_id: str = ""
    content: str = ""
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    source_location: str = ""
    quote_span: Optional[str] = None
    confidence: float = 0.0
    source_type: str = "text"

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "version_id": self.version_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "source_location": self.source_location,
            "quote_span": self.quote_span,
            "confidence": self.confidence,
            "source_type": self.source_type,
        }


@dataclass
class Coverage:
    """证据覆盖度"""
    has_direct_answer: bool = False
    has_conflict: bool = False
    missing_info: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "has_direct_answer": self.has_direct_answer,
            "has_conflict": self.has_conflict,
            "missing_info": self.missing_info,
        }


@dataclass
class EnhancedEvidencePack:
    """增强证据包"""
    query: str
    query_type: str = "text"
    retrieval_strategy: str = "vector"
    evidences: list[Evidence] = field(default_factory=list)
    coverage: Coverage = field(default_factory=Coverage)
    rewritten_queries: list[str] = field(default_factory=list)
    dense_results_count: int = 0
    sparse_results_count: int = 0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "retrieval_strategy": self.retrieval_strategy,
            "rewritten_queries": self.rewritten_queries,
            "dense_results_count": self.dense_results_count,
            "sparse_results_count": self.sparse_results_count,
            "evidences": [e.to_dict() for e in self.evidences],
            "coverage": self.coverage.to_dict(),
        }


class EnhancedEvidencePackBuilder:
    """从检索结果构建 EnhancedEvidencePack"""

    @staticmethod
    def build(
        query: str,
        retrieval_hits: list[dict],
        reranked_hits: list[dict],
        query_type: str = "text",
    ) -> EnhancedEvidencePack:
        evidence_map: dict[str, Evidence] = {}

        # Dense scores
        for hit in retrieval_hits:
            eid = hit.get("id", "")
            if eid not in evidence_map:
                evidence_map[eid] = Evidence(
                    evidence_id=eid,
                    document_id=str(hit.get("document_id", "")),
                    document_title=hit.get("filename", ""),
                    chunk_id=eid,
                    content=hit.get("content", ""),
                    dense_score=hit.get("score", 0.0),
                    source_location=(
                        f"page={hit.get('page_number')}" if hit.get("page_number")
                        else hit.get("section_path", "")
                    ),
                    source_type=hit.get("source_type", "text"),
                )
            else:
                evidence_map[eid].dense_score = hit.get("score", 0.0)

        # Rerank scores
        for hit in reranked_hits:
            eid = hit.get("id", "")
            if eid in evidence_map:
                evidence_map[eid].rerank_score = hit.get("rerank_score", 0.0)
                evidence_map[eid].final_score = evidence_map[eid].rerank_score

        # Compute final_score and confidence
        for ev in evidence_map.values():
            if ev.rerank_score > 0:
                ev.final_score = ev.rerank_score
            else:
                ev.final_score = ev.dense_score
            ev.confidence = ev.final_score

        evidences = sorted(
            evidence_map.values(), key=lambda e: e.final_score, reverse=True
        )

        # Coverage assessment
        coverage = Coverage(
            has_direct_answer=len(evidences) > 0,
            has_conflict=False,
            missing_info=[],
        )

        return EnhancedEvidencePack(
            query=query,
            query_type=query_type,
            retrieval_strategy="vector",
            evidences=evidences[:8],
            coverage=coverage,
            dense_results_count=len(retrieval_hits),
            sparse_results_count=0,
        )


class RefusalEngine:
    """多因子低置信拒答引擎"""

    LOW_CONFIDENCE_THRESHOLD = 0.15
    MIN_EVIDENCE_COUNT = 1

    @classmethod
    def evaluate(
        cls,
        evidence_pack: EnhancedEvidencePack,
        citation_coverage: float = 0.0,
    ) -> tuple[bool, str]:
        """
        综合评估是否应该拒答。
        Returns: (should_refuse, refusal_reason)
        """
        evidences = evidence_pack.evidences
        reasons: list[str] = []

        # Factor 1: No evidence at all
        if not evidences:
            return True, "no_evidence: 检索未找到任何相关知识库内容"

        # Factor 2: All scores below threshold
        max_score = max(e.final_score for e in evidences)
        if max_score < cls.LOW_CONFIDENCE_THRESHOLD:
            reasons.append(f"low_score: 最高相关度 {max_score:.2f} < 阈值 {cls.LOW_CONFIDENCE_THRESHOLD}")

        # Factor 3: Too few evidences
        if len(evidences) < cls.MIN_EVIDENCE_COUNT:
            reasons.append(f"insufficient_evidence: 仅 {len(evidences)} 条证据")

        # Factor 4: Citation coverage too low
        if citation_coverage < 0.3 and len(evidences) >= cls.MIN_EVIDENCE_COUNT:
            reasons.append(f"low_citation_coverage: 引用覆盖率 {citation_coverage:.1%} < 30%")

        # Factor 5: Type mismatch (query vs evidence)
        if evidence_pack.query_type in ("table", "code") and all(
            e.source_type != evidence_pack.query_type for e in evidences
        ):
            reasons.append(f"type_mismatch: 查询类型为 {evidence_pack.query_type} 但无匹配证据类型")

        if reasons:
            missing = []
            if evidence_pack.query_type == "table":
                missing.append("表格数据")
            if evidence_pack.query_type == "code":
                missing.append("代码示例")
            if max_score < cls.LOW_CONFIDENCE_THRESHOLD:
                missing.append("高相关度文档")

            reason_text = "; ".join(reasons)
            if missing:
                reason_text += f"。建议补充: {', '.join(missing)}"
            return True, reason_text

        return False, ""


class ClaimVerifier:
    """Claim 级引用覆盖率校验"""

    @staticmethod
    def extract_claims(text: str) -> list[str]:
        """将回答拆解为 claims"""
        # Split by Chinese/English sentence boundaries
        claims = re.split(r"(?<=[。！？.!?])\s*", text)
        return [c.strip() for c in claims if c.strip() and len(c.strip()) > 5]

    @staticmethod
    def verify_claim(claim: str, evidences: list[Evidence]) -> Optional[Evidence]:
        """检查一个 claim 是否被至少一个 evidence 支持"""
        claim_words = set(claim.lower().split())
        for ev in evidences:
            ev_words = set(ev.content.lower().split())
            overlap = len(claim_words & ev_words)
            if overlap >= 3:  # At least 3 common words
                if len(claim_words) > 0:
                    ratio = overlap / len(claim_words)
                    if ratio >= 0.2:
                        return ev
        return None

    @classmethod
    def compute_coverage(
        cls, answer: str, evidences: list[Evidence]
    ) -> tuple[float, list[str], list[str]]:
        """
        Returns: (coverage_ratio, supported_claims, unsupported_claims)
        """
        claims = cls.extract_claims(answer)
        if not claims:
            return 0.0, [], []

        supported = []
        unsupported = []
        for claim in claims:
            if cls.verify_claim(claim, evidences):
                supported.append(claim)
            else:
                unsupported.append(claim)

        coverage = len(supported) / len(claims) if claims else 0.0
        return coverage, supported, unsupported
