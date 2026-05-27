"""
Qdrant 向量存储服务
"""

import uuid
from typing import Optional

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.core.config import get_settings

settings = get_settings()


class QdrantService:
    """Qdrant 向量数据库封装"""

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY or None,
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self.vector_size = settings.QDRANT_VECTOR_SIZE

    def ensure_collection(self) -> None:
        """确保 collection 存在"""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {self.collection_name}")

    async def upsert_chunks(
        self, chunks: list[dict], kb_id: str
    ) -> list[str]:
        """批量写入向量，返回 embedding_id 列表"""
        self.ensure_collection()
        points = []
        embedding_ids = []

        for chunk in chunks:
            vector = chunk.get("embedding", [])
            if not vector:
                continue

            # 如果 vector_size 不匹配，跳过
            if len(vector) != self.vector_size:
                logger.warning(
                    f"Vector size mismatch: expected {self.vector_size}, got {len(vector)}. Updating vector_size."
                )
                # 动态更新 vector_size
                self.vector_size = len(vector)
                self._recreate_collection()

            eid = str(uuid.uuid4())
            embedding_ids.append(eid)
            chunk["embedding_id"] = eid

            payload = {
                "document_id": str(chunk.get("document_id", "")),
                "kb_id": str(kb_id),
                "chunk_index": chunk.get("chunk_index", 0),
                "content": chunk.get("content", ""),
                "content_hash": chunk.get("content_hash", ""),
                "section_path": chunk.get("section_path", ""),
                "page_number": chunk.get("page_number"),
                "slide_number": chunk.get("slide_number"),
                "source_type": chunk.get("source_type", "text"),
                "filename": chunk.get("source", {}).get("filename", ""),
                "metadata_json": chunk.get("metadata_json", {}),
            }

            points.append(
                qdrant_models.PointStruct(
                    id=eid,
                    vector=vector,
                    payload=payload,
                )
            )

        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            logger.info(f"Upserted {len(points)} points to Qdrant")

        return embedding_ids

    async def search(
        self,
        query_vector: list[float],
        kb_id: str,
        top_k: int = 40,
        score_threshold: float = 0.0,
    ) -> list[dict]:
        """向量检索"""
        self.ensure_collection()

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="kb_id",
                        match=qdrant_models.MatchValue(value=str(kb_id)),
                    )
                ]
            ),
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "document_id": hit.payload.get("document_id"),
                "content": hit.payload.get("content"),
                "filename": hit.payload.get("filename"),
                "section_path": hit.payload.get("section_path"),
                "page_number": hit.payload.get("page_number"),
                "slide_number": hit.payload.get("slide_number"),
                "source_type": hit.payload.get("source_type"),
                "metadata_json": hit.payload.get("metadata_json"),
            }
            for hit in results
        ]

    def delete_by_document(self, document_id: str) -> None:
        """删除文档的所有向量"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="document_id",
                                match=qdrant_models.MatchValue(value=str(document_id)),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to delete vectors for document {document_id}: {e}")

    def _recreate_collection(self) -> None:
        """重建 collection（更新 vector_size）"""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=self.vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
