"""知识库 API 路由 — 真实数据库查询"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select, case
from sqlalchemy.sql import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Document, DocumentChunk, IngestJob, KnowledgeBase
from app.schemas.schemas import KBCreate, KBResponse, KBUpdate, PaginatedResponse
from app.dependencies.auth import get_current_device
from app.api.system_routes import _sanitize

router = APIRouter()

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def _verify_kb_ownership(db_result, current_user_id: str = DEFAULT_USER_ID):
    """校验知识库归属"""
    if not db_result:
        return
    uid = str(db_result.user_id) if hasattr(db_result, 'user_id') else None
    if uid and uid != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied: not your knowledge base")


@router.post("/kbs", response_model=KBResponse)
async def create_kb(req: KBCreate, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    kb = KnowledgeBase(
        user_id=uuid.UUID(DEFAULT_USER_ID),
        name=req.name,
        description=req.description,
        default_llm=req.default_llm,
        embedding_model=req.embedding_model,
        rerank_model=req.rerank_model,
        chunk_strategy=req.chunk_strategy,
        visibility=req.visibility,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return _kb_to_response(kb)


@router.get("/kbs")
async def list_kbs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_device: dict = Depends(get_current_device),
):
    user_id = uuid.UUID(DEFAULT_USER_ID)
    # 总数
    count_q = select(func.count(KnowledgeBase.id)).where(
        KnowledgeBase.user_id == user_id, KnowledgeBase.is_deleted == False
    )
    total = (await db.execute(count_q)).scalar() or 0

    # 列表（按 updated_at 倒序）
    q = (
        select(KnowledgeBase)
        .where(KnowledgeBase.user_id == user_id, KnowledgeBase.is_deleted == False)
        .order_by(desc(KnowledgeBase.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    kbs = result.scalars().all()

    items = []
    for kb in kbs:
        doc_count = (await db.execute(
            select(func.count(Document.id)).where(
                Document.kb_id == kb.id, Document.is_deleted == False
            )
        )).scalar() or 0

        chunk_count = (await db.execute(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.kb_id == kb.id)
        )).scalar() or 0

        last_doc = (await db.execute(
            select(Document.updated_at)
            .where(Document.kb_id == kb.id, Document.is_deleted == False)
            .order_by(desc(Document.updated_at))
            .limit(1)
        )).scalar()

        items.append({
            "id": kb.id,
            "user_id": kb.user_id,
            "name": kb.name,
            "description": kb.description,
            "default_llm": kb.default_llm,
            "embedding_model": kb.embedding_model,
            "rerank_model": kb.rerank_model,
            "chunk_strategy": kb.chunk_strategy,
            "visibility": kb.visibility,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat(),
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "last_updated_at": last_doc.isoformat() if last_doc else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/kbs/{kb_id}")
async def get_kb(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc_count = (await db.execute(
        select(func.count(Document.id)).where(
            Document.kb_id == kb.id, Document.is_deleted == False
        )
    )).scalar() or 0

    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.kb_id == kb.id)
    )).scalar() or 0

    last_doc = (await db.execute(
        select(Document.updated_at)
        .where(Document.kb_id == kb.id, Document.is_deleted == False)
        .order_by(desc(Document.updated_at))
        .limit(1)
    )).scalar()

    return {
        "id": kb.id, "user_id": kb.user_id, "name": kb.name,
        "description": kb.description, "default_llm": kb.default_llm,
        "embedding_model": kb.embedding_model, "rerank_model": kb.rerank_model,
        "chunk_strategy": kb.chunk_strategy, "visibility": kb.visibility,
        "created_at": kb.created_at.isoformat(), "updated_at": kb.updated_at.isoformat(),
        "document_count": doc_count, "chunk_count": chunk_count,
        "last_updated_at": last_doc.isoformat() if last_doc else None,
    }


@router.put("/kbs/{kb_id}")
async def update_kb(kb_id: uuid.UUID, req: KBUpdate, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(kb, key, value)
    await db.commit()
    await db.refresh(kb)
    return await get_kb(kb_id, db)


@router.delete("/kbs/{kb_id}")
async def delete_kb(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb or kb.is_deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    kb.is_deleted = True
    await db.commit()
    return {"message": "Knowledge base deleted"}


def _kb_to_response(kb: KnowledgeBase) -> dict:
    return {
        "id": kb.id, "user_id": kb.user_id, "name": kb.name,
        "description": kb.description, "default_llm": kb.default_llm,
        "embedding_model": kb.embedding_model, "rerank_model": kb.rerank_model,
        "chunk_strategy": kb.chunk_strategy, "visibility": kb.visibility,
        "created_at": kb.created_at, "updated_at": kb.updated_at,
        "document_count": 0, "chunk_count": 0, "last_updated_at": None,
    }


# ============================================================
# Phase 3B: Knowledge Base Management
# ============================================================

@router.get("/kbs/{kb_id}/stats")
async def kb_stats(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                   current_device: dict = Depends(get_current_device)):
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="KB not found")
    stmt = select(
        func.count(Document.id).label("total"),
        func.count(case((Document.status == "READY", 1))).label("ready"),
        func.count(case((Document.status == "UPLOADED", 1))).label("uploaded"),
        func.count(case((Document.status == "PARSING", 1))).label("parsing"),
        func.count(case((Document.status == "PARSED", 1))).label("parsed"),
        func.count(case((Document.status == "CHUNKING", 1))).label("chunking"),
        func.count(case((Document.status == "EMBEDDING", 1))).label("embedding"),
        func.count(case((Document.status == "INDEXING", 1))).label("indexing"),
        func.count(case((Document.status == "REINDEXING", 1))).label("reindexing"),
        func.count(case((Document.status == "FAILED", 1))).label("failed"),
    ).where(Document.kb_id == kb_id, Document.is_deleted == False)
    stats = (await db.execute(stmt)).one()
    active_docs = select(Document.id).where(Document.kb_id == kb_id, Document.is_deleted == False).scalar_subquery()
    chunk_count = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id.in_(active_docs))
    )).scalar() or 0
    last_failed = (await db.execute(
        select(IngestJob).where(IngestJob.kb_id == kb_id, IngestJob.status == "FAILED")
        .order_by(desc(IngestJob.updated_at)).limit(1)
    )).scalar_one_or_none()
    return {
        "kb_id": str(kb.id), "name": kb.name, "description": kb.description,
        "documents": {"total": stats.total, "ready": stats.ready, "uploaded": stats.uploaded,
                      "parsing": stats.parsing, "parsed": stats.parsed,
                      "chunking": stats.chunking, "embedding": stats.embedding,
                      "indexing": stats.indexing, "reindexing": stats.reindexing,
                      "failed": stats.failed,
                      "processing_total": (stats.parsing or 0)+(stats.parsed or 0)+(stats.chunking or 0)+(stats.embedding or 0)+(stats.indexing or 0)+(stats.reindexing or 0)},
        "index": {"active_version": 1, "total_chunks": chunk_count,
                  "total_vectors": chunk_count, "last_indexed_at": None},
        "last_error": _sanitize(last_failed.error_message[:200]) if last_failed and last_failed.error_message else None,
    }


@router.get("/kbs/{kb_id}/documents")
async def kb_documents(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       current_device: dict = Depends(get_current_device),
                       page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                       status: Optional[str] = None, search: Optional[str] = None,
                       file_type: Optional[str] = None, parse_status: Optional[str] = None):
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="KB not found")
    q = select(Document).where(Document.kb_id == kb_id, Document.is_deleted == False)
    if status:
        q = q.where(Document.status == status)
    if search: q = q.where(Document.original_filename.ilike(f"%{search}%"))
    if file_type: q = q.where(Document.file_type == file_type)
    if parse_status: q = q.where(Document.parse_status == parse_status)
    q = q.order_by(desc(Document.updated_at))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    items = []
    for doc in rows:
        job = (await db.execute(select(IngestJob).where(IngestJob.document_id == doc.id)
                                .order_by(desc(IngestJob.updated_at)).limit(1))).scalar_one_or_none()
        items.append({
            "document_id": str(doc.id), "kb_id": str(doc.kb_id),
            "filename": doc.filename, "original_filename": doc.original_filename,
            "file_type": doc.file_type, "mime_type": doc.mime_type, "file_size": doc.file_size,
            "uploaded_at": doc.created_at.isoformat(), "updated_at": doc.updated_at.isoformat(),
            "status": doc.status, "parse_status": doc.parse_status,
            "embed_status": doc.embed_status, "index_status": doc.index_status,
            "progress": job.progress if job else (1.0 if doc.status == "READY" else 0.0),
            "chunk_count": len(doc.chunks) if doc.chunks else 0,
            "vector_count": len(doc.chunks) if doc.chunks else 0,
            "error_message": _sanitize(doc.metadata_json.get("error", "") if doc.metadata_json else "") or "",
            "retry_count": job.retry_count if job else 0,
            "last_retry_at": doc.last_retry_at.isoformat() if doc.last_retry_at else None,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/kbs/{kb_id}/reindex/status")
async def kb_reindex_status(kb_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                            current_device: dict = Depends(get_current_device)):
    kb = (await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))).scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="KB not found")
    job = (await db.execute(
        select(IngestJob).where(IngestJob.kb_id == kb_id, IngestJob.job_type == "reindex")
        .order_by(desc(IngestJob.updated_at)).limit(1)
    )).scalar_one_or_none()
    total_docs = (await db.execute(
        select(func.count(Document.id)).where(Document.kb_id == kb_id, Document.is_deleted == False)
    )).scalar()
    return {
        "active_version": 1,
        "target_version": 2 if job and job.status == "RUNNING" else 1,
        "status": job.status if job else "idle",
        "total_documents": total_docs,
        "processed_documents": int(job.progress * total_docs) if job else 0,
        "failed_documents": 0, "current_document": None,
        "started_at": job.started_at.isoformat() if job and job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job and job.finished_at else None,
        "error_message": _sanitize(job.error_message[:200]) if job and job.error_message else None,
    }
