"""文档管理 API 路由 — 真实上传链路 + 数据库查询"""

import hashlib
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from loguru import logger
from sqlalchemy import desc, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_device
from app.models.models import (
    Document, DocumentBlock, DocumentChunk, DocumentAsset,
    IngestJob, TableObject, KnowledgeBase,
)
from app.schemas.schemas import DocumentResponse
from app.services.storage import minio_storage

settings = get_settings()
router = APIRouter()


def _mask_storage_path(path: str) -> str:
    """Mask full local/MinIO paths — only return last 2 segments"""
    if not path:
        return ""
    parts = path.replace("\\", "/").rstrip("/").split("/")
    visible = parts[-2:] if len(parts) >= 2 else parts
    return ".../" + "/".join(visible)


def _mask_path(path: str) -> str:
    """Mask absolute paths — return filename only"""
    if not path:
        return ""
    for prefix in ("/Users/", "/home/", "C:\\", "minio://"):
        if path.startswith(prefix):
            return path.replace("\\", "/").split("/")[-1]
    return path


def _compute_sha256(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return f"sha256:{sha.hexdigest()}"


def _guess_mime_and_type(filename: str) -> tuple[str, str]:
    ext = Path(filename).suffix.lower()
    ext_map = {
        ".md": ("text/markdown", "md"),
        ".txt": ("text/plain", "txt"),
        ".pdf": ("application/pdf", "pdf"),
        ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
        ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
        ".tex": ("application/x-latex", "tex"),
        ".html": ("text/html", "html"),
        ".py": ("text/x-python", "py"),
        ".js": ("text/javascript", "js"),
        ".ts": ("text/typescript", "ts"),
        ".jpg": ("image/jpeg", "jpg"),
        ".jpeg": ("image/jpeg", "jpeg"),
        ".png": ("image/png", "png"),
        ".webp": ("image/webp", "webp"),
        ".mp3": ("audio/mpeg", "mp3"),
        ".wav": ("audio/wav", "wav"),
        ".m4a": ("audio/mp4", "m4a"),
        ".mp4": ("video/mp4", "mp4"),
        ".mov": ("video/quicktime", "mov"),
        ".mkv": ("video/x-matroska", "mkv"),
        ".zip": ("application/zip", "zip"),
        ".tar.gz": ("application/gzip", "tar.gz"),
    }
    return ext_map.get(ext, ("application/octet-stream", ext.lstrip(".") or "unknown"))


# ================================================================
# File Upload — Real Pipeline
# ================================================================
@router.post("/kbs/{kb_id}/documents/upload")
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_device: dict = Depends(get_current_device),
):
    """真实文件上传链路：hash → 去重 → MinIO → document → job → Celery"""
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 1. Save temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename or "upload")
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 2. Compute hash
        file_hash = _compute_sha256(temp_path)
        mime_type, file_type = _guess_mime_and_type(file.filename or "unknown")

        # 3. Check dedup — same hash in same kb
        existing = (await db.execute(
            select(Document).where(
                Document.kb_id == kb_id,
                Document.file_hash == file_hash,
                Document.is_deleted == False,
            )
        )).scalar()

        if existing:
            # Dedup: return existing document
            logger.info(f"Dedup: file {file.filename} already exists as {existing.id}")
            return {
                "message": "File already exists (dedup)",
                "document_id": str(existing.id),
                "duplicate": True,
                "parse_status": existing.parse_status,
                "status": existing.status,
            }

        # 4. Upload to MinIO
        file_size = os.path.getsize(temp_path)
        object_name = f"{kb_id}/{uuid.uuid4().hex}{Path(file.filename).suffix}"
        minio_storage.upload_file(
            object_name=object_name,
            file_path=temp_path,
            content_type=mime_type,
        )
        storage_path = f"minio://{settings.MINIO_BUCKET}/{object_name}"
        logger.info(f"Uploaded to MinIO: {object_name}")

        # 5. Create document record
        doc = Document(
            kb_id=kb_id,
            filename=file.filename or "unknown",
            original_filename=file.filename or "unknown",
            file_type=file_type,
            mime_type=mime_type,
            file_size=file_size,
            file_hash=file_hash,
            storage_path=storage_path,
            source_type="upload",
            source_uri=None,
            document_version=1,
            parse_status="pending",
            embed_status="pending",
            index_status="pending",
            title=file.filename,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id_str = str(doc.id)
        kb_id_str = str(kb_id)

        # 6. Create ingest job
        job = IngestJob(
            kb_id=kb_id,
            document_id=doc.id,
            job_type="ingest",
            status="PENDING",
            progress=0.0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id_str = str(job.id)

        # 7. Dispatch Celery task (只传 document_id + kb_id)
        try:
            from app.workers.celery_app import ingest_document
            ingest_document.apply_async(
                args=[doc_id_str, kb_id_str],
                task_id=job_id_str,
            )
            logger.info(f"Dispatched Celery task {job_id_str} for doc {doc_id_str}")
        except Exception as e:
            logger.error(f"Failed to dispatch Celery task: {e}")
            job.status = "FAILED"
            job.error_message = f"Celery dispatch failed: {str(e)}"
            await db.commit()

        return {
            "message": "Document uploaded and ingest job created",
            "document_id": doc_id_str,
            "job_id": job_id_str,
            "duplicate": False,
            "parse_status": doc.parse_status,
            "status": doc.status,
            "file_hash": file_hash,
            "file_size": file_size,
            "mime_type": mime_type,
        }

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Cleanup temp
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ================================================================
# Folder Import
# ================================================================
@router.post("/kbs/{kb_id}/documents/import-folder")
async def import_folder(
    kb_id: uuid.UUID,
    folder_path: str = Form(...),
    recursive: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
    current_device: dict = Depends(get_current_device),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    from app.services.connectors.base import LocalFolderConnector
    connector = LocalFolderConnector()
    files = connector.scan({"path": folder_path, "recursive": recursive})

    # Create import jobs for each file (batch)
    imported = []
    for fobj in files:
        # Simple file copy + upload flow for each file
        try:
            file_hash = fobj.checksum if fobj.checksum.startswith("sha256:") else _compute_sha256(fobj.file_path)
            mime_type = fobj.mime_type

            # Check dedup
            existing = (await db.execute(
                select(Document).where(
                    Document.kb_id == kb_id,
                    Document.file_hash == file_hash,
                    Document.is_deleted == False,
                )
            )).scalar()

            if existing:
                imported.append({"filename": fobj.filename, "status": "duplicate", "document_id": str(existing.id)})
                continue

            # Upload to MinIO
            object_name = f"{kb_id}/{uuid.uuid4().hex}{Path(fobj.filename).suffix}"
            minio_storage.upload_file(
                object_name=object_name,
                file_path=fobj.file_path,
                content_type=mime_type,
            )

            doc = Document(
                kb_id=kb_id,
                filename=fobj.filename,
                original_filename=fobj.filename,
                file_type=Path(fobj.filename).suffix.lstrip("."),
                mime_type=mime_type,
                file_size=fobj.size,
                file_hash=file_hash,
                storage_path=f"minio://{settings.MINIO_BUCKET}/{object_name}",
                source_type=fobj.source_type,
                source_uri=fobj.source_uri,
                parse_status="pending",
                embed_status="pending",
                index_status="pending",
                title=fobj.filename,
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)

            job = IngestJob(kb_id=kb_id, document_id=doc.id, job_type="ingest", status="PENDING")
            db.add(job)
            await db.commit()
            await db.refresh(job)

            try:
                from app.workers.celery_app import ingest_document
                ingest_document.apply_async(
                    args=[str(doc.id), str(kb_id)],
                    task_id=str(job.id),
                )
            except Exception:
                pass

            imported.append({"filename": fobj.filename, "status": "imported", "document_id": str(doc.id), "job_id": str(job.id)})

        except Exception as e:
            logger.error(f"Failed to import {fobj.filename}: {e}")
            imported.append({"filename": fobj.filename, "status": "failed", "error": str(e)})

    return {
        "message": f"Imported {len(imported)} files",
        "total_scanned": len(files),
        "imported": imported,
    }


# ================================================================

# List moved to kb_routes.py — Phase 3B-hotfix



@router.get("/documents/{doc_id}")
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get latest job for retry info
    from sqlalchemy import desc, select as sqla_select
    last_job = (await db.execute(
        sqla_select(IngestJob).where(IngestJob.document_id == doc.id)
        .order_by(desc(IngestJob.updated_at)).limit(1)
    )).scalar_one_or_none()
    from app.api.system_routes import _sanitize

    block_count = (await db.execute(
        select(func.count(DocumentBlock.id)).where(DocumentBlock.document_id == doc.id)
    )).scalar() or 0
    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)
    )).scalar() or 0
    asset_count = (await db.execute(
        select(func.count(DocumentAsset.id)).where(DocumentAsset.document_id == doc.id)
    )).scalar() or 0

    quality_report = None
    if doc.metadata_json and "quality_report" in doc.metadata_json:
        quality_report = doc.metadata_json["quality_report"]

    return {
        "document_id": str(doc.id), "kb_id": str(doc.kb_id), "filename": doc.filename,
        "original_filename": doc.original_filename, "file_type": doc.file_type,
        "mime_type": doc.mime_type, "file_size": doc.file_size,
        "file_hash": doc.file_hash,
        "object_key": doc.filename,
        "masked_storage_path": _mask_storage_path(doc.storage_path),
        "source_type": doc.source_type, "source_uri": _mask_path(doc.source_uri or ""),
        "document_version": doc.document_version,
        "active_version": doc.active_version,
        "status": doc.status,
        "parse_status": doc.parse_status, "embed_status": doc.embed_status,
        "index_status": doc.index_status,
        "title": doc.title, "author": doc.author,
        "block_count": block_count, "chunk_count": chunk_count, "asset_count": asset_count,
        "quality_report": quality_report,
        "created_at": doc.created_at.isoformat(), "updated_at": doc.updated_at.isoformat(),
        "retry_count": last_job.retry_count if last_job else 0,
        "last_retry_at": doc.last_retry_at.isoformat() if doc.last_retry_at else None,
        "error_message": _sanitize(doc.metadata_json.get("error", "") if doc.metadata_json else ""),
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    import datetime as dt
    doc.is_deleted = True
    doc.deleted_at = dt.datetime.now(dt.timezone.utc)
    doc.status = "DELETED"
    # Document-level soft delete only — chunk soft-delete via document filter
    await db.commit()
    return {
        "document_id": str(doc.id), "deleted": True,
        "cleanup_status": "document_soft_deleted",
        "vectors_cleanup": "pending", "object_cleanup": "pending",
    }


@router.post("/documents/{doc_id}/retry")
async def retry_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                         current_device: dict = Depends(get_current_device), force: bool = False):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot retry a deleted document")
    if doc.status == "READY" and not force:
        raise HTTPException(status_code=400, detail="READY document cannot be retried. Use force=true")
    retryable = doc.status in ("FAILED", "ERROR", "UPLOADED", "PARSING")
    if not retryable and not force:
        raise HTTPException(status_code=400, detail=f"Document status {doc.status} not retryable. Use force=true")

    from sqlalchemy import desc
    last_job = (await db.execute(
        select(IngestJob).where(IngestJob.document_id == doc.id)
        .order_by(desc(IngestJob.updated_at)).limit(1)
    )).scalar_one_or_none()
    retry_count = (last_job.retry_count if last_job else 0) + 1
    if retry_count > 5 and not force:
        raise HTTPException(status_code=400, detail="Retry limit (5) exceeded. Use force=true")

    import datetime as _dt
    new_job = IngestJob(
        kb_id=doc.kb_id, document_id=doc.id, job_type="ingest",
        status="PENDING", retry_count=retry_count,
        last_retry_at=_dt.datetime.now(_dt.timezone.utc),
    )
    db.add(new_job)
    doc.status = "UPLOADED"
    doc.parse_status = "pending"
    doc.embed_status = "pending"
    doc.index_status = "pending"
    doc.last_retry_at = _dt.datetime.now(_dt.timezone.utc)
    await db.commit()
    await db.refresh(new_job)

    # Dispatch Celery task
    try:
        from app.workers.celery_app import ingest_document
        ingest_document.apply_async(
            args=[str(doc.id), str(doc.kb_id)],
            task_id=str(new_job.id),
        )
        return {"document_id": str(doc.id), "job_id": str(new_job.id), "status": "PENDING", "dispatched": True}
    except Exception as e:
        new_job.status = "FAILED"
        new_job.error_message = _sanitize(str(e))[:200]
        doc.status = "FAILED"
        await db.commit()
        return {"success": False, "document_id": str(doc.id), "job_id": str(new_job.id), "error": _sanitize(str(e))[:200]}


