"""任务状态 API 路由 — 真实数据库查询"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import IngestJob

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "kb_id": str(job.kb_id),
        "document_id": str(job.document_id) if job.document_id else None,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
        "warnings_json": job.warnings_json,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "retry_count": job.retry_count,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/kbs/{kb_id}/jobs")
async def list_jobs(
    kb_id: uuid.UUID,
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    conditions = [IngestJob.kb_id == kb_id]
    if status:
        conditions.append(IngestJob.status == status)

    total_q = select(func.count(IngestJob.id)).where(*conditions)
    total = (await db.execute(total_q)).scalar() or 0

    q = (
        select(IngestJob)
        .where(*conditions)
        .order_by(desc(IngestJob.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    jobs = result.scalars().all()

    return {
        "kb_id": str(kb_id),
        "total": total,
        "page": page,
        "page_size": page_size,
        "jobs": [
            {
                "id": str(j.id), "kb_id": str(j.kb_id),
                "document_id": str(j.document_id) if j.document_id else None,
                "job_type": j.job_type, "status": j.status, "progress": j.progress,
                "error_message": j.error_message,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                "created_at": j.created_at.isoformat(), "updated_at": j.updated_at.isoformat(),
            }
            for j in jobs
        ],
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
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
        ingest_document.apply_async(
            args=[doc_id, str(job.kb_id), ""],
            task_id=str(job.id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch retry: {str(e)}")

    return {"message": "Job retry dispatched", "job_id": str(job.id)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Revoke Celery task
    try:
        from app.workers.celery_app import celery_app
        celery_app.control.revoke(job_id, terminate=True)
    except Exception:
        pass

    job.status = "CANCELLED"
    job.error_message = "Cancelled by user"
    await db.commit()

    return {"message": "Job cancelled", "job_id": str(job.id)}
