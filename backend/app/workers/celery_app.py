"""
Celery Worker — 真实文档导入 DAG

任务 DAG (7 步):
  detecting → extracting → parsing → chunking → embedding → indexing → checking → completed

关键修复 (Phase 1.5):
  - 不传临时文件路径，只传 document_id/kb_id
  - worker 从 MinIO 下载原始文件到临时目录
  - 导入 parsers 触发注册
  - document_id 使用真实数据库 UUID
  - Qdrant 维度不匹配时报错而非重建 collection
  - 使用同步 create_engine + Session
"""

import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from celery import Celery
from loguru import logger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "personal_kb",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,
    task_time_limit=900,
)

# 触发所有 parser 注册
import app.services.parsers  # noqa: E402


def _get_sync_session():
    """获取同步数据库会话"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine(
        settings.DATABASE_URL_SYNC,
        pool_size=5, max_overflow=10, pool_pre_ping=True,
    )
    return Session(engine)


def _update_job(db, job_id, status, progress, **kwargs):
    from app.models.models import IngestJob
    job = db.get(IngestJob, job_id)
    if not job:
        return
    job.status = status
    job.progress = progress
    for k, v in kwargs.items():
        if hasattr(job, k):
            setattr(job, k, v)
    db.commit()


def _download_from_minio(storage_path: str) -> str:
    """从 MinIO/Local 下载文件到临时目录，返回路径"""
    from app.services.storage import minio_storage
    prefix = f"minio://{settings.MINIO_BUCKET}/"
    if not storage_path.startswith(prefix):
        if os.path.exists(storage_path):
            return storage_path
        raise FileNotFoundError(f"File not found: {storage_path}")
    object_name = storage_path[len(prefix):]
    data = minio_storage.download_file(object_name)
    suffix = Path(object_name).suffix
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


@celery_app.task(bind=True, name="ingest_document")
def ingest_document(self, document_id: str, kb_id: str, options: dict = None):
    """
    完整文档导入任务。
    只接收 document_id 和 kb_id，worker 从 MinIO 下载文件。
    """
    options = options or {}
    db = _get_sync_session()
    job_id = self.request.id
    warnings: list[str] = []
    tmp_path = None

    try:
        from app.models.models import Document, DocumentBlock, DocumentChunk

        doc = db.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Step 1: detecting (5%)
        _update_job(db, job_id, "detecting", 5, started_at=datetime.utcnow())

        mime_type = doc.mime_type
        ext = Path(doc.filename).suffix
        if not mime_type or mime_type == "application/octet-stream":
            from app.services.connectors.base import LocalFolderConnector
            mime_type = LocalFolderConnector._guess_mime_type(Path(doc.filename))
        doc.mime_type = mime_type
        doc.file_type = ext.lstrip(".")
        db.commit()

        # Step 2: Download + Parse (50%)
        _update_job(db, job_id, "parsing", 15)
        tmp_path = _download_from_minio(doc.storage_path)

        from app.services.parsers.base import ParserRegistry
        parser = ParserRegistry.get_parser(mime_type=mime_type, extension=ext)
        if parser is None:
            raise ValueError(f"No parser for {mime_type} / {ext}")

        try:
            udr = parser.parse(tmp_path, options)
        except Exception as parse_err:
            logger.warning(f"Primary parser failed: {parse_err}, trying fallback")
            from app.services.parsers.fallback_parser import FallbackParser
            udr = FallbackParser().parse(tmp_path, options)
            warnings.append(f"Primary parser failed: {str(parse_err)}. Used fallback.")

        # Override document_id with real DB UUID
        udr.document_id = str(doc.id)

        doc.title = udr.metadata.get("title", doc.filename)
        doc.author = udr.metadata.get("author", "")
        doc.metadata_json = udr.metadata
        doc.parse_status = "parsing"
        db.commit()

        # Write blocks
        block_count = 0
        for block in udr.blocks:
            db_block = DocumentBlock(
                document_id=doc.id, block_type=block.type, text=block.text,
                structured_json=block.structured_data,
                page_number=block.page, slide_number=block.slide,
                sheet_name=block.sheet_name, cell_range=block.cell_range,
                start_time=block.start_time, end_time=block.end_time,
                bbox_json=block.bbox, section_path=block.section_path,
                metadata_json=block.metadata,
            )
            db.add(db_block)
            block_count += 1
        db.commit()

        # Step 3: chunking (50%)
        _update_job(db, job_id, "chunking", 45)
        from app.services.chunking.chunker import ChunkingService
        chunker = ChunkingService(
            chunk_size=options.get("chunk_size", settings.CHUNK_SIZE),
            chunk_overlap=options.get("chunk_overlap", settings.CHUNK_OVERLAP),
        )
        chunks = chunker.chunk_udr(udr)

        # Step 4: embedding (70%)
        _update_job(db, job_id, "embedding", 55)
        import asyncio
        from app.services.embedding import EmbeddingService
        emb_service = EmbeddingService(model=options.get("embedding_model", settings.DEFAULT_EMBEDDING))
        batch_size = 32
        all_texts = [c["content"] for c in chunks]
        all_vectors = []
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i:i + batch_size]
            try:
                vectors = asyncio.new_event_loop().run_until_complete(emb_service.embed_texts(batch))
                all_vectors.extend(vectors)
            except Exception as e:
                logger.error(f"Embedding batch {i} failed: {e}")
                warnings.append(f"Embedding error: {str(e)}")
                all_vectors.extend([[0.0] * settings.QDRANT_VECTOR_SIZE] * len(batch))
            pct = 55 + int((i + len(batch)) / len(all_texts) * 15)
            _update_job(db, job_id, "embedding", min(pct, 70))

        for i, chunk_data in enumerate(chunks):
            chunk_data["embedding"] = all_vectors[i] if i < len(all_vectors) else []
            db_chunk = DocumentChunk(
                document_id=doc.id, kb_id=kb_id, chunk_index=i,
                content=chunk_data["content"],
                content_hash=chunk_data.get("content_hash", ""),
                token_count=chunk_data.get("token_count", 0),
                source_block_ids=[],
                metadata_json=chunk_data.get("metadata_json", {}),
                page_number=chunk_data.get("page_number"),
                slide_number=chunk_data.get("slide_number"),
                section_path=chunk_data.get("section_path"),
            )
            db.add(db_chunk)
        db.commit()
        doc.parse_status = "parsed"
        db.commit()

        # Step 5: indexing — Qdrant (85%)
        _update_job(db, job_id, "indexing", 75)
        from app.services.qdrant_store import QdrantService
        qdrant = QdrantService()

        # Validate dimension — NEVER recreate collection
        if all_vectors and len(all_vectors[0]) != qdrant.vector_size:
            error_msg = (
                f"Vector dimension mismatch: got {len(all_vectors[0])}d, "
                f"Qdrant collection expects {qdrant.vector_size}d. "
                f"Update QDRANT_VECTOR_SIZE={len(all_vectors[0])} in .env and restart."
            )
            logger.error(error_msg)
            _update_job(db, job_id, "failed", 75, error_message=error_msg, finished_at=datetime.utcnow())
            doc.parse_status = "failed"
            db.commit()
            db.close()
            return {"status": "failed", "error": error_msg}

        try:
            eids = asyncio.new_event_loop().run_until_complete(qdrant.upsert_chunks(chunks, kb_id))
            chunk_objs = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).order_by(DocumentChunk.chunk_index).all()
            for i, co in enumerate(chunk_objs):
                if i < len(eids):
                    co.embedding_id = eids[i]
            db.commit()
            doc.index_status = "indexed"
            db.commit()
        except Exception as e:
            logger.error(f"Qdrant indexing failed: {e}")
            warnings.append(f"Qdrant error: {str(e)}")
            doc.index_status = "failed"
            db.commit()

        # Step 6: checking (95%)
        _update_job(db, job_id, "checking", 90)
        block_cnt = db.query(DocumentBlock).filter(DocumentBlock.document_id == doc.id).count()
        chunk_cnt = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        quality_report = {
            "text_length": sum(len(b.text or "") for b in udr.blocks),
            "block_count": block_cnt, "chunk_count": chunk_cnt,
            "table_count": sum(1 for b in udr.blocks if b.type == "table"),
            "image_count": sum(1 for b in udr.blocks if b.type == "image"),
            "audio_duration": 0, "video_duration": 0,
            "ocr_confidence_avg": None, "asr_confidence_avg": None,
            "empty_page_count": 0, "failed_blocks": 0, "warnings": warnings,
        }
        doc.metadata_json = doc.metadata_json or {}
        doc.metadata_json["quality_report"] = quality_report
        if doc.index_status == "failed":
            doc.parse_status = "partially_completed"
        elif warnings:
            doc.parse_status = "partially_completed"
        else:
            doc.parse_status = "completed"
        doc.embed_status = "completed" if doc.index_status != "failed" else "failed"
        db.commit()

        # Step 7: completed
        _update_job(db, job_id, "completed", 100, finished_at=datetime.utcnow(),
                     warnings_json=warnings if warnings else None)

        return {"status": "completed", "document_id": document_id,
                "block_count": block_cnt, "chunk_count": chunk_cnt, "warnings": warnings}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Ingest failed [{document_id}]: {e}\n{tb}")
        _update_job(db, job_id, "failed", 0,
                     error_message=str(e), finished_at=datetime.utcnow())
        try:
            from app.models.models import Document
            d = db.get(Document, document_id)
            if d:
                d.parse_status = "failed"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@celery_app.task(bind=True, name="reparse_document")
def reparse_document(self, document_id: str, kb_id: str, options: dict = None):
    """重新解析 — 清理旧数据后重新 ingest（只传 document_id/kb_id）"""
    db = _get_sync_session()
    try:
        from app.models.models import Document, DocumentBlock, DocumentChunk, IngestJob
        from app.services.qdrant_store import QdrantService

        db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        try:
            QdrantService().delete_by_document(document_id)
        except Exception as e:
            logger.warning(f"Qdrant cleanup failed: {e}")

        doc = db.get(Document, document_id)
        if doc:
            doc.parse_status = "pending"
            doc.embed_status = "pending"
            doc.index_status = "pending"
            doc.document_version = (doc.document_version or 0) + 1
            db.commit()

        job = IngestJob(kb_id=kb_id, document_id=document_id,
                         job_type="reparse", status="pending")
        db.add(job)
        db.commit()

        # 只传 document_id 和 kb_id，不传 file_path
        ingest_document.apply_async(args=[document_id, kb_id, options], task_id=str(job.id))
        return {"status": "submitted", "job_id": str(job.id), "document_id": document_id}
    finally:
        db.close()
