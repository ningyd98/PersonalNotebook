"""
System Runtime + Diagnostics API — Phase 3A-hotfix
"""

import os
import re
import subprocess
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.dependencies.auth import get_current_device

settings = get_settings()

router = APIRouter()

ENABLE_RUNTIME_API = os.getenv("ENABLE_RUNTIME_API", "true").lower() not in ("false", "0", "no")

SENSITIVE_KEYS = re.compile(
    r'(SECRET_KEY|PASSWORD|TOKEN|API_KEY|ACCESS_KEY|SECRET)\s*[=:]\s*\S+',
    re.IGNORECASE,
)


def _sanitize(text: str) -> str:
    return SENSITIVE_KEYS.sub(lambda m: m.group(1).upper() + '=***REDACTED***', text)


def _sanitize_dict(d: dict, depth: int = 0) -> dict:
    if depth > 5:
        return {"...": "max_depth"}
    result = {}
    for k, v in d.items():
        if k.lower() in ("api_key", "authorization", "token", "secret_key", "password"):
            result[k] = "***REDACTED***"
        elif isinstance(v, dict):
            result[k] = _sanitize_dict(v, depth + 1)
        elif isinstance(v, str):
            result[k] = _sanitize(v)
        else:
            result[k] = v
    return result


def _require_local(request: Request):
    if not ENABLE_RUNTIME_API:
        raise HTTPException(status_code=403, detail="Runtime API disabled (ENABLE_RUNTIME_API=false)")
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Runtime API only available from localhost")


# ============================================================
# Runtime endpoints (localhost only)
# ============================================================

@router.get("/system/status")
async def system_status(request: Request):
    _require_local(request)
    services = {}
    for name, check_cmd in [
        ("postgres", ["pg_isready", "-q"]),
        ("redis", ["redis-cli", "ping"]),
        ("qdrant", ["curl", "-sf", "http://localhost:6333/health"]),
        ("minio", ["curl", "-sf", "http://localhost:9000/minio/health/live"]),
    ]:
        try:
            subprocess.run(check_cmd, capture_output=True, timeout=5, check=True)
            services[name] = "running"
        except Exception:
            services[name] = "stopped"
    try:
        r = subprocess.run(["pgrep", "-f", "celery.*worker"], capture_output=True, text=True, timeout=3)
        services["celery_worker"] = "running" if r.stdout.strip() else "stopped"
    except Exception:
        services["celery_worker"] = "unknown"
    return {"success": True, "data": {"services": services, "docker_available": _check_docker()}}


@router.post("/system/runtime/start")
async def runtime_start(request: Request):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True, timeout=120, cwd=_find_infra_dir())
        return {"success": r.returncode == 0, "data": {"output": _sanitize(r.stdout[-2000:])}}
    except FileNotFoundError:
        return {"success": False, "error": {"code": "DOCKER_NOT_FOUND", "message": "Docker not installed"}}
    except Exception as e:
        return {"success": False, "error": {"code": "RUNTIME_START_FAILED", "message": str(e)}}


@router.post("/system/runtime/stop")
async def runtime_stop(request: Request):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "down"], capture_output=True, text=True, timeout=60, cwd=_find_infra_dir())
        return {"success": r.returncode == 0, "data": {"output": _sanitize(r.stdout[-2000:])}}
    except Exception as e:
        return {"success": False, "error": {"code": "RUNTIME_STOP_FAILED", "message": str(e)}}


@router.post("/system/runtime/restart")
async def runtime_restart(request: Request):
    await runtime_stop(request)
    return await runtime_start(request)


@router.get("/system/logs")
async def system_logs(request: Request, tail: int = 100):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "logs", f"--tail={min(tail, 500)}"], capture_output=True, text=True, timeout=30, cwd=_find_infra_dir())
        return {"success": True, "data": {"logs": _sanitize(r.stdout[-5000:])}}
    except Exception as e:
        return {"success": False, "error": {"code": "LOGS_FAILED", "message": str(e)}}


# ============================================================
# Phase 3A-hotfix: Diagnostics API (auth-gated, no api_key passthrough)
# ============================================================

@router.get("/system/diagnostics/basic")
async def diagnostics_basic():
    """Public basic status — no auth required, no internal topology exposed."""
    return {
        "status": "ok",
        "version": "0.2.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/system/diagnostics")
