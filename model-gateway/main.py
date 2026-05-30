"""
Personal-KB Model Gateway — 统一模型服务网关
独立于业务后端，提供 LLM / Embedding / Rerank 的统一 API
"""

import os

from fastapi import FastAPI, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from schemas import ChatMessage, ChatRequest, EmbedRequest, RerankRequest, TokenizeRequest, TokenizeResponse

app = FastAPI(title="Personal-KB Model Gateway", version="0.1.0")


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

try:
    from providers.dashscope import DashScopeProvider
    register_provider("dashscope", DashScopeProvider())
except ImportError:
    logger.warning("DashScopeProvider not available")


def _find_provider_for_model(model: str):
    """根据模型名 + 环境变量选择 provider (dashscope > openai_compatible > vllm > ollama)"""
    import os
    preferred = os.getenv("MODEL_PROVIDER", "")
    if preferred and preferred in _providers:
        return _providers[preferred]

    # Qwen / gte models → dashscope
    if any(model.startswith(p) for p in ("qwen", "gte-rerank")):
        p = _providers.get("dashscope")
        if p:
            return p

    # DeepSeek / OpenAI models → openai_compatible
    if any(model.startswith(p) for p in ("gpt-", "o1", "o3", "text-embedding", "deepseek")):
        return _providers.get("openai_compatible")

    # 按优先级: dashscope > openai_compatible > vllm > ollama
    for name in ["dashscope", "openai_compatible", "vllm", "ollama"]:
        p = _providers.get(name)
        if p:
            return p
    return None


def _pick_provider(api_key: str = "", model: str = ""):
    """有 api_key → 按模型/环境匹配 provider; 无 api_key → ollama"""
    import os
    # DashScope key → dashscope provider
    if os.getenv("DASHSCOPE_API_KEY"):
        p = _providers.get("dashscope")
        if p:
            return p

    if api_key:
        p = _providers.get("openai_compatible")
        if p:
            from providers.openai_compatible import OpenAICompatibleProvider
            if hasattr(p, 'api_key'):
                p.api_key = api_key
            return p

    # 按优先级: dashscope > openai_compatible > vllm > ollama
    for name in ["dashscope", "openai_compatible", "vllm", "ollama"]:
        p = _providers.get(name)
        if p:
            return p
    return None


# ============================================================
# API Routes
# ============================================================
@app.post("/model/chat")
async def chat(request: ChatRequest):
    provider = _pick_provider(request.api_key)
    if request.api_key:
        set_runtime_api_key(request.api_key)
    # Check for openai_compatible missing key
    import os
    if provider and hasattr(provider, "__class__") and provider.__class__.__name__ == "OpenAICompatibleProvider":
        if not (os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or _api_key):
            raise HTTPException(status_code=503, detail="missing_api_key: no API key configured")
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
    """Phase 3D: enhanced status with api_key indicators + masked info."""
    import os
    provider_statuses = []
    for name, provider in _providers.items():
        entry = {"name": name, "status": "unknown", "models": [], "error": None}
        try:
            s = await provider.status()
            entry["status"] = s.get("status", "unknown")
            entry["models"] = s.get("models", [])[:10]
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)[:200]
        # Enrich with provider-specific info
        if name == "openai_compatible":
            entry["has_api_key"] = bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"))
            entry["base_url_masked"] = (os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1")
            if not entry["has_api_key"] and entry["status"] == "disconnected":
                entry["status"] = "missing_api_key"
        elif name == "ollama":
            entry["base_url"] = "http://localhost:11434"
        elif name == "dashscope":
            entry["has_api_key"] = bool(os.getenv("DASHSCOPE_API_KEY"))
            entry["base_url_masked"] = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            if not entry["has_api_key"] and entry["status"] == "disconnected":
                entry["status"] = "missing_api_key"
        provider_statuses.append(entry)
    return {"providers": provider_statuses}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/model/tokenize", response_model=TokenizeResponse)
async def tokenize(request: TokenizeRequest):
    """Tokenize text, return token count using tiktoken (cl100k_base) or fallback"""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(request.text))
    except Exception:
        # Fallback: rough estimate by character count / 4
        token_count = max(1, len(request.text) // 4)

    model_name = request.model or "cl100k_base"
    return TokenizeResponse(token_count=token_count, model=model_name)
