"""
检索服务 — 实现多路检索（向量检索 + 预留 BM25/表格/媒体检索）
"""

from typing import Optional

from loguru import logger

from app.core.config import get_settings
from app.services.embedding import EmbeddingService
from app.services.qdrant_store import QdrantService

settings = get_settings()


class RetrievalService:
    """多路检索服务"""

    def __init__(self):
        self.qdrant = QdrantService()
        self.embedding_service = EmbeddingService()

    async def retrieve(
        self,
        query: str,
        kb_id: str,
        top_k: int = 40,
        retrieval_mode: str = "auto",
    ) -> dict:
        """
        执行检索。
        返回 {"query": str, "query_type": str, "hits": list[dict], "stats": dict}
        """
        query_type = self._classify_query(query)

        hits = []
        stats = {"vector": 0, "bm25": 0, "table": 0, "media": 0}

        # 1. 向量检索（始终执行）
        query_vector = await self.embedding_service.embed_text(query)
        if query_vector:
            vector_hits = await self.qdrant.search(
                query_vector=query_vector,
                kb_id=kb_id,
                top_k=top_k,
            )
            stats["vector"] = len(vector_hits)
            hits.extend(vector_hits)

        # 2. 预留：BM25 检索
        # stats["bm25"] = await self._bm25_search(query, kb_id, top_k)

        # 3. 预留：表格检索
        # stats["table"] = await self._table_search(query, kb_id)

        # 4. 预留：媒体检索
        # stats["media"] = await self._media_search(query, kb_id)

        # 去重
        hits = self._deduplicate_hits(hits)

        return {
            "query": query,
            "query_type": query_type,
            "hits": hits[:top_k],
            "stats": stats,
        }

    @staticmethod
    def _classify_query(query: str) -> str:
        """简单的问题类型分类"""
        query_lower = query.lower()

        table_keywords = ["表格", "表", "统计", "多少", "总计", "合计", "sheet", "excel", "xlsx",
                          "数据", "支出", "收入", "预算", "金额", "数量"]
        image_keywords = ["图片", "截图", "照片", "图像", "图中", "图示", "如图"]
        video_keywords = ["视频", "录像", "片段", "录像", "回放", "讲", "那段"]
        audio_keywords = ["录音", "音频", "语音", "说了"]
        code_keywords = ["代码", "函数", "class", "函数", "方法", "报错", "bug", "error"]
        formula_keywords = ["公式", "方程", "数学", "推导", "证明", "定理"]

        if any(kw in query_lower for kw in table_keywords):
            return "table"
        if any(kw in query_lower for kw in image_keywords):
            return "image"
        if any(kw in query_lower for kw in video_keywords):
            return "video"
        if any(kw in query_lower for kw in audio_keywords):
            return "audio"
        if any(kw in query_lower for kw in code_keywords):
            return "code"
        if any(kw in query_lower for kw in formula_keywords):
            return "formula"

        return "text"

    @staticmethod
    def _deduplicate_hits(hits: list[dict]) -> list[dict]:
        """按 content 去重"""
        seen = set()
        deduped = []
        for hit in hits:
            content = hit.get("content", "")
            content_hash = hash(content[:200])
            if content_hash not in seen:
                seen.add(content_hash)
                deduped.append(hit)
        return deduped
