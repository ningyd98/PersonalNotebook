"""
Celery Worker — 真实文档导入 DAG (Phase 1.6 修复)

状态规范:
  job.status ∈ {PENDING, RUNNING, RETRYING, SUCCESS, FAILED, CANCELLED}
  job.phase ∈ {detecting, parsing, chunking, embedding, indexing, checking}

文档状态机 (DocStateMachine):
  UPLOADED → PARSING → PARSED → CHUNKING → EMBEDDING → INDEXING → READY

双缓冲 reindex:
  保留旧 version，新建 version={doc.document_version+1}，校验后切换 active_version
"""

import asyncio
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

import app.services.parsers  # noqa: E402 — 触发 parser 注册


# ─── helpers ──────────────────────────────────────────────
def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_size=5, max_overflow=10, pool_pre_ping=True)
    return Session(engine)


def _update_job(db, job_id, status, progress, phase=None, **kwargs):
    """
    job.status 只允许 PENDING|RUNNING|RETRYING|SUCCESS|FAILED|CANCELLED
    job.phase 记录详细步骤: detecting|parsing|chunking|embedding|indexing|checking
    """
    from app.models.models import IngestJob
    job = db.get(IngestJob, job_id)
    if not job:
        return
    job.status = status
    job.progress = progress
    if phase:
        job.phase = phase
    for k, v in kwargs.items():
        if hasattr(job, k):
            setattr(job, k, v)
    db.commit()


def _transition_doc(db, doc, new_state, reason=None):
    from app.services.document_state import DocStateMachine
    ok = DocStateMachine.transition(doc, new_state, reason=reason)
    if ok:
        db.commit()
    return ok


def _download_from_minio(storage_path: str) -> str:
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


