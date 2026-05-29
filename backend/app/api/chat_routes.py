"""问答 API — 持久化 conversation/messages + Citation Verification"""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies.auth import get_current_device
from app.models.models import Conversation, Feedback, Message, Document
from app.schemas.schemas import (
    ChatRequest, ChatResponse, Citation, FeedbackRequest,
    FeedbackResponse, RetrievalTrace,
)
from app.services.retrieval.retriever import RetrievalService
from app.services.rerank.reranker import RerankService, EvidencePackBuilder
from app.services.generation.generator import GenerationService

settings = get_settings()
router = APIRouter()

retrieval_service = RetrievalService()
rerank_service = RerankService()
generation_service = GenerationService()

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"

# Rerank score threshold for refusal
LOW_CONFIDENCE_THRESHOLD = 0.15
NO_EVIDENCE_ANSWER = "当前知识库未找到可靠依据。"


def _parse_uuid(value: object) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None



def _evaluate_refusal(evidence_pack, answer, citations) -> dict:
    """Evaluate if the answer should be refused based on evidence quality."""
    if not evidence_pack or len(evidence_pack) == 0:
        return {"should_refuse": True, "refusal_score": 1.0, "reason": "no_evidence"}
    if not citations or len(citations) == 0:
        return {"should_refuse": True, "refusal_score": 0.9, "reason": "no_verified_citations"}
    scores = [c.get("score", 0) for c in citations if isinstance(c, dict)]
    if not scores:
        return {"should_refuse": False, "refusal_score": 0.0, "reason": None}
    best = max(scores)
    if best < 0.3:
        return {"should_refuse": True, "refusal_score": 0.7, "reason": "low_confidence_all_scores_below_0.3"}
    if not answer or len(answer.strip()) < 5:
        return {"should_refuse": True, "refusal_score": 0.8, "reason": "empty_answer"}
    return {"should_refuse": False, "refusal_score": max(0.0, best - 0.3), "reason": None}
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    start_time = time.time()
    kb_id = str(req.kb_id)
    user_id = uuid.UUID(DEFAULT_USER_ID)

    # ================================================================
    # 0. Get or create conversation
    # ================================================================
    conv = None
    if req.conversation_id:
        conv = await db.get(Conversation, req.conversation_id)

    if not conv:
        conv = Conversation(
            user_id=user_id,
            kb_id=req.kb_id,
            title=req.question[:100],
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # ================================================================
    # 1. Retrieval
    # ================================================================
    retrieval_result = await retrieval_service.retrieve(
        query=req.question,
        kb_id=kb_id,
        top_k=settings.VECTOR_TOP_K,
        retrieval_mode=req.retrieval_mode,
    )
    hits = retrieval_result["hits"]

    # 2. Rerank
    if req.use_rerank and hits:
        hits = await rerank_service.rerank(
            query=req.question,
            documents=hits,
            top_k=req.top_k,
        )

    # 3. Evidence Pack
    evidence_pack = EvidencePackBuilder.build(hits, req.top_k)

    # ================================================================
    # Refusal check: no evidence or best score below threshold
    # ================================================================
    best_score = max((e.get("score", 0) for e in evidence_pack), default=0.0)

    if not evidence_pack or best_score < LOW_CONFIDENCE_THRESHOLD:
        latency_ms = (time.time() - start_time) * 1000

        # Save refusal message
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=NO_EVIDENCE_ANSWER,
            citations_json=[],
            retrieval_trace_json={
                "query": req.question,
                "query_type": retrieval_result["query_type"],
                "retrievers": retrieval_result["stats"],
                "rerank_top_k": req.top_k,
                "selected_evidence": [],
                "latency_ms": latency_ms,
            },
            model_name=None,
            latency_ms=latency_ms,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        suggested_actions = ["上传更多相关文档到该知识库", "尝试换一种更具体的问法", "检查知识库是否已完成索引"]

        return ChatResponse(
            answer=NO_EVIDENCE_ANSWER,
            citations=[],
            trace=RetrievalTrace(
                query=req.question,
                query_type=retrieval_result["query_type"],
                retrievers=retrieval_result["stats"],
                rerank_top_k=req.top_k,
                selected_evidence=[],
                latency_ms=latency_ms,
            ) if req.debug else None,
            conversation_id=conv.id,
            message_id=assistant_msg.id,
            model=settings.DEFAULT_LLM,
            latency_ms=latency_ms,
            confidence=0.0,
            refusal=True,
            refusal_reason="no_evidence_or_low_confidence",
            suggested_actions=suggested_actions,
            should_refuse=True,
            citation_coverage=0.0,
        )

    # ================================================================
    # 4. LLM Generation
    # ================================================================
    gen_result = await generation_service.generate(
        question=req.question, evidence_pack=evidence_pack,
        strict_citation=req.strict_citation,
    )

    latency_ms = (time.time() - start_time) * 1000
    model_name = gen_result.get("model", settings.DEFAULT_LLM)

    # ================================================================
    # 5. Citation Verification
    # ================================================================
    verified_citations = _verify_citations(
        gen_result.get("citations", []), evidence_pack
    )

    # Build Citation objects with enriched info + validation
    citations = []
    deleted_doc_ids = set()
    try:
        from sqlalchemy import select as sa_select
        deleted_rows = (await db.execute(
            sa_select(Document.id).where(Document.is_deleted == True)
        )).scalars().all()
        deleted_doc_ids = set(str(r) for r in deleted_rows)
    except Exception:
        pass

    for i, c in enumerate(verified_citations):
        doc_uuid = _parse_uuid(c.get("document_id"))
        if doc_uuid is None:
            continue
        # Filter deleted documents
        if str(doc_uuid) in deleted_doc_ids:
            continue
        # Filter verified citations only
        if not c.get("verified", True):
            continue

        doc = (await db.execute(
            sa_select(Document).where(Document.id == doc_uuid)
        )).scalar_one_or_none()

        citations.append(
            Citation(
                citation_id=f"cit_{len(citations):03d}",
                evidence_id=c.get("evidence_id", f"ev_{len(citations):03d}"),
                source_type=c.get("source_type", "text"),
                document_id=doc_uuid,
                document_name=doc.original_filename if doc else c.get("filename", ""),
                chunk_id=c.get("chunk_id"),
                chunk_index=c.get("chunk_index", c.get("index")),
                version_id=c.get("version_id"),
                filename=c.get("filename", ""),
                page_number=c.get("page_number"),
                section_path=c.get("section_path"),
                score=c.get("score", 0.0),
                rerank_score=c.get("rerank_score"),
                content_preview=c.get("content_preview", (c.get("content", "") or "")[:200]),
                evidence_text=c.get("content", "")[:500] if c.get("content") else "",
            )
        )

    # Build refusal/confidence (evaluated in return block below)

    # ================================================================
    # 6. Save assistant message
    # ================================================================
    trace_data = None
    if req.debug:
        trace_data = {
            "query": req.question,
            "query_type": retrieval_result["query_type"],
            "rewrite_query": None,
            "retrievers": retrieval_result["stats"],
            "rerank_top_k": req.top_k,
            "selected_evidence": [f"ev_{i:03d}" for i in range(len(evidence_pack))],
            "latency_ms": latency_ms,
        }

    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=gen_result["answer"],
        citations_json=[c.model_dump() for c in citations] if citations else None,
        retrieval_trace_json=trace_data,
        model_name=model_name,
        latency_ms=latency_ms,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    refusal_result = _evaluate_refusal(evidence_pack, gen_result.get("answer",""), citations)
    confidence = 1.0 - refusal_result.get("refusal_score", 0.0)
    refusal = refusal_result.get("should_refuse", False)
    refusal_reason = refusal_result.get("reason") if refusal else None
    suggested_actions = ["上传更多相关文档到该知识库", "尝试换一种更具体的问法", "检查知识库是否已完成索引"] if refusal else []

    return ChatResponse(
        answer=gen_result["answer"],
        citations=citations,
        trace=RetrievalTrace(**trace_data) if req.debug and trace_data else None,
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        model=model_name,
        latency_ms=latency_ms,
        confidence=confidence,
        refusal=refusal,
        refusal_reason=refusal_reason,
        suggested_actions=suggested_actions,
        should_refuse=refusal,
        citation_coverage=(len(citations) / len(evidence_pack)) if evidence_pack else 0.0,
    )


def _verify_citations(generated_citations: list[dict], evidence_pack: list[dict]) -> list[dict]:
    """
    Citation Verification:
    - Each citation must map to a valid evidence_id in the evidence_pack
    - Remove fabricated citations
    - If no valid citations but evidence exists, build citations from evidence
    """
    if not generated_citations:
        # Build citations from evidence if LLM didn't provide any
        return [
            {
                "evidence_id": ev["evidence_id"],
                "source_type": ev.get("source_type", "text"),
                "document_id": ev.get("document_id", ""),
                "chunk_id": ev.get("chunk_id", ""),
                "version_id": ev.get("version_id", 1),
                "filename": ev.get("filename", ""),
                "page_number": ev.get("page_number"),
                "slide_number": ev.get("slide_number"),
                "section_path": ev.get("section_path"),
                "score": ev.get("score", 0.0),
                "content_preview": ev.get("content", "")[:200],
            }
            for ev in evidence_pack[:5]
        ]

    # Build evidence_id set for validation
    valid_evidence_ids = {ev["evidence_id"] for ev in evidence_pack}
    ev_by_id = {ev["evidence_id"]: ev for ev in evidence_pack}

    verified = []
    for cit in generated_citations:
        eid = cit.get("evidence_id", "")
        if eid in valid_evidence_ids:
            ev = ev_by_id[eid]
            verified.append({
                **cit,
                "document_id": ev.get("document_id", cit.get("document_id", "")),
                "chunk_id": ev.get("chunk_id", cit.get("chunk_id", "")),
                "version_id": ev.get("version_id", cit.get("version_id", 1)),
                "filename": ev.get("filename", cit.get("filename", "")),
                "score": ev.get("score", cit.get("score", 0.0)),
                "content_preview": ev.get("content", cit.get("content_preview", ""))[:200],
            })

    return verified


# ================================================================
# Conversations
# ================================================================
@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    user_id = uuid.UUID(DEFAULT_USER_ID)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(50)
    )
    convs = result.scalars().all()
    return {
        "conversations": [
            {
                "id": str(c.id), "user_id": str(c.user_id),
                "kb_id": str(c.kb_id) if c.kb_id else None,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ],
        "total": len(convs),
    }


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    conv = await db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": str(conv.id),
        "kb_id": str(conv.kb_id) if conv.kb_id else None,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": [
            {
                "id": str(m.id), "role": m.role, "content": m.content,
                "citations_json": m.citations_json,
                "retrieval_trace_json": m.retrieval_trace_json,
                "model_name": m.model_name,
                "latency_ms": m.latency_ms,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


# ================================================================
# Feedback
# ================================================================
@router.post("/messages/{msg_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(msg_id: uuid.UUID, req: FeedbackRequest, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    msg = await db.get(Message, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # Check existing feedback
    from sqlalchemy import select as sa_select
    existing = (await db.execute(
        sa_select(Feedback).where(Feedback.message_id == msg_id)
    )).scalar()

    if existing:
        existing.rating = req.rating
        existing.comment = req.comment
        existing.error_type = req.error_type
        fb = existing
    else:
        fb = Feedback(
            message_id=msg_id,
            rating=req.rating,
            comment=req.comment,
            error_type=req.error_type,
        )
        db.add(fb)

    await db.commit()
    await db.refresh(fb)

    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        rating=fb.rating,
        comment=fb.comment,
        error_type=fb.error_type,
        created_at=fb.created_at,
    )


# ================================================================
# Debug Chat API — Phase 1.6
# ================================================================
@router.post("/chat/debug")
async def chat_debug(req: ChatRequest, db: AsyncSession = Depends(get_db), current_device: dict = Depends(get_current_device)):
    """返回完整 RAG trace 用于排查召回/排序/生成质量"""
    start_time = time.time()
    kb_id = str(req.kb_id)

    retrieval_result = await retrieval_service.retrieve(
        query=req.question, kb_id=kb_id,
        top_k=settings.VECTOR_TOP_K, retrieval_mode=req.retrieval_mode,
    )
    hits = retrieval_result["hits"]

    reranked_hits = hits
    if req.use_rerank and hits:
        reranked_hits = await rerank_service.rerank(query=req.question, documents=hits, top_k=req.top_k)

    from app.services.claims.evidence_pack import (
        EnhancedEvidencePackBuilder, RefusalEngine, ClaimVerifier,
    )
    evidence_pack = EnhancedEvidencePackBuilder.build(
        query=req.question, retrieval_hits=hits,
        reranked_hits=reranked_hits, query_type=retrieval_result["query_type"],
    )

    gen_result = await generation_service.generate(
        question=req.question, evidence_pack=[e.to_dict() for e in evidence_pack.evidences],
        strict_citation=req.strict_citation,
    )
    answer = gen_result.get("answer", "")
    latency_ms = (time.time() - start_time) * 1000

    coverage_ratio, supported, unsupported = ClaimVerifier.compute_coverage(
        answer, evidence_pack.evidences
    )
    should_refuse, refusal_reason = RefusalEngine.evaluate(
        evidence_pack, citation_coverage=coverage_ratio
    )

    return {
        "query": req.question,
        "query_type": retrieval_result["query_type"],
        "rewritten_queries": [],
        "dense_results": [
            {"id": h.get("id"), "score": h.get("score"), "content": (h.get("content", ""))[:200]}
            for h in hits[:10]
        ],
        "sparse_results": [],
        "merged_results_count": len(hits),
        "reranked_results": [
            {"id": h.get("id"), "rerank_score": h.get("rerank_score", 0.0),
             "content": (h.get("content", ""))[:200]}
            for h in reranked_hits[:8]
        ],
        "evidence_pack": evidence_pack.to_dict(),
        "answer": answer,
        "citations": gen_result.get("citations", []),
        "refusal_reason": refusal_reason if should_refuse else None,
        "should_refuse": should_refuse,
        "citation_coverage": coverage_ratio,
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "latency_ms": latency_ms,
        "model": gen_result.get("model", settings.DEFAULT_LLM),
    }
