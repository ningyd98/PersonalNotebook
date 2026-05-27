"""vLLM Provider — 通过 vLLM OpenAI-compatible API 调用模型"""

import os

from loguru import logger

from providers.openai_compatible import OpenAICompatibleProvider

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")


class VLLMProvider(OpenAICompatibleProvider):
    """vLLM 适配器（继承 OpenAI-compatible）"""

    def __init__(self):
        super().__init__()
        self.base_url = VLLM_BASE_URL.rstrip("/")
        # vLLM 通常不需要 API key
