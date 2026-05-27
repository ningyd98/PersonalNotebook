"""OpenAI-compatible Provider — 支持任何 OpenAI API 兼容服务"""

import os
from typing import Optional

import httpx
from loguru import logger

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class OpenAICompatibleProvider:
    """OpenAI API 兼容适配器"""

    def __init__(self):
        self.base_url = OPENAI_BASE_URL.rstrip("/")
        self.api_key = OPENAI_API_KEY

    def supports_model(self, model: str) -> bool:
        return True

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
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
            logger.error(f"OpenAI chat failed: {e}")
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
            logger.error(f"OpenAI embed failed: {e}")
            raise

    async def rerank(self, model: str, query: str, documents: list[str]) -> dict:
        """
        OpenAI API 默认不支持 rerank。
        尝试调用 /rerank endpoint（部分兼容服务支持），
        否则 fallback：用 chat API 打分。
        """
        # 尝试原生 rerank endpoint
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/rerank",
                    headers=self._headers,
                    json={"model": model, "query": query, "documents": documents},
                )
                resp.raise_for_status()
                data = resp.json()
                return {"results": data.get("results", [])}
        except Exception:
            pass

        # fallback: 基于 chat 打分
        results = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            for i, doc in enumerate(documents):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers,
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "Rate the relevance of the document to the query. Output only a number between 0 and 1."},
                                {"role": "user", "content": f"Query: {query}\nDocument: {doc[:500]}"},
                            ],
                            "temperature": 0,
                            "max_tokens": 10,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw = data.get("choices", [{}])[0].get("message", {}).get("content", "0")
                    try:
                        score = float(raw.strip())
                    except ValueError:
                        score = 0.0
                    results.append({"index": i, "score": min(max(score, 0.0), 1.0)})
                except Exception:
                    results.append({"index": i, "score": 0.0})

        results.sort(key=lambda r: r["score"], reverse=True)
        return {"results": results}

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
