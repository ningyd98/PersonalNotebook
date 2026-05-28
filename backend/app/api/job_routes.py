"""任务状态 API 路由 — 真实数据库查询 (Phase 2B)"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_device
from app.models.models import IngestJob

router = APIRouter()


def _job_payload(job) -> dict:
    return {
        "id": str(job.id), "kb_id": str(job.kb_id),
        "document_id": str(job.document_id) if job.document_id else None,
        "job_type": job.job_type, "status": job.status,
        "phase": getattr(job, "phase", None),
        "progress": job.progress, "error_message": job.error_message,
        "retry_count": job.retry_count,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


# ⚠️ /jobs/recent MUST come before /jobs/{job_id} to avoid UUID route capture
@router.get("/jobs/recent")
async def recent_jobs(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_device: dict = Depends(get_current_device),
):
    conditions = []
    if status:
        conditions.append(IngestJob.status == status)
    q = select(IngestJob).where(*conditions).order_by(desc(IngestJob.created_at)).limit(limit)
    result = await db.execute(q)
    jobs = result.scalars().all()
    return {"success": True, "data": {"jobs": [_job_payload(j) for j in jobs]}}


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                  current_device: dict = Depends(get_current_device)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_payload(job)


@router.get("/kbs/{kb_id}/jobs")
async def list_jobs(
    kb_id: uuid.UUID,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_device: dict = Depends(get_current_device),
):
    conditions = [IngestJob.kb_id == kb_id]
    if status:
        conditions.append(IngestJob.status == status)
    total = (await db.execute(select(func.count(IngestJob.id)).where(*conditions))).scalar() or 0
    q = (select(IngestJob).where(*conditions).order_by(desc(IngestJob.created_at))
         .offset((page - 1) * page_size).limit(page_size))
    result = await db.execute(q)
    jobs = result.scalars().all()
    return {"kb_id": str(kb_id), "total": total, "page": page, "page_size": page_size,
            "jobs": [_job_payload(j) for j in jobs]}


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                    current_device: dict = Depends(get_current_device)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "PENDING"
    job.retry_count = (job.retry_count or 0) + 1
    job.error_message = None
    await db.commit()
    try:
        from app.workers.celery_app import ingest_document
        doc_id = str(job.document_id) if job.document_id else ""
        ingest_document.apply_async(args=[doc_id, str(job.kb_id), ""], task_id=str(job.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch retry: {e}")
    return {"message": "Job retry dispatched", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                     current_device: dict = Depends(get_current_device)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job_id, terminate=True)
    except Exception:
        pass
    job.status = "CANCELLED"
    job.error_message = "Cancelled by user"
    await db.commit()
    return {"message": "Job cancelled", "job_id": str(job.id)}
