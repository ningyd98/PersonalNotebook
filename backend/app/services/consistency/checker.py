"""
Qdrant ↔ PostgreSQL 一致性校验与修复 — Phase 1.7

修复:
  - 分页 scroll
  - inactive 历史向量不计入 orphan
  - repair 成功后恢复 READY
"""

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger
from qdrant_client.http import models as qdrant_models
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings

settings = get_settings()


@dataclass
class ConsistencyReport:
    kb_id: str
    total_docs_ready: int = 0
    total_chunks_in_db: int = 0
    total_vectors_in_qdrant: int = 0
    missing_vectors: list[str] = field(default_factory=list)
    orphan_vectors: list[str] = field(default_factory=list)
    inactive_historical_vectors_count: int = 0
    dimension_mismatches: list[dict] = field(default_factory=list)
    version_mismatches: list[dict] = field(default_factory=list)
    is_consistent: bool = False

    def to_dict(self) -> dict:
        return {
            "kb_id": self.kb_id,
            "total_docs_ready": self.total_docs_ready,
            "total_chunks_in_db": self.total_chunks_in_db,
            "total_vectors_in_qdrant": self.total_vectors_in_qdrant,
            "missing_vectors_count": len(self.missing_vectors),
            "orphan_vectors_count": len(self.orphan_vectors),
            "inactive_historical_vectors_count": self.inactive_historical_vectors_count,
            "dimension_mismatches_count": len(self.dimension_mismatches),
            "version_mismatches_count": len(self.version_mismatches),
            "is_consistent": self.is_consistent,
            "missing_vectors": self.missing_vectors[:100],
            "orphan_vectors": self.orphan_vectors[:100],
            "dimension_mismatches": self.dimension_mismatches[:50],
            "version_mismatches": self.version_mismatches[:50],
        }


def check_index_consistency(kb_id: str, db: Session) -> ConsistencyReport:
    from app.models.models import DocumentChunk, Document
    from app.services.qdrant_store import QdrantService

    report = ConsistencyReport(kb_id=kb_id)
    qdrant = QdrantService()

    report.total_docs_ready = db.query(func.count(Document.id)).filter(
        Document.kb_id == kb_id,
        Document.status == "READY",
        Document.is_deleted == False,
        Document.active_version > 0,
    ).scalar() or 0

    report.total_chunks_in_db = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.kb_id == kb_id, DocumentChunk.version_id > 0,
    ).scalar() or 0

    try:
        qdrant.ensure_collection()
        qdrant_filter = qdrant_models.Filter(must=[
            qdrant_models.FieldCondition(key="kb_id", match=qdrant_models.MatchValue(value=str(kb_id))),
        ])
        qdrant_points = []
        offset = None
        while True:
            batch, next_offset = qdrant.client.scroll(
                collection_name=qdrant.collection_name,
                scroll_filter=qdrant_filter,
                limit=1000, offset=offset,
                with_payload=True, with_vectors=False,
            )
            qdrant_points.extend(batch)
            if next_offset is None:
                break
            offset = next_offset
        report.total_vectors_in_qdrant = len(qdrant_points)

        # Separate active vs inactive Qdrant points
        active_points = [p for p in qdrant_points if (p.payload or {}).get("is_active") is not False]
        inactive_points = [p for p in qdrant_points if (p.payload or {}).get("is_active") is False]
        report.inactive_historical_vectors_count = len(inactive_points)

        # Compare ONLY active Qdrant points with DB active chunks
        db_active_chunks = db.query(
            DocumentChunk.embedding_id, DocumentChunk.id, DocumentChunk.version_id
        ).join(Document, DocumentChunk.document_id == Document.id).filter(
            DocumentChunk.kb_id == kb_id,
            DocumentChunk.embedding_id.isnot(None),
            Document.active_version == DocumentChunk.version_id,
            Document.status == "READY",
        ).all()
        db_eid_to_chunk = {c.embedding_id: c for c in db_active_chunks}
        db_chunk_ids = set(db_eid_to_chunk.keys())

        active_qdrant_ids = {str(p.id) for p in active_points}

        # Missing: in DB but not in active Qdrant
        report.missing_vectors = list(db_chunk_ids - active_qdrant_ids)

        # Orphan: in active Qdrant but not in DB (exclude inactive historical)
        report.orphan_vectors = list(active_qdrant_ids - db_chunk_ids)

        for point in active_points:
            pid = str(point.id)
            if pid in db_eid_to_chunk:
                chunk = db_eid_to_chunk[pid]
                pv = (point.payload or {}).get("version_id", 1)
                if pv != chunk.version_id:
                    report.version_mismatches.append({
                        "chunk_id": str(chunk.id), "embedding_id": pid,
                        "db_version": chunk.version_id, "qdrant_version": pv,
                    })

        report.is_consistent = (
            len(report.missing_vectors) == 0 and len(report.orphan_vectors) == 0
            and len(report.dimension_mismatches) == 0 and len(report.version_mismatches) == 0
        )

    except Exception as e:
        logger.error(f"Consistency check failed: {e}")
        report.dimension_mismatches.append({"error": str(e)})

    return report


