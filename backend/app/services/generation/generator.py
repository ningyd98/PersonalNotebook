"""
LLM 生成服务 — Phase 3D: error classification + fallback
"""

import re
import time
from typing import Optional

import httpx
from loguru import logger

from app.core.config import get_settings

settings = get_settings()

RAG_SYSTEM_PROMPT = (
    "你是个人知识库问答助手。\n"
    "你必须优先依据提供的知识库证据回答。\n"
    "如果证据不足，必须明确说明'当前知识库未找到可靠依据'。\n"
    "不得编造文件名、页码、章节、时间戳、表格范围。\n"
    "回答中必须给出引用来源，格式为 [证据X]。\n"
    "如果多个证据存在冲突，请指出冲突。\n"
    "如果问题需要表格计算，而证据中没有足够数据，请说明缺少哪些数据。\n"
    "回答要用中文，结构清晰，适合个人学习和工作使用。"
)

FALLBACK_ANSWER = "模型服务暂时不可用。以下为知识库中检索到的相关证据，尚未经模型整理。"


def _classify_model_error(e: Exception) -> dict:
    """Classify model errors into typed categories."""
    msg = str(e)
    if isinstance(e, httpx.ConnectError):
        return {"type": "gateway_unavailable", "message": "无法连接到模型网关", "retryable": True}
    if isinstance(e, httpx.TimeoutException):
        return {"type": "timeout", "message": "模型请求超时", "retryable": True}
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        body = (e.response.text or "")[:300].lower()
        # Text-based API key detection
        if any(kw in body for kw in ("missing api key", "no api key", "api key required", "unauthorized", "invalid api key", "authentication failed")):
            if "missing" in body or "required" in body or "no api" in body:
                return {"type": "missing_api_key", "message": "缺少 API Key，请检查环境变量配置", "retryable": False}
            return {"type": "invalid_api_key", "message": "API Key 无效或已过期", "retryable": False}
        if code == 401 or code == 403:
            return {"type": "invalid_api_key", "message": "API Key 无效或已过期", "retryable": False}
        if code == 429:
            return {"type": "rate_limited", "message": "API 请求频率限制", "retryable": True}
        if code >= 500:
            return {"type": "upstream_llm_unavailable", "message": f"上游模型服务不可用 (HTTP {code})", "retryable": True}
        if code == 404:
            return {"type": "model_not_found", "message": "模型不存在或未拉取", "retryable": False}
        return {"type": "unknown_model_error", "message": sanitize_error(msg[:200]), "retryable": True}
    return {"type": "unknown_model_error", "message": sanitize_error(msg[:200]), "retryable": True}


def sanitize_error(msg: str) -> str:
    """Remove sensitive data from error messages."""
    import re
    msg = re.sub(r'sk-[a-zA-Z0-9]{10,}', 'sk-***REDACTED', msg)
    msg = re.sub(r'Bearer\s+\S+', 'Bearer ***REDACTED', msg)
    msg = re.sub(r'(api_key|apikey)=[^&\s]+', r'\1=***REDACTED', msg, flags=re.IGNORECASE)
    return msg


class GenerationService:
    """LLM 生成服务 with error classification and fallback."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.DEFAULT_LLM
        self.gateway_url = settings.MODEL_GATEWAY_URL.rstrip("/")

    async def generate(
        self, question: str, evidence_pack: list[dict],
        conversation_history: Optional[list[dict]] = None,
        strict_citation: bool = True,
    ) -> dict:
        start_time = time.time()
        model_error = None
        answer = ""
        raw_citations = []

        user_prompt = self._build_prompt(question, evidence_pack, strict_citation)
        messages = [{"role": "system", "content": RAG_SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history[-6:])
        messages.append({"role": "user", "content": user_prompt})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.gateway_url}/model/chat",
                    json={"model": self.model, "messages": messages,
                          "temperature": 0.2, "max_tokens": 2048},
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("content", "")
        except Exception as e:
            logger.error(f"LLM generation failed: {sanitize_error(str(e))}")
            model_error = _classify_model_error(e)
            if evidence_pack:
                answer = FALLBACK_ANSWER
            else:
                answer = "抱歉，模型服务暂时不可用，且知识库中未检索到相关证据。"

        latency_ms = (time.time() - start_time) * 1000

        if strict_citation:
            raw_citations = self._extract_citations(answer, evidence_pack)

        return {
            "answer": answer,
            "citations": raw_citations,
            "model": self.model,
            "latency_ms": latency_ms,
            "model_error": model_error,
        }

    @staticmethod
    def _build_prompt(question: str, evidence_pack: list[dict], strict_citation: bool) -> str:
        """构造给 LLM 的用户 prompt"""
        evidence_text_parts = []
        for ev in evidence_pack:
            source_info = f"[证据{ev['evidence_id']}] 来源：{ev.get('filename', '')}"
            if ev.get("section_path"):
                source_info += f" > {ev['section_path']}"
            if ev.get("page_number"):
                source_info += f" 第{ev['page_number']}页"
            if ev.get("slide_number"):
                source_info += f" 第{ev['slide_number']}页幻灯片"

            evidence_text_parts.append(
                f"{source_info}\n内容：{ev.get('content', '')}\n"
            )

        evidence_text = "\n---\n".join(evidence_text_parts)

        citation_instruction = ""
        if strict_citation:
            citation_instruction = (
                "\n\n【重要】你的回答必须基于以上证据。每个关键信息点后标注引用来源，"
                "格式为 [证据X]。如果没有相关证据，请明确说"
                "'当前知识库未找到可靠依据'。"
            )

        return (
            f"请根据以下知识库证据回答问题。\n\n"
            f"## 知识库证据\n\n{evidence_text}\n\n"
            f"## 问题\n\n{question}"
            f"{citation_instruction}"
        )

    @staticmethod
    def _extract_citations(answer: str, evidence_pack: list[dict]) -> list[dict]:
        """
        从 LLM 回答中提取引用标记，匹配 evidence_pack。
        返回格式化的 citation 列表。
        """
        citations = []
        ev_map = {ev["evidence_id"]: ev for ev in evidence_pack}

        # 匹配 [证据X] 格式
        pattern = re.compile(r"\[证据([^\]]+)\]")
        seen_ids = set()
        for match in pattern.finditer(answer):
            ev_id = match.group(1).strip()
            if ev_id not in ev_map or ev_id in seen_ids:
                continue
            seen_ids.add(ev_id)
            ev = ev_map[ev_id]
            citations.append({
                "evidence_id": ev_id,
                "source_type": ev.get("source_type", "text"),
                "document_id": ev.get("document_id", ""),
                "filename": ev.get("filename", ""),
                "page_number": ev.get("page_number"),
                "slide_number": ev.get("slide_number"),
                "section_path": ev.get("section_path"),
                "score": ev.get("score", 0.0),
                "content_preview": ev.get("content", "")[:200],
                "asset_preview": ev.get("metadata", {}).get("asset_preview"),
            })

        return citations
