"""
Rerank 服务 — 对检索结果重排序
"""

from typing import Optional

import httpx
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


class RerankService:
    """重排序服务"""

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.DEFAULT_RERANK
        self.gateway_url = settings.MODEL_GATEWAY_URL.rstrip("/")

    async def rerank(
        self, query: str, documents: list[dict], top_k: int = 8
    ) -> list[dict]:
        """
        对候选文档重排序。
        输入 documents: [{"content": ..., ...}, ...]
        返回排序后的 documents，增加 rerank_score。
        """
        if not documents:
            return []

        try:
            contents = [d.get("content", "") for d in documents]
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.gateway_url}/model/rerank",
                    json={
                        "model": self.model,
                        "query": query,
                        "documents": contents,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])

                # 按 rerank 分数排序
                score_map = {r["index"]: r["score"] for r in results}
                for i, doc in enumerate(documents):
                    doc["rerank_score"] = score_map.get(i, 0.0)

                documents.sort(key=lambda d: d.get("rerank_score", 0.0), reverse=True)
                return documents[:top_k]

        except Exception as e:
            logger.warning(f"Rerank failed, falling back to original order: {e}")
            return documents[:top_k]


class EvidencePackBuilder:
    """
    证据包构造器。
    将重排序后的检索结果构造为标准 Evidence Pack，
    供 LLM 生成回答使用。
    """

    @staticmethod
    def build(hits: list[dict], top_k: int = 8) -> list[dict]:
        """构造 evidence pack"""
        evidence_pack = []
        for i, hit in enumerate(hits[:top_k]):
            evidence = {
                "evidence_id": f"ev_{i:03d}",
                "source_type": hit.get("source_type", "text"),
                "document_id": hit.get("document_id", ""),
                "filename": hit.get("filename", ""),
                "content": hit.get("content", ""),
                "page_number": hit.get("page_number"),
                "slide_number": hit.get("slide_number"),
                "section_path": hit.get("section_path"),
                "score": hit.get("rerank_score", hit.get("score", 0.0)),
                "metadata": hit.get("metadata_json", {}),
            }
            evidence_pack.append(evidence)

        return evidence_pack
