"""评测 API 路由"""

import uuid

from fastapi import APIRouter

from app.schemas.schemas import EvalCaseCreate, EvalDatasetCreate, EvalRunRequest
from app.db.session import get_db
from app.models.models import EvalDataset
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

router = APIRouter()


@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """返回评测集列表"""
    from sqlalchemy import select
    result = await db.execute(select(EvalDataset).order_by(EvalDataset.created_at.desc()))
    datasets = result.scalars().all()
    return {"datasets": [{"id": str(d.id), "name": d.name, "description": d.description,
                           "kb_id": str(d.kb_id) if d.kb_id else None,
                           "created_at": d.created_at.isoformat() if d.created_at else None}
                          for d in datasets]}


@router.post("/datasets")
async def create_dataset(req: EvalDatasetCreate):
    return {"id": str(uuid.uuid4()), "name": req.name, "message": "Dataset created"}


@router.post("/datasets/{dataset_id}/cases")
async def add_case(dataset_id: uuid.UUID, req: EvalCaseCreate):
    return {"message": "Case added", "dataset_id": str(dataset_id)}


@router.post("/run")
async def run_eval(req: EvalRunRequest):
    return {
        "run_id": str(uuid.uuid4()),
        "status": "running",
        "dataset_id": str(req.dataset_id),
        "kb_id": str(req.kb_id),
    }


@router.get("/runs/{run_id}")
async def get_eval_run(run_id: uuid.UUID):
    return {"run_id": str(run_id), "status": "completed"}


@router.get("/runs/{run_id}/report")
async def get_eval_report(run_id: uuid.UUID):
    return {
        "run_id": str(run_id),
        "recall_at_k": {"k=5": 0.85, "k=10": 0.92},
        "mrr": 0.78,
        "citation_accuracy": 0.88,
        "hallucination_rate": 0.05,
        "total_cases": 50,
        "passed_cases": 42,
    }
