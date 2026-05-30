"""DashScope Provider — 通过阿里云 DashScope API 调用模型（通义千问）"""

import os
from typing import Optional

import httpx
from loguru import logger

DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")


class DashScopeProvider:
    """DashScope (阿里云通义千问) 模型服务适配器

    Chat/Embedding 走 OpenAI 兼容模式;
    Rerank 走 DashScope 专用 rerank API.
    """

    def __init__(self):
        self.base_url = DASHSCOPE_BASE_URL.rstrip("/")
        self.api_key = DASHSCOPE_API_KEY

    def supports_model(self, model: str) -> bool:
        """DashScope 支持通义千问系列模型及 DashScope 兼容模型"""
        dashscope_prefixes = ("qwen", "gte", "text-embedding")
        return any(model.startswith(p) for p in dashscope_prefixes) or True

    @property
    def _headers(self) -> dict:
        key = self.api_key
        if not key:
            key = os.getenv("DASHSCOPE_API_KEY", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                return {
                    "content": choice.get("message", {}).get("content", ""),
                    "model": model,
                    "usage": data.get("usage", {}),
                }
        except Exception as e:
            logger.error(f"DashScope chat failed: {e}")
            raise

    async def embed(self, model: str, texts: list[str]) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self._headers,
                    json={"model": model, "input": texts},
                )
                resp.raise_for_status()
                data = resp.json()
                vectors = [d["embedding"] for d in data.get("data", [])]
                return {"vectors": vectors, "model": model}
        except Exception as e:
            logger.error(f"DashScope embed failed: {e}")
            raise

    async def rerank(self, model: str, query: str, documents: list[str]) -> dict:
        """调用 DashScope 专用 rerank API

        POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-rerank/rerank
        请求: {"model": "gte-rerank", "input": {"query": "...", "documents": [...]}}
        响应: {"output": {"results": [{"index": 0, "relevance_score": 0.9}]}}
        """
        rerank_url = os.getenv(
            "DASHSCOPE_RERANK_URL",
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-rerank/rerank",
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    rerank_url,
                    headers=self._headers,
                    json={
                        "model": model or "gte-rerank",
                        "input": {
                            "query": query,
                            "documents": documents,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                # DashScope rerank 响应格式: output.results[].index / relevance_score
                raw_results = data.get("output", {}).get("results", [])
                results = []
                for r in raw_results:
                    results.append({
                        "index": r.get("index", 0),
                        "relevance_score": r.get("relevance_score", 0.0),
                    })
                # 按相关性降序排列
                results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
                return {"results": results}
        except Exception as e:
            logger.error(f"DashScope rerank failed: {e}")
            raise

    async def status(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                return {"status": "ok", "models": models}
        except Exception as e:
            return {"status": "disconnected", "error": str(e), "models": []}
