"""PersonalNotebook Backend — FastAPI 主入口 (Phase 2B)"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.api import (kb_routes, document_routes, job_routes, chat_routes,
                     eval_routes, auth_routes, pair_routes, system_routes)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保所有解析器被注册
    import app.services.parsers  # noqa: F401
    logger.info(f"Starting {settings.PROJECT_NAME} v0.2.0")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(title=settings.PROJECT_NAME, version="0.2.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(auth_routes.router, prefix="/api/auth", tags=["Auth"])
app.include_router(kb_routes.router, prefix="/api", tags=["Knowledge Bases"])
app.include_router(document_routes.router, prefix="/api", tags=["Documents"])
app.include_router(job_routes.router, prefix="/api", tags=["Jobs"])
app.include_router(chat_routes.router, prefix="/api", tags=["Chat"])
app.include_router(eval_routes.router, prefix="/api/eval", tags=["Evaluation"])
app.include_router(pair_routes.router, prefix="/auth", tags=["Pairing"])
app.include_router(system_routes.router, prefix="/api", tags=["System"])


@app.get("/health")
async def health():
    result = {"status": "ok", "service": settings.PROJECT_NAME, "version": "0.2.0"}
    try:
        from sqlalchemy import text; from app.db.session import engine
        async with engine.connect() as conn: await conn.execute(text("SELECT 1"))
        result["postgres"] = "ok"
    except Exception as e: result["postgres"] = f"error: {e}"
    try:
        from app.services.qdrant_store import QdrantService
        QdrantService().ensure_collection()
        result["qdrant"] = "ok"
    except Exception as e: result["qdrant"] = f"error: {e}"
    try:
        from app.services.storage import minio_storage
        minio_storage.client.list_buckets()
        result["minio"] = "ok"
    except Exception as e: result["minio"] = f"error: {e}"
    try:
        import redis
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_connect_timeout=2)
        r.ping(); r.close()
        result["redis"] = "ok"
    except Exception as e: result["redis"] = f"error: {e}"
    if any(v != "ok" for k, v in result.items() if k in ("postgres", "qdrant", "minio", "redis")):
        result["status"] = "degraded"
    return result