def repair_index(kb_id: str, db: Session, dry_run: bool = True) -> dict:
    report = check_index_consistency(kb_id, db)
    actions: list[str] = []

    if dry_run:
        return {
            "dry_run": True, "report": report.to_dict(),
            "would_delete_orphans": len(report.orphan_vectors),
            "would_mark_failed": len(report.missing_vectors),
        }

    from app.services.qdrant_store import QdrantService
    from app.models.models import Document, DocumentChunk
    qdrant = QdrantService()

    # 1. Delete orphan vectors
    if report.orphan_vectors:
        try:
            qdrant.client.delete(
                collection_name=qdrant.collection_name,
                points_selector=qdrant_models.PointIdsList(points=report.orphan_vectors),
            )
            actions.append(f"deleted_{len(report.orphan_vectors)}_orphans")
        except Exception as e:
            actions.append(f"orphan_delete_failed: {e}")

    # 2. Mark + try re-embed missing vectors
    if report.missing_vectors:
        affected_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.embedding_id.in_(report.missing_vectors)
        ).all()
        affected_doc_ids = set(str(c.document_id) for c in affected_chunks)
        for doc_id in affected_doc_ids:
            doc = db.get(Document, doc_id)
            if not doc:
                continue
            doc_chunks = [c for c in affected_chunks if str(c.document_id) == doc_id]
            doc.status = "FAILED"
            doc.metadata_json = doc.metadata_json or {}
            doc.metadata_json["need_reindex"] = True
            doc.metadata_json["repair_note"] = f"Missing {len(doc_chunks)} vectors"
            db.commit()

            if doc_chunks:
                _try_rewrite_missing(db, qdrant, kb_id, doc_chunks, actions)

            # Re-check: if all chunks now have embedding_id, restore READY
            remaining = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.embedding_id.is_(None),
            ).count()
            if remaining == 0:
                doc.status = "READY"
                doc.metadata_json["need_reindex"] = False
                doc.metadata_json.pop("repair_note", None)
                db.commit()
                actions.append(f"restored_{doc_id}_to_READY")
                logger.info(f"Restored doc {doc_id} to READY after full repair")
            else:
                actions.append(f"marked_{doc_id}_FAILED_NEED_REINDEX")

    return {"dry_run": False, "report": report.to_dict(), "actions": actions}


def _try_rewrite_missing(db, qdrant, kb_id, chunks, actions):
    import asyncio
    try:
        from app.services.embedding import EmbeddingService
        emb = EmbeddingService()
        texts = [c.content for c in chunks if c.content]
        if not texts:
            return
        vectors = asyncio.new_event_loop().run_until_complete(emb.embed_texts(texts))
        payload_chunks = []
        for i, c in enumerate(chunks):
            if i >= len(vectors):
                break
            payload_chunks.append({
                "embedding": vectors[i], "document_id": str(c.document_id),
                "chunk_index": c.chunk_index, "content": c.content or "",
                "content_hash": c.content_hash or "", "version_id": c.version_id or 1,
                "tenant_id": "default", "chunk_id": str(c.id),
            })
        if payload_chunks:
            eids = asyncio.new_event_loop().run_until_complete(qdrant.upsert_chunks(payload_chunks, kb_id))
            for i, c in enumerate(chunks):
                if i < len(eids):
                    c.embedding_id = eids[i]
            db.commit()
            actions.append(f"rewrote_{len(eids)}_vectors")
    except Exception as e:
        actions.append(f"rewrite_failed: {e}")
