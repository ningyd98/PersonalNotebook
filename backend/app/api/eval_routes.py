"""评测 API 路由"""

import uuid

from fastapi import APIRouter

from app.schemas.schemas import EvalCaseCreate, EvalDatasetCreate, EvalRunRequest

router = APIRouter()


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