async def system_diagnostics(current_device: dict = Depends(get_current_device)):
    """Full diagnostics — requires pairing auth. No API key content exposed."""
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "models": {},
        "api_key_configured": False,
        "last_error": None,
    }

    # PostgreSQL
    try:
        from sqlalchemy import text
        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["services"]["postgres"] = {"status": "ok"}
    except Exception as e:
        result["services"]["postgres"] = {"status": "error", "error": _sanitize(str(e)[:200])}

    # Redis
    try:
        import redis
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_connect_timeout=2)
        r.ping(); r.close()
        result["services"]["redis"] = {"status": "ok"}
    except Exception as e:
        result["services"]["redis"] = {"status": "error", "error": _sanitize(str(e)[:200])}

    # Qdrant
    try:
        from app.services.qdrant_store import QdrantService
        QdrantService().ensure_collection()
        result["services"]["qdrant"] = {"status": "ok"}
    except Exception as e:
        result["services"]["qdrant"] = {"status": "error", "error": _sanitize(str(e)[:200])}

    # MinIO
    try:
        from app.services.storage import minio_storage
        minio_storage.client.list_buckets()
        result["services"]["minio"] = {"status": "ok"}
    except Exception as e:
        result["services"]["minio"] = {"status": "error", "error": _sanitize(str(e)[:200])}

    # Celery
    try:
        r = subprocess.run(["pgrep", "-f", "celery.*worker"], capture_output=True, text=True, timeout=3)
        result["services"]["celery"] = {"status": "ok" if r.stdout.strip() else "not_running"}
    except Exception:
        result["services"]["celery"] = {"status": "unknown"}

    # Model Gateway
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            gw_resp = await client.get(f"{settings.MODEL_GATEWAY_URL}/health")
            gw_resp.raise_for_status()
            result["services"]["model_gateway"] = {"status": "ok"}
        async with httpx.AsyncClient(timeout=5) as client:
            prov_resp = await client.get(f"{settings.MODEL_GATEWAY_URL}/model/status")
            prov_data = prov_resp.json()
            providers = prov_data.get("providers", [])
            for p in providers:
                name = p.get("name", "")
                result["models"][name] = {
                    "status": p.get("status", "unknown"),
                    "model_count": len(p.get("models", [])),
                    "models": p.get("models", [])[:5],
                }
    except Exception as e:
        result["services"]["model_gateway"] = {"status": "error", "error": _sanitize(str(e)[:200])}

    # API Key — only configured: bool, no key content
    api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    result["api_key_configured"] = bool(api_key and len(api_key) > 10)

    # Last error
    try:
        from sqlalchemy import desc
        from app.db.session import SessionLocal
        from app.models.models import IngestJob
        db_sync = SessionLocal()
        last_failed = db_sync.query(IngestJob).filter(
            IngestJob.status == "FAILED"
        ).order_by(desc(IngestJob.updated_at)).first()
        if last_failed:
            result["last_error"] = {
                "job_id": str(last_failed.id),
                "phase": getattr(last_failed, "phase", None),
                "error": _sanitize((last_failed.error_message or "")[:200]),
                "timestamp": last_failed.updated_at.isoformat() if last_failed.updated_at else None,
            }
        db_sync.close()
    except Exception:
        pass

    overall = all(
        v.get("status") == "ok"
        for v in result["services"].values()
        if isinstance(v, dict)
    )
    result["overall"] = "healthy" if overall else "degraded"
    return _sanitize_dict(result)


@router.post("/system/test-model")
async def test_model(model: str = None, current_device: dict = Depends(get_current_device)):
    """Test chat model — uses server-side API key only. No api_key passthrough."""
    llm = model or settings.DEFAULT_LLM
    try:
        body = {
            "model": llm, "messages": [{"role": "user", "content": "Reply with just OK."}],
            "temperature": 0, "max_tokens": 10,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.MODEL_GATEWAY_URL}/model/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "model": llm, "response": data.get("content", "")[:100]}
    except Exception as e:
        return {"success": False, "model": llm, "error": _sanitize(str(e)[:300])}


@router.post("/system/test-embedding")
async def test_embedding(model: str = None, current_device: dict = Depends(get_current_device)):
    """Test embedding model — uses server-side API key only."""
    emb = model or settings.DEFAULT_EMBEDDING
    try:
        body = {"model": emb, "texts": ["test embedding"]}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.MODEL_GATEWAY_URL}/model/embed", json=body)
            resp.raise_for_status()
            data = resp.json()
            vecs = data.get("vectors", [])
            return {"success": True, "model": emb, "dimensions": len(vecs[0]) if vecs else 0}
    except Exception as e:
        return {"success": False, "model": emb, "error": _sanitize(str(e)[:300])}


@router.post("/system/test-rag")
async def test_rag(current_device: dict = Depends(get_current_device)):
    """RAG test using internal services — no self-HTTP-call."""
    from sqlalchemy import select
    from app.db.session import engine as sync_engine
    from app.models.models import Document

    # Find a READY document
    from app.db.session import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    async for db in get_db():
        row = (await db.execute(
            select(Document.kb_id).where(Document.status == "READY", Document.is_deleted == False).limit(1)
        )).fetchone()
        if not row:
            return {"success": False, "error": "No READY document found. Upload a document first."}
        kb_id = str(row[0])
        break

    # Try internal chat via direct service calls
    try:
        from app.services.retrieval.retriever import RetrievalService
        from app.services.generation.generator import LLMGenerator
        from app.services.rerank.reranker import RerankService

        retriever = RetrievalService()
        generator = LLMGenerator()

        # Retrieve
        try:
            docs = await retriever.retrieve(kb_id=kb_id, query="test", top_k=4)
            has_docs = len(docs) > 0
        except Exception:
            has_docs = False

        return {
            "success": True,
            "kb_id": kb_id,
            "has_citations": has_docs,
            "citation_count": len(docs) if has_docs else 0,
            "answer_preview": "(Internal retrieval test — generation requires model gateway)",
        }
    except Exception as e:
        return {"success": False, "error": _sanitize(str(e)[:300])}


def _check_docker() -> bool:
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def _find_infra_dir() -> str:
    for root in [
        os.environ.get("PERSONAL_NOTEBOOK_ROOT", ""),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"),
        os.path.join(os.getcwd(), "infra"),
        os.getcwd(),
    ]:
        if root and os.path.exists(os.path.join(root, "docker-compose.yml")):
            return root
    return os.getcwd()
