"""
Personal-KB Pydantic Schemas
API 请求/响应模型定义
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 通用
# ============================================================
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


# ============================================================
# 知识库
# ============================================================
class KBCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    default_llm: str = "qwen3:8b"
    embedding_model: str = "bge-m3"
    rerank_model: str = "qwen3-reranker-0.6b"
    chunk_strategy: str = "adaptive"
    visibility: str = "private"


class KBUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_llm: Optional[str] = None
    embedding_model: Optional[str] = None
    rerank_model: Optional[str] = None
    chunk_strategy: Optional[str] = None
    visibility: Optional[str] = None


class KBResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    default_llm: str
    embedding_model: str
    rerank_model: str
    chunk_strategy: str
    visibility: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    chunk_count: int = 0
    last_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================
# 文档
# ============================================================
class DocumentImportRequest(BaseModel):
    source_type: str = "upload"  # upload | local_folder | nas | obsidian
    source_path: Optional[str] = None  # 用于 local_folder / nas
    parse_options: Optional[dict] = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    file_hash: str
    storage_path: str
    source_type: str
    source_uri: Optional[str] = None
    document_version: int
    parse_status: str
    embed_status: str
    index_status: str
    title: Optional[str] = None
    author: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentBlockResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    parent_block_id: Optional[uuid.UUID] = None
    block_type: str
    text: Optional[str] = None
    structured_json: Optional[dict] = None
    asset_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    bbox_json: Optional[dict] = None
    section_path: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    kb_id: uuid.UUID
    chunk_index: int
    content: str
    content_hash: str
    token_count: int
    source_block_ids: Optional[list] = None
    metadata_json: Optional[dict] = None
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    section_path: Optional[str] = None
    embedding_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentAssetResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    asset_type: str
    asset_uri: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    checksum: str
    metadata_json: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TableObjectResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    sheet_name: Optional[str] = None
    table_name: Optional[str] = None
    headers_json: Optional[list] = None
    rows_json: Optional[list] = None
    summary: Optional[str] = None
    row_count: int
    col_count: int
    cell_range: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityReportResponse(BaseModel):
    document_id: uuid.UUID
    parse_quality: dict
    chunk_quality: dict
    overall_status: str


# ============================================================
# 任务
# ============================================================
class IngestJobResponse(BaseModel):
    id: uuid.UUID
    kb_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    job_type: str
    status: str
    progress: float
    error_message: Optional[str] = None
    warnings_json: Optional[list] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 问答
# ============================================================
class ChatRequest(BaseModel):
    kb_id: uuid.UUID
    question: str = Field(min_length=1, max_length=5000)
    retrieval_mode: str = "auto"  # auto | vector_only | hybrid | table | media
    top_k: int = Field(default=8, ge=1, le=40)
    use_rerank: bool = True
    strict_citation: bool = True
    conversation_id: Optional[uuid.UUID] = None
    debug: bool = False  # 是否返回检索 trace


class Citation(BaseModel):
    evidence_id: str
    source_type: str
    document_id: uuid.UUID
    filename: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    section_path: Optional[str] = None
    score: float
    content_preview: str
    asset_preview: Optional[str] = None


class RetrievalTrace(BaseModel):
    query: str
    query_type: str
    rewrite_query: Optional[str] = None
    retrievers: dict
    rerank_top_k: int
    selected_evidence: list[str]
    latency_ms: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    trace: Optional[RetrievalTrace] = None
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    model: str
    latency_ms: float = 0.0


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    kb_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations_json: Optional[list] = None
    retrieval_trace_json: Optional[dict] = None
    model_name: Optional[str] = None
    latency_ms: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackRequest(BaseModel):
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = None
    error_type: Optional[str] = None  # useful | not_useful | citation_error | irrelevant | hallucination | incomplete | wrong_format


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    message_id: uuid.UUID
    rating: Optional[int] = None
    comment: Optional[str] = None
    error_type: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 评测
# ============================================================
class EvalDatasetCreate(BaseModel):
    kb_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None


class EvalCaseCreate(BaseModel):
    question: str
    expected_docs_json: Optional[list] = None
    expected_chunks_json: Optional[list] = None
    reference_answer: Optional[str] = None
    answer_type: Optional[str] = None  # factoid | summary | comparison | reasoning | no_answer | table_qa | image_qa | video_qa
    metadata_json: Optional[dict] = None


class EvalRunRequest(BaseModel):
    dataset_id: uuid.UUID
    kb_id: uuid.UUID
    top_k: int = 8
    use_rerank: bool = True


class EvalMetricsResponse(BaseModel):
    recall_at_k: dict
    mrr: float
    rerank_accuracy: Optional[float] = None
    answer_faithfulness: float
    citation_accuracy: float
    hallucination_rate: float
    refusal_accuracy: float
    avg_latency_ms: float
    total_cases: int
    passed_cases: int


# ============================================================
# 用户 / 认证
# ============================================================
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
