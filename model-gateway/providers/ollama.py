"""Ollama Provider — 通过 Ollama API 调用模型"""

import os
from typing import Optional

import httpx
from loguru import logger

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class OllamaProvider:
    """Ollama 模型服务适配器"""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL.rstrip("/")

    def supports_model(self, model: str) -> bool:
        """简单判断：Ollama 支持任何模型名"""
        return True

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
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "content": data.get("message", {}).get("content", ""),
                    "model": model,
                    "usage": {
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                }
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise

    async def embed(self, model: str, texts: list[str]) -> dict:
        vectors = []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for text in texts:
                    resp = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    vectors.append(data.get("embedding", []))
            return {"vectors": vectors, "model": model}
        except Exception as e:
            logger.error(f"Ollama embed failed: {e}")
            raise

    async def rerank(self, model: str, query: str, documents: list[str]) -> dict:
        """
        Ollama 原生不支持 rerank API。
        这里用 chat API 模拟：让 LLM 对每个文档打分。
        实际部署建议使用专用 reranker。
        """
        results = []
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, doc in enumerate(documents):
                    prompt = (
                        f"Query: {query}\n"
                        f"Document: {doc[:500]}\n"
                        f'Rate relevance 0-1 (output number only):'
                    )
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0, "num_predict": 10},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw = data.get("response", "0").strip()
                    try:
                        score = float(raw)
                    except ValueError:
                        score = 0.0
                    results.append({"index": i, "score": min(max(score, 0.0), 1.0)})

            # 按分数降序排列
            results.sort(key=lambda r: r["score"], reverse=True)
            return {"results": results}
        except Exception as e:
            logger.error(f"Ollama rerank failed: {e}")
            # Fallback: 保守分数，避免绕过低置信拒答
            return {
                "results": [
                    {"index": i, "score": max(0.50 - i * 0.05, 0.05)}
                    for i in range(len(documents))
                ]
            }

    async def status(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"status": "ok", "models": models}
        except Exception as e:
            return {"status": "error", "error": str(e), "models": []}
