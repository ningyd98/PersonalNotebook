"""知识库 API 路由 — 真实数据库查询"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Document, DocumentChunk, KnowledgeBase
from app.schemas.schemas import KBCreate, KBResponse, KBUpdate, PaginatedResponse
from app.dependencies.auth import get_current_device

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
