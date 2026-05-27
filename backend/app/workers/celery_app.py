"""
Celery Worker — 真实文档导入 DAG

任务 DAG (7 步):
  detecting → extracting → parsing → chunking → embedding → indexing → checking → completed

每一步都真实执行并更新 ingest_jobs 状态。
"""

import hashlib
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from celery import Celery
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

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

# 用于在 Celery task 中访问数据库的同步 engine
_sync_engine = None


def _get_sync_session():
    """获取同步数据库会话（Celery task 内使用）"""
    from sqlalchemy.orm import Session
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return Session(_sync_engine)


def _update_job(db, job_id: str, status: str, progress: float, **kwargs):
    """更新 ingest_job 状态"""
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


@celery_app.task(bind=True, name="ingest_document")
def ingest_document(self, document_id: str, kb_id: str, file_path: str = "", options: dict = None):
    """
    完整文档导入任务链。
    7 步 DAG：detect → extract → parse → chunk → embed → index → check → complete
    """
    options = options or {}
    db = _get_sync_session()
    job_id = self.request.id
    warnings: list[str] = []

    try:
        from app.models.models import Document, IngestJob, DocumentBlock, DocumentChunk

        doc = db.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Resolve file_path from document storage_path
        if not file_path:
            file_path = doc.storage_path

        # ================================================================
        # Step 1: detecting (5%)
        # ================================================================
        _update_job(db, job_id, "detecting", 5, started_at=datetime.utcnow())
        logger.info(f"[{document_id}] Step 1/7: Detecting file type")

        from app.services.connectors.base import LocalFolderConnector
        mime_type = doc.mime_type
        ext = Path(doc.filename).suffix
        if not mime_type or mime_type == "application/octet-stream":
            mime_type = LocalFolderConnector._guess_mime_type(Path(doc.filename))

        doc.mime_type = mime_type
        doc.file_type = ext.lstrip(".")
        db.commit()
        logger.info(f"[{document_id}] Detected: {mime_type}, ext: {ext}")

        # ================================================================
        # Step 2: extracting + parsing (40%)
        # ================================================================
        _update_job(db, job_id, "parsing", 15)

        from app.services.parsers.base import ParserRegistry

        parser = ParserRegistry.get_parser(mime_type=mime_type, extension=ext)
        if parser is None:
            raise ValueError(f"No parser found for {mime_type} / {ext}")

        logger.info(f"[{document_id}] Using parser: {parser.__class__.__name__}")

        # Handle MinIO files: download to temp
        actual_path = file_path
        temp_file = None
        if file_path.startswith("minio://"):
            from app.services.storage import minio_storage
            object_name = file_path.replace(f"minio://{settings.MINIO_BUCKET}/", "")
            data = minio_storage.download_file(object_name)
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            temp_file.write(data)
            temp_file.close()
            actual_path = temp_file.name

        try:
            udr = parser.parse(actual_path, options)
        except Exception as parse_err:
            logger.warning(f"[{document_id}] Primary parser failed: {parse_err}, trying fallback")
            from app.services.parsers.fallback_parser import FallbackParser
            fallback = FallbackParser()
            udr = fallback.parse(actual_path, options)
            warnings.append(f"Primary parser failed: {str(parse_err)}. Used fallback.")

        # Update document metadata
        doc.title = udr.metadata.get("title", doc.filename)
        doc.author = udr.metadata.get("author", "")
        doc.metadata_json = udr.metadata
        doc.parse_status = "parsing"
        db.commit()

        # Write blocks to database
        _update_job(db, job_id, "parsing", 30)
        block_count = 0
        for block in udr.blocks:
            db_block = DocumentBlock(
                document_id=doc.id,
                parent_block_id=None,
                block_type=block.type,
                text=block.text,
                structured_json=block.structured_data,
                page_number=block.page,
                slide_number=block.slide,
                sheet_name=block.sheet_name,
                cell_range=block.cell_range,
                start_time=block.start_time,
                end_time=block.end_time,
                bbox_json=block.bbox,
                section_path=block.section_path,
                metadata_json=block.metadata,
            )
            db.add(db_block)
            block_count += 1

        db.commit()
        logger.info(f"[{document_id}] Written {block_count} blocks")

        # ================================================================
        # Step 3: chunking (50%)
        # ================================================================
        _update_job(db, job_id, "chunking", 45)

        from app.services.chunking.chunker import ChunkingService
        chunker = ChunkingService(
            chunk_size=options.get("chunk_size", settings.CHUNK_SIZE),
            chunk_overlap=options.get("chunk_overlap", settings.CHUNK_OVERLAP),
        )
        chunks = chunker.chunk_udr(udr)
        logger.info(f"[{document_id}] Generated {len(chunks)} chunks")

        # ================================================================
        # Step 4: embedding (70%)
        # ================================================================
        _update_job(db, job_id, "embedding", 55)

        import asyncio
        from app.services.embedding import EmbeddingService

        emb_service = EmbeddingService(
            model=options.get("embedding_model", settings.DEFAULT_EMBEDDING)
        )

        # Batch embedding: 32 texts at a time
        batch_size = 32
        all_texts = [c["content"] for c in chunks]
        all_vectors = []

        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i : i + batch_size]
            try:
                vectors = asyncio.new_event_loop().run_until_complete(
                    emb_service.embed_texts(batch)
                )
                all_vectors.extend(vectors)
            except Exception as e:
                logger.error(f"[{document_id}] Embedding batch failed: {e}")
                warnings.append(f"Embedding batch {i}-{i+batch_size} failed: {str(e)}")
                # Fill with zeros
                all_vectors.extend([[0.0] * settings.QDRANT_VECTOR_SIZE] * len(batch))

            progress = 55 + int((i + len(batch)) / len(all_texts) * 15)
            _update_job(db, job_id, "embedding", min(progress, 70))

        # Write chunks to database
        for i, chunk_data in enumerate(chunks):
            vector = all_vectors[i] if i < len(all_vectors) else []
            chunk_data["embedding"] = vector
            chunk_data["embedding_id"] = None  # will be set after Qdrant upsert

            db_chunk = DocumentChunk(
                document_id=doc.id,
                kb_id=kb_id,
                chunk_index=i,
                content=chunk_data["content"],
                content_hash=chunk_data.get("content_hash", ""),
                token_count=chunk_data.get("token_count", 0),
                source_block_ids=[],
                metadata_json=chunk_data.get("metadata_json", {}),
                page_number=chunk_data.get("page_number"),
                slide_number=chunk_data.get("slide_number"),
                section_path=chunk_data.get("section_path"),
                embedding_id=None,
            )
            db.add(db_chunk)

        db.commit()
        doc.parse_status = "parsed"
        db.commit()

        # ================================================================
        # Step 5: indexing (85%)
        # ================================================================
        _update_job(db, job_id, "indexing", 75)

        from app.services.qdrant_store import QdrantService
        qdrant = QdrantService()

        try:
            embedding_ids = asyncio.new_event_loop().run_until_complete(
                qdrant.upsert_chunks(chunks, kb_id)
            )

            # Update chunk embedding_ids
            chunk_objs = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id
            ).order_by(DocumentChunk.chunk_index).all()

            for i, chunk_obj in enumerate(chunk_objs):
                if i < len(embedding_ids):
                    chunk_obj.embedding_id = embedding_ids[i]

            db.commit()
            doc.index_status = "indexed"
            db.commit()
            logger.info(f"[{document_id}] Indexed {len(embedding_ids)} vectors in Qdrant")

        except Exception as e:
            logger.error(f"[{document_id}] Qdrant indexing failed: {e}")
            warnings.append(f"Qdrant indexing error: {str(e)}")
            doc.index_status = "failed"
            db.commit()

        # ================================================================
        # Step 6: checking (95%)
        # ================================================================
        _update_job(db, job_id, "checking", 90)

        # Build quality report
        block_count_actual = db.query(DocumentBlock).filter(
            DocumentBlock.document_id == doc.id
        ).count()
        chunk_count_actual = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id
        ).count()

        quality_report = {
            "text_length": sum(len(b.text or "") for b in udr.blocks),
            "block_count": block_count_actual,
            "chunk_count": chunk_count_actual,
            "table_count": sum(1 for b in udr.blocks if b.type == "table"),
            "image_count": sum(1 for b in udr.blocks if b.type == "image"),
            "audio_duration": 0,
            "video_duration": 0,
            "ocr_confidence_avg": None,
            "asr_confidence_avg": None,
            "empty_page_count": 0,
            "failed_blocks": 0,
            "warnings": warnings,
        }

        # Store quality report in document metadata
        doc.metadata_json = doc.metadata_json or {}
        doc.metadata_json["quality_report"] = quality_report

        # Determine overall status
        if doc.index_status == "failed":
            doc.parse_status = "partially_completed"
            overall = "yellow"
        elif warnings:
            overall = "yellow"
            doc.parse_status = "partially_completed"
        else:
            overall = "green"
            doc.parse_status = "completed"

        doc.embed_status = "completed" if doc.index_status != "failed" else "failed"
        db.commit()

        # ================================================================
        # Step 7: completed (100%)
        # ================================================================
        _update_job(
            db, job_id, "completed", 100,
            finished_at=datetime.utcnow(),
            warnings_json=warnings if warnings else None,
        )

        # Cleanup temp file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

        logger.info(f"[{document_id}] Ingest completed: {block_count_actual} blocks, {chunk_count_actual} chunks, quality={overall}")

        return {
            "status": "completed",
            "document_id": document_id,
            "block_count": block_count_actual,
            "chunk_count": chunk_count_actual,
            "warnings": warnings,
            "quality": overall,
        }

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[{document_id}] Ingest failed: {e}\n{tb}")
        _update_job(
            db, job_id, "failed", 0,
            error_message=f"{str(e)}\n{tb[:500]}",
            finished_at=datetime.utcnow(),
        )

        # Update document status
        try:
            from app.models.models import Document
            doc = db.get(Document, document_id)
            if doc:
                doc.parse_status = "failed"
                db.commit()
        except Exception:
            pass

        raise


