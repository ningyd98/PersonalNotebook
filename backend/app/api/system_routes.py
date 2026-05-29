"""
System Runtime API — Phase 2B 加固
桌面端 Core 服务生命周期管理 (仅本机可用)
"""

import os
import re
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings

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
    """Recursively remove API key values from dict. 'error' fields truncated."""
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


def _sanitize(text: str) -> str:
    return SENSITIVE_KEYS.sub(lambda m: m.group(1).upper() + '=***REDACTED***', text)


@router.get("/system/status")
async def system_status(request: Request):
    """返回 Core 服务运行状态 (仅 localhost)"""
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

    docker_ok = _check_docker()
    return {"success": True, "data": {"services": services, "docker_available": docker_ok}}


@router.post("/system/runtime/start")
async def runtime_start(request: Request):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True, timeout=120, cwd=_find_infra_dir())
        return {"success": r.returncode == 0, "data": {"output": _sanitize(r.stdout[-2000:])}}
    except FileNotFoundError:
        return {"success": False, "error": {"code": "DOCKER_NOT_FOUND", "message": "Docker not installed or not in PATH"}}
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


# ============================================================
# Phase 3A: Diagnostics API
# ============================================================

@router.get("/system/diagnostics")
async def system_diagnostics():
    """综合诊断：Core/DB/Redis/Qdrant/MinIO/ModelGateway/API Key/最后错误"""
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
        result["services"]["postgres"] = {"status": "error", "error": str(e)[:200]}

    # Redis
    try:
        import redis
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_connect_timeout=2)
        r.ping(); r.close()
        result["services"]["redis"] = {"status": "ok"}
    except Exception as e:
        result["services"]["redis"] = {"status": "error", "error": str(e)[:200]}

    # Qdrant
    try:
        from app.services.qdrant_store import QdrantService
        QdrantService().ensure_collection()
        result["services"]["qdrant"] = {"status": "ok"}
    except Exception as e:
        result["services"]["qdrant"] = {"status": "error", "error": str(e)[:200]}

    # MinIO
    try:
        from app.services.storage import minio_storage
        minio_storage.client.list_buckets()
        result["services"]["minio"] = {"status": "ok"}
    except Exception as e:
        result["services"]["minio"] = {"status": "error", "error": str(e)[:200]}

    # Celery worker
    try:
        r = subprocess.run(["pgrep", "-f", "celery.*worker"], capture_output=True, text=True, timeout=3)
        result["services"]["celery"] = {"status": "ok" if r.stdout.strip() else "not_running"}
    except Exception:
        result["services"]["celery"] = {"status": "unknown"}

    # Model Gateway
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            gw_resp = await client.get(f"{settings.MODEL_GATEWAY_URL}/health")
            gw_resp.raise_for_status()
            result["services"]["model_gateway"] = {"status": "ok"}
        # Provider status
        async with httpx.AsyncClient(timeout=5) as client:
            prov_resp = await client.get(f"{settings.MODEL_GATEWAY_URL}/model/status")
            prov_data = prov_resp.json()
            providers = prov_data.get("providers", [])
            for p in providers:
                name = p.get("name", "")
                s = p.get("status", "unknown")
                models = p.get("models", [])
                result["models"][name] = {
                    "status": s,
                    "model_count": len(models),
                    "models": models[:5],
                }
    except Exception as e:
        result["services"]["model_gateway"] = {"status": "error", "error": str(e)[:200]}

    # API Key check (no key content)
    api_key = os.getenv("DEEPSEEK_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    result["api_key_configured"] = bool(api_key and len(api_key) > 10)

    # Last error from Celery
    try:
        from sqlalchemy import desc, select
        from app.db.session import SessionLocal
        db_sync = SessionLocal()
        from app.models.models import IngestJob
        last_failed = db_sync.query(IngestJob).filter(
            IngestJob.status == "FAILED"
        ).order_by(desc(IngestJob.updated_at)).first()
        if last_failed:
            result["last_error"] = {
                "job_id": str(last_failed.id),
                "phase": getattr(last_failed, "phase", None),
                "error": (last_failed.error_message or "")[:200],
                "timestamp": last_failed.updated_at.isoformat(),
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

    # Sanitize: no secrets
    return _sanitize_dict(result)


@router.post("/system/test-model")
async def test_model(model: str = None, api_key: str = ""):
    """测试 Chat 模型连通性 — POST model-gateway 简单消息"""
    llm = model or settings.DEFAULT_LLM
    import httpx
    try:
        body = {
            "model": llm, "messages": [{"role": "user", "content": "Hello, reply with just OK."}],
            "temperature": 0, "max_tokens": 10,
        }
        if api_key:
            body["api_key"] = api_key
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.MODEL_GATEWAY_URL}/model/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "model": llm, "response": data.get("content", "")[:100]}
    except Exception as e:
        return {"success": False, "model": llm, "error": str(e)[:300]}


@router.post("/system/test-embedding")
async def test_embedding(model: str = None, api_key: str = ""):
    """测试 Embedding 模型连通性"""
    emb = model or settings.DEFAULT_EMBEDDING
    import httpx
    try:
        body = {"model": emb, "texts": ["test embedding"]}
        if api_key:
            body["api_key"] = api_key
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.MODEL_GATEWAY_URL}/model/embed", json=body)
            resp.raise_for_status()
            data = resp.json()
            vecs = data.get("vectors", [])
            return {"success": True, "model": emb, "dimensions": len(vecs[0]) if vecs else 0}
    except Exception as e:
        return {"success": False, "model": emb, "error": str(e)[:300]}


@router.post("/system/test-rag")
async def test_rag():
    """快速 RAG 测试 — 需要至少一个 READY 文档的 KB"""
    from sqlalchemy import select, func
    from app.db.session import engine
    from app.models.models import Document, KnowledgeBase
    async with engine.connect() as conn:
        doc_result = await conn.execute(
            select(Document.kb_id).where(Document.status == "READY", Document.is_deleted == False).limit(1)
        )
        row = doc_result.fetchone()
        if not row:
            return {"success": False, "error": "No READY document found. Upload a document first."}
        kb_id = str(row[0])

    # Simple RAG test via chat
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"http://localhost:8000/api/chat",
                json={"kb_id": kb_id, "question": "Summarize in one sentence", "top_k": 4, "strict_citation": True},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "kb_id": kb_id,
                "answer": data.get("answer", "")[:200],
                "has_citations": len(data.get("citations", [])) > 0,
                "citation_count": len(data.get("citations", [])),
            }
    except Exception as e:
        return {"success": False, "error": str(e)[:300]}
