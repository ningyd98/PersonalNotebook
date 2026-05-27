"""
Personal-KB Backend — FastAPI 主入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.api import kb_routes, document_routes, job_routes, chat_routes, eval_routes, auth_routes

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {settings.PROJECT_NAME} v0.1.0")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 开发阶段允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Auth"])
app.include_router(kb_routes.router, prefix="/api", tags=["Knowledge Bases"])
app.include_router(document_routes.router, prefix="/api", tags=["Documents"])
app.include_router(job_routes.router, prefix="/api", tags=["Jobs"])
app.include_router(chat_routes.router, prefix="/api", tags=["Chat"])
app.include_router(eval_routes.router, prefix="/api/eval", tags=["Evaluation"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "0.1.0"}