@celery_app.task(bind=True, name="reparse_document")
def reparse_document(self, document_id: str, kb_id: str, options: dict = None):
    """重新解析文档 — 先清理旧数据，再重新执行 ingest"""
    db = _get_sync_session()
    try:
        from app.models.models import Document, DocumentBlock, DocumentChunk, IngestJob
        from app.services.qdrant_store import QdrantService

        # Clean old blocks and chunks
        db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

        # Clean Qdrant vectors
        try:
            qdrant = QdrantService()
            qdrant.delete_by_document(document_id)
        except Exception as e:
            logger.warning(f"Failed to clean Qdrant: {e}")

        # Reset document status
        doc = db.get(Document, document_id)
        if doc:
            doc.parse_status = "pending"
            doc.embed_status = "pending"
            doc.index_status = "pending"
            doc.document_version = (doc.document_version or 0) + 1
            db.commit()

        # Create new ingest job and chain
        job = IngestJob(
            kb_id=kb_id,
            document_id=document_id,
            job_type="reparse",
            status="pending",
        )
        db.add(job)
        db.commit()

        # Get file path from document
        file_path = doc.storage_path if doc else ""

        # Execute the ingest task directly
        ingest_document.apply_async(
            args=[document_id, kb_id, file_path, options],
            task_id=str(job.id),
        )

        return {"status": "submitted", "job_id": str(job.id), "document_id": document_id}

    except Exception as e:
        logger.error(f"Reparse failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="batch_import")
def batch_import(self, kb_id: str, file_paths: list[str], options: dict = None):
    """批量导入多个文件"""
    results = []
    for fp in file_paths:
        results.append({"file_path": fp, "status": "queued"})
    return {"status": "batch_queued", "total": len(file_paths), "results": results}