@router.post("/documents/{doc_id}/reparse")
async def reparse_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        from app.workers.celery_app import reparse_document
        result = reparse_document.delay(str(doc.id), str(doc.kb_id))
        return {"message": "Reparse job submitted", "document_id": str(doc.id), "job_id": result.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch reparse: {str(e)}")


@router.post("/documents/{doc_id}/reembed")
async def reembed_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    # Reembed = reparse (for MVP)
    return await reparse_document(doc_id, db)


# ================================================================
# Document Detail Views
# ================================================================
@router.get("/documents/{doc_id}/blocks")
async def get_document_blocks(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    result = await db.execute(
        select(DocumentBlock).where(DocumentBlock.document_id == doc_id).order_by(DocumentBlock.created_at)
    )
    blocks = result.scalars().all()
    return {
        "document_id": str(doc_id),
        "total": len(blocks),
        "blocks": [
            {
                "id": b.id, "block_type": b.block_type, "text": (b.text or "")[:500],
                "page_number": b.page_number, "slide_number": b.slide_number,
                "section_path": b.section_path,
            }
            for b in blocks
        ],
    }


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return {
        "document_id": str(doc_id),
        "total": len(chunks),
        "chunks": [
            {
                "id": c.id, "chunk_index": c.chunk_index, "content": c.content[:300],
                "token_count": c.token_count, "embedding_id": c.embedding_id,
            }
            for c in chunks
        ],
    }


@router.get("/documents/{doc_id}/assets")
async def get_document_assets(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    result = await db.execute(
        select(DocumentAsset).where(DocumentAsset.document_id == doc_id)
    )
    assets = result.scalars().all()
    return {"document_id": str(doc_id), "total": len(assets), "assets": [a.__dict__ for a in assets]}


@router.get("/documents/{doc_id}/tables")
async def get_document_tables(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    result = await db.execute(
        select(TableObject).where(TableObject.document_id == doc_id)
    )
    tables = result.scalars().all()
    return {
        "document_id": str(doc_id),
        "total": len(tables),
        "tables": [
            {"id": t.id, "sheet_name": t.sheet_name, "table_name": t.table_name,
             "row_count": t.row_count, "col_count": t.col_count}
            for t in tables
        ],
    }


@router.get("/documents/{doc_id}/quality-report")
async def get_quality_report(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    block_count = (await db.execute(
        select(func.count(DocumentBlock.id)).where(DocumentBlock.document_id == doc.id)
    )).scalar() or 0
    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)
    )).scalar() or 0

    quality_report = doc.metadata_json.get("quality_report", {}) if doc.metadata_json else {}
    quality_report["block_count"] = block_count
    quality_report["chunk_count"] = chunk_count

    # Determine overall status
    if doc.parse_status == "completed":
        overall_status = "green"
    elif doc.parse_status in ("partially_completed", "parsed"):
        overall_status = "yellow"
    elif doc.parse_status == "failed":
        overall_status = "red"
    else:
        overall_status = "blue"

    return {
        "document_id": str(doc.id),
        "parse_quality": quality_report,
        "chunk_quality": {"chunk_count": chunk_count},
        "overall_status": overall_status,
    }


# ================================================================
# Reindex & Consistency APIs — Phase 1.6
# ================================================================
@router.post("/documents/{doc_id}/reindex")
async def reindex_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    """重新索引文档 — API 只设置 REINDEXING，new_version 由 worker 统一计算"""
    doc = await db.get(Document, doc_id)
    if not doc or doc.is_deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "REINDEXING"
    await db.commit()
    try:
        from app.workers.celery_app import reparse_document
        r = reparse_document.delay(str(doc.id), str(doc.kb_id))
        return {"message": "Reindex submitted", "document_id": str(doc.id), "job_id": r.id}
    except Exception as e:
        doc.status = "READY"; await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kbs/{kb_id}/reindex")
async def reindex_kb(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    """重新索引整个知识库"""
    from app.models.models import KnowledgeBase
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    docs_result = await db.execute(select(Document).where(Document.kb_id == kb_id, Document.is_deleted == False, Document.status.in_(["READY", "FAILED"])))
    docs = docs_result.scalars().all()
    jobs = []
    for doc in docs:
        try:
            from app.workers.celery_app import reparse_document
            jobs.append({"document_id": str(doc.id), "job_id": reparse_document.delay(str(doc.id), str(kb_id)).id})
        except Exception as e:
            jobs.append({"document_id": str(doc.id), "error": str(e)})
    return {"message": f"Reindex {len(jobs)} docs", "kb_id": str(kb_id), "jobs": jobs}


@router.get("/kbs/{kb_id}/consistency")
async def check_consistency(kb_id: uuid.UUID, dry_run: bool = True, db = Depends(get_db), current_device: dict = Depends(get_current_device)):
    """检查知识库 PostgreSQL ↔ Qdrant 一致性"""
    from app.services.consistency.checker import check_index_consistency, repair_index
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    db_sync = Session(engine)
    try:
        if dry_run:
            return {"dry_run": True, "report": check_index_consistency(str(kb_id), db_sync).to_dict()}
        return repair_index(str(kb_id), db_sync, dry_run=False)
    finally:
        db_sync.close()


# ============================================================
