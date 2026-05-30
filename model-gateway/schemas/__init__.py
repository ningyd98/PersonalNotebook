"""Request / Response schemas for Model Gateway"""

from pydantic import BaseModel, Field


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


class TokenizeRequest(BaseModel):
    text: str
    model: str = ""


class TokenizeResponse(BaseModel):
    token_count: int
    model: str
