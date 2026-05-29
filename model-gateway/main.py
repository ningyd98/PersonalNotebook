"""
Personal-KB Model Gateway — 统一模型服务网关
独立于业务后端，提供 LLM / Embedding / Rerank 的统一 API
"""

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

app = FastAPI(title="Personal-KB Model Gateway", version="0.1.0")


# ============================================================
# Request Schemas
# ============================================================
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "deepseek-chat"
    messages: list[ChatMessage]
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    api_key: str = ""


class EmbedRequest(BaseModel):
    model: str = "text-embedding-3-small"
    texts: list[str]
    api_key: str = ""


class RerankRequest(BaseModel):
    model: str = "deepseek-chat"
    query: str
    documents: list[str]
    api_key: str = ""


_providers: dict[str, object] = {}
_api_key: str = ""  # runtime override from requests


def set_runtime_api_key(key: str):
    global _api_key
    _api_key = key


def register_provider(name: str, provider):
    _providers[name] = provider
    logger.info(f"Registered provider: {name}")


# 尝试导入各 provider
try:
    from providers.ollama import OllamaProvider
    register_provider("ollama", OllamaProvider())
except ImportError:
    logger.warning("OllamaProvider not available")

try:
    from providers.openai_compatible import OpenAICompatibleProvider
    register_provider("openai_compatible", OpenAICompatibleProvider())
except ImportError:
    logger.warning("OpenAICompatibleProvider not available")

try:
    from providers.vllm import VLLMProvider
    register_provider("vllm", VLLMProvider())
except ImportError:
    logger.warning("VLLMProvider not available")


def _find_provider_for_model(model: str):
    """根据模型名 + 环境变量选择 provider (vllm > openai_compatible > ollama)"""
    import os
    preferred = os.getenv("MODEL_PROVIDER", "")
    if preferred and preferred in _providers:
        return _providers[preferred]

    # DeepSeek / OpenAI models → openai_compatible
    if any(model.startswith(p) for p in ("gpt-", "o1", "o3", "text-embedding", "deepseek")):
        return _providers.get("openai_compatible")

    # 按优先级: vllm > openai_compatible > ollama
    for name in ["vllm", "openai_compatible", "ollama"]:
        p = _providers.get(name)
        if p:
            return p
    return None


def _pick_provider(api_key: str = "", model: str = ""):
    """有 api_key → openai_compatible (auto-detect OpenAI/DeepSeek); 无 api_key → ollama"""
    if api_key:
        p = _providers.get("openai_compatible")
        if p:
            # Auto-detect: DeepSeek keys start with 'sk-', OpenAI keys start with 'sk-proj-' or 'sk-'
            from providers.openai_compatible import OpenAICompatibleProvider
            if hasattr(p, 'api_key'):
                p.api_key = api_key
            return p
    for name in ["ollama", "vllm", "openai_compatible"]:
        p = _providers.get(name)
        if p: return p
    return None


# ============================================================
# API Routes
# ============================================================
@app.post("/model/chat")
async def chat(request: ChatRequest):
    provider = _pick_provider(request.api_key)
    if request.api_key:
        set_runtime_api_key(request.api_key)
    if provider is None:
        raise HTTPException(status_code=503, detail="No model provider available")
    result = await provider.chat(
        model=request.model, messages=[m.model_dump() for m in request.messages],
        temperature=request.temperature, max_tokens=request.max_tokens,
    )
    return result


@app.post("/model/embed")
async def embed(request: EmbedRequest):
    provider = _pick_provider(request.api_key)
    if request.api_key:
        set_runtime_api_key(request.api_key)
    if provider is None:
        raise HTTPException(status_code=503, detail="No model provider available")
    result = await provider.embed(model=request.model, texts=request.texts)
    return result


@app.post("/model/rerank")
async def rerank(request: RerankRequest):
    provider = _pick_provider(request.api_key)
    if request.api_key:
        set_runtime_api_key(request.api_key)
    if provider is None:
        raise HTTPException(status_code=503, detail="No model provider available")
    result = await provider.rerank(model=request.model, query=request.query, documents=request.documents)
    return result


@app.get("/model/status")
async def status():
    provider_statuses = []
    for name, provider in _providers.items():
        try:
            s = await provider.status()
            provider_statuses.append({"name": name, **s})
        except Exception as e:
            provider_statuses.append({"name": name, "status": "error", "error": str(e)})

    return {"providers": provider_statuses}


@app.get("/health")
async def health():
    return {"status": "ok"}
