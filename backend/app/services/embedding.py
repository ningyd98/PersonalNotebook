"""
Embedding 服务 — 通过 model-gateway 调用 embedding 模型
"""

from typing import Optional

import httpx
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Embedding 向量化服务"""

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.DEFAULT_EMBEDDING
        self.gateway_url = settings.MODEL_GATEWAY_URL.rstrip("/")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量 texts -> vectors"""
        if not texts:
            return []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.gateway_url}/model/embed",
                    json={"model": self.model, "texts": texts},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("vectors", [])
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    async def embed_text(self, text: str) -> list[float]:
        """单个 text -> vector"""
        vectors = await self.embed_texts([text])
        return vectors[0] if vectors else []

    async def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """批量向量化 chunk 列表，将 vector 写入 chunk"""
        texts = [c["content"] for c in chunks]
        vectors = await self.embed_texts(texts)
        for i, chunk in enumerate(chunks):
            if i < len(vectors):
                chunk["embedding"] = vectors[i]
        return chunks