# ─── ingest — 7-step DAG (status/phase 分离) ────────────
@celery_app.task(bind=True, name="ingest_document")
def ingest_document(self, document_id: str, kb_id: str, options: dict = None):
    options = options or {}
    db = _get_sync_session()
    job_id = self.request.id
    warnings: list[str] = []
    tmp_path = None
    version = int(options.get("version", 0))
    is_reindex = bool(options.get("reindex", False))

    try:
        from app.models.models import Document, DocumentBlock, DocumentChunk
        from app.services.document_state import DocStateMachine

        doc = db.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # ── Step 1: detecting ──────────────────────────
        _update_job(db, job_id, status="RUNNING", progress=5, phase="detecting", started_at=datetime.utcnow())
        _transition_doc(db, doc, "PARSING", "ingest start")

        mime_type = doc.mime_type
        ext = Path(doc.filename).suffix
        if not mime_type or mime_type == "application/octet-stream":
            from app.services.connectors.base import LocalFolderConnector
            mime_type = LocalFolderConnector._guess_mime_type(Path(doc.filename))
        doc.mime_type = mime_type
        doc.file_type = ext.lstrip(".")
        db.commit()

        # ── Step 2: parse ──────────────────────────────
        _update_job(db, job_id, status="RUNNING", progress=15, phase="parsing")
        tmp_path = _download_from_minio(doc.storage_path)

        from app.services.parsers.base import ParserRegistry
        parser = ParserRegistry.get_parser(mime_type=mime_type, extension=ext)
        if parser is None:
            raise ValueError(f"No parser for {mime_type} / {ext}")

        try:
            udr = parser.parse(tmp_path, options)
        except Exception as parse_err:
            logger.warning(f"Primary parser failed: {parse_err}")
            from app.services.parsers.fallback_parser import FallbackParser
            udr = FallbackParser().parse(tmp_path, options)
            warnings.append(f"Parser fallback: {str(parse_err)}")

        udr.document_id = str(doc.id)
        doc.title = udr.metadata.get("title", doc.filename)
        doc.author = udr.metadata.get("author", "")
        doc.metadata_json = udr.metadata
        doc.parse_status = "parsing"
        _transition_doc(db, doc, "PARSED", "parse complete")
        db.commit()

        # Write blocks
        block_count = 0
        for block in udr.blocks:
            db.add(DocumentBlock(
                document_id=doc.id, block_type=block.type, text=block.text,
                structured_json=block.structured_data,
                page_number=block.page, slide_number=block.slide,
                sheet_name=block.sheet_name, cell_range=block.cell_range,
                start_time=block.start_time, end_time=block.end_time,
                bbox_json=block.bbox, section_path=block.section_path,
                metadata_json=block.metadata,
            ))
            block_count += 1
        db.commit()

        # ── Step 3: chunking ───────────────────────────
        _update_job(db, job_id, status="RUNNING", progress=45, phase="chunking")
        _transition_doc(db, doc, "CHUNKING", "chunking start")

        from app.services.chunking.chunker import ChunkingService
        chunker = ChunkingService(
            chunk_size=options.get("chunk_size", settings.CHUNK_SIZE),
            chunk_overlap=options.get("chunk_overlap", settings.CHUNK_OVERLAP),
        )
        chunks = chunker.chunk_udr(udr)

        # ── Step 4: embedding ──────────────────────────
        _update_job(db, job_id, status="RUNNING", progress=55, phase="embedding")
        _transition_doc(db, doc, "EMBEDDING", "embedding start")

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
            _update_job(db, job_id, status="RUNNING", progress=min(pct, 70), phase="embedding")

        for i, chunk_data in enumerate(chunks):
            chunk_data["embedding"] = all_vectors[i] if i < len(all_vectors) else []
            cversion = version if version > 0 else (doc.document_version or 1)
            db.add(DocumentChunk(
                document_id=doc.id, kb_id=kb_id, chunk_index=i,
                content=chunk_data["content"],
                content_hash=chunk_data.get("content_hash", ""),
                token_count=chunk_data.get("token_count", 0),
                source_block_ids=[],
                metadata_json=chunk_data.get("metadata_json", {}),
                page_number=chunk_data.get("page_number"),
                slide_number=chunk_data.get("slide_number"),
                section_path=chunk_data.get("section_path"),
                version_id=cversion,
            ))
        db.commit()
        doc.parse_status = "parsed"

        # ── Step 5: indexing ───────────────────────────
        _update_job(db, job_id, status="RUNNING", progress=75, phase="indexing")
        _transition_doc(db, doc, "INDEXING", "indexing start")

        from app.services.qdrant_store import QdrantService
        qdrant = QdrantService()

        if all_vectors and len(all_vectors[0]) != qdrant.vector_size:
            err = (f"Vector dim mismatch: got {len(all_vectors[0])}d, "
                   f"expected {qdrant.vector_size}d. Update QDRANT_VECTOR_SIZE.")
            logger.error(err)
            _update_job(db, job_id, status="FAILED", progress=75, phase="indexing",
                         error_message=err, finished_at=datetime.utcnow())
            _transition_doc(db, doc, "FAILED", err)
            db.close()
            return {"status": "FAILED", "error": err}

        try:
            cversion = version if version > 0 else (doc.document_version or 1)
            # Query freshly-created DB chunks to get real IDs
            db_chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id,
                DocumentChunk.version_id == cversion,
            ).order_by(DocumentChunk.chunk_index).all()
            # Build Qdrant payload with real DB IDs
            qdrant_chunks = []
            for i, dc in enumerate(db_chunks):
                chunk_data = chunks[i] if i < len(chunks) else {}
                qdrant_chunks.append({
                    "embedding": chunk_data.get("embedding", all_vectors[i] if i < len(all_vectors) else []),
                    "document_id": str(doc.id),
                    "kb_id": str(kb_id),
                    "chunk_index": dc.chunk_index,
                    "content": dc.content or "",
                    "content_hash": dc.content_hash or "",
                    "section_path": dc.section_path or "",
                    "page_number": dc.page_number,
                    "slide_number": dc.slide_number,
                    "source_type": chunk_data.get("source_type", "text"),
                    "filename": doc.filename,
                    "metadata_json": chunk_data.get("metadata_json", {}),
                    "version_id": cversion,
                    "tenant_id": "default",
                    "chunk_id": str(dc.id),
                })
            eids = asyncio.new_event_loop().run_until_complete(qdrant.upsert_chunks(qdrant_chunks, kb_id))
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

        # ── Step 6: checking + version switch ──────────
        _update_job(db, job_id, status="RUNNING", progress=90, phase="checking")
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
            _transition_doc(db, doc, "FAILED", "indexing failed")
        else:
            # 成功 → 切换 active_version
            new_version = version if version > 0 else (doc.document_version or 1)
            doc.active_version = new_version
            doc.parse_status = "completed"
            doc.embed_status = "completed"
            _transition_doc(db, doc, "READY", f"active_version={new_version}")

            # 如果旧版本存在，标记 is_active=False（延迟清理）
            try:
                _deactivate_old_version(qdrant, str(doc.id), new_version)
            except Exception as e:
                logger.warning(f"Failed to deactivate old version: {e}")
                warnings.append(f"version_deactivate_error: {e}")

        doc.embed_status = "completed" if doc.index_status != "failed" else "failed"
        db.commit()

        # ── Step 7: done ───────────────────────────────
        _update_job(db, job_id, status="SUCCESS", progress=100, phase="completed",
                     finished_at=datetime.utcnow(),
                     warnings_json=warnings if warnings else None)

        return {"status": "SUCCESS", "document_id": document_id,
                "block_count": block_cnt, "chunk_count": chunk_cnt, "warnings": warnings}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Ingest failed [{document_id}]: {e}\n{tb}")
        _update_job(db, job_id, status="FAILED", progress=0, phase="failed",
                     error_message=str(e), finished_at=datetime.utcnow())
        try:
            from app.models.models import Document
            d = db.get(Document, document_id)
            if d:
                d.parse_status = "failed"
                _transition_doc(db, d, "FAILED", str(e)[:200])
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


def _deactivate_old_version(qdrant, document_id: str, new_version: int):
    """先标记 new_version is_active=True，再标记 version_id != new_version 为 is_active=False"""
    from qdrant_client.http import models as qm
    try:
        # Step 1: Ensure new version vectors are active
        qdrant.client.set_payload(
            collection_name=qdrant.collection_name,
            payload={"is_active": True},
            points=qm.FilterSelector(
                filter=qm.Filter(must=[
                    qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id)),
                    qm.FieldCondition(key="version_id", match=qm.MatchValue(value=new_version)),
                ])
            ),
        )
        logger.info(f"Activated version {new_version} for doc {document_id}")
    except Exception as e:
        logger.warning(f"Failed to activate new_version={new_version} for doc {document_id}: {e}")
        raise

    try:
        # Step 2: Deactivate old versions (version_id != new_version)
        qdrant.client.set_payload(
            collection_name=qdrant.collection_name,
            payload={"is_active": False},
            points=qm.FilterSelector(
                filter=qm.Filter(must=[
                    qm.FieldCondition(key="document_id", match=qm.MatchValue(value=document_id)),
                    qm.FieldCondition(key="version_id", match=qm.MatchExcept(value=new_version)),
                ])
            ),
        )
        logger.info(f"Deactivated old versions for doc {document_id} (kept v{new_version})")
    except Exception as e:
        logger.warning(f"Failed to deactivate old versions for doc {document_id}: {e}")
        raise


# ─── reparse — 真正双缓冲 ───────────────────────────────
@celery_app.task(bind=True, name="reparse_document")
def reparse_document(self, document_id: str, kb_id: str, options: dict = None):
    """
    双缓冲重新索引:
    a) 保留旧 version 继续服务
    b) 新建 new_version = document_version + 1
    c) 新 blocks/chunks/vector 带 version_id=new_version
    d) 成功 → active_version=new_version, 旧版本延迟清理
    e) 失败 → 旧 active_version 继续可用
    """
    options = options or {}
    db = _get_sync_session()
    try:
        from app.models.models import Document, IngestJob

        doc = db.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # 计算新版本号
        new_version = (doc.document_version or 0) + 1
        doc.document_version = new_version
        doc.status = "REINDEXING"
        doc.parse_status = "pending"
        doc.embed_status = "pending"
        doc.index_status = "pending"
        db.commit()

        # 创建 job
        job = IngestJob(
            kb_id=kb_id, document_id=document_id,
            job_type="reparse", status="PENDING",
        )
        db.add(job)
        db.commit()

        # 将 version 传入 options，ingest 会据此写 chunk/Qdrant
        reindex_options = {**options, "version": new_version, "reindex": True}
        ingest_document.apply_async(
            args=[document_id, kb_id, reindex_options],
            task_id=str(job.id),
        )

        return {"status": "PENDING", "job_id": str(job.id),
                "document_id": document_id, "new_version": new_version}
    finally:
        db.close()
