"""
Personal-KB 所有数据库模型

表清单：
  - users               用户
  - knowledge_bases     知识库
  - documents           文档
  - document_blocks     统一文档表示 UDR
  - document_chunks     文档切片
  - document_assets     文档资产（图片/音频/视频/附件）
  - table_objects       表格对象
  - media_segments      媒体时间段
  - document_relations  文档关系
  - conversations       会话
  - messages            消息
  - feedback            反馈
  - ingest_jobs         导入任务
  - eval_datasets       评测集
  - eval_cases          评测用例
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer,
    JSON, String, Text, func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin, SoftDeleteMixin

# ============================================================
# 1. users
# ============================================================
class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 关系
    kbs = relationship("KnowledgeBase", back_populates="owner", lazy="selectin")
    conversations = relationship("Conversation", back_populates="user", lazy="selectin")


# ============================================================
# paired_devices — App 配对 token / 设备
# ============================================================
class PairedDevice(Base, UUIDMixin):
    __tablename__ = "paired_devices"

    tenant_id: Mapped[str] = mapped_column(String(100), default="default", nullable=False, index=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


# ============================================================
# 2. knowledge_bases
# ============================================================
class KnowledgeBase(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "knowledge_bases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_llm: Mapped[str] = mapped_column(String(100), default="qwen3:8b")
    embedding_model: Mapped[str] = mapped_column(String(100), default="bge-m3")
    rerank_model: Mapped[str] = mapped_column(String(100), default="qwen3-reranker-0.6b")
    chunk_strategy: Mapped[str] = mapped_column(String(50), default="adaptive")
    visibility: Mapped[str] = mapped_column(String(20), default="private")

    # 关系
    owner = relationship("User", back_populates="kbs")
    documents = relationship("Document", back_populates="kb", lazy="selectin")
    conversations = relationship("Conversation", back_populates="kb", lazy="selectin")
    ingest_jobs = relationship("IngestJob", back_populates="kb", lazy="selectin")


# ============================================================
# 3. documents
# ============================================================
class Document(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "documents"

    kb_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="upload")
    source_uri: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    document_version: Mapped[int] = mapped_column(Integer, default=1)
    parse_status: Mapped[str] = mapped_column(String(30), default="pending")
    embed_status: Mapped[str] = mapped_column(String(30), default="pending")
    index_status: Mapped[str] = mapped_column(String(30), default="pending")
    status: Mapped[str] = mapped_column(
        String(30), default="UPLOADED", nullable=False,
        doc="UPLOADED|PARSING|PARSED|CHUNKING|EMBEDDING|INDEXING|READY|FAILED|DELETED|REINDEXING"
    )
    active_version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 关系
    kb = relationship("KnowledgeBase", back_populates="documents")
    blocks = relationship("DocumentBlock", back_populates="document", lazy="selectin")
    chunks = relationship("DocumentChunk", back_populates="document", lazy="selectin")
    assets = relationship("DocumentAsset", back_populates="document", lazy="selectin")
    tables = relationship("TableObject", back_populates="document", lazy="selectin")
    media_segments = relationship("MediaSegment", back_populates="document", lazy="selectin")
    ingest_jobs = relationship("IngestJob", back_populates="document", lazy="selectin")


# ============================================================
# 4. document_blocks — UDR 核心表
# ============================================================
class DocumentBlock(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_blocks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    parent_block_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_blocks.id"), nullable=True
    )
    block_type: Mapped[str] = mapped_column(
        Enum(
            "heading", "paragraph", "table", "image", "equation",
            "code", "transcript", "video_segment", "list", "quote",
            "metadata", "annotation",
            name="block_type_enum",
        ),
        nullable=False,
    )
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_assets.id"), nullable=True
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slide_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cell_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    section_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 关系
    document = relationship("Document", back_populates="blocks")


# ============================================================
# 5. document_chunks
# ============================================================
class DocumentChunk(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    source_block_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slide_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cell_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    section_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version_id: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # 关系
    document = relationship("Document", back_populates="chunks")


# ============================================================
# 6. document_assets
# ============================================================
class DocumentAsset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_assets"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(
        Enum("image", "audio", "video", "frame", "attachment", name="asset_type_enum"),
        nullable=False,
    )
    asset_uri: Mapped[str] = mapped_column(String(2000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document = relationship("Document", back_populates="assets")


# ============================================================
# 7. table_objects
# ============================================================
class TableObject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "table_objects"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    block_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_blocks.id"), nullable=True
    )
    sheet_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    table_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    headers_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    rows_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    col_count: Mapped[int] = mapped_column(Integer, default=0)
    cell_range: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document = relationship("Document", back_populates="tables")


# ============================================================
# 8. media_segments
# ============================================================
class MediaSegment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "media_segments"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_assets.id"), nullable=True
    )
    segment_type: Mapped[str] = mapped_column(
        Enum("audio", "video", name="segment_type_enum"), nullable=False
    )
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    speaker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keyframes_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document = relationship("Document", back_populates="media_segments")


# ============================================================
# 9. document_relations
# ============================================================
class DocumentRelation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "document_relations"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    target_document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(
        Enum(
            "links_to", "cites", "mentions", "derived_from", "attachment_of",
            name="relation_type_enum",
        ),
        nullable=False,
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


# ============================================================
# 10. conversations
# ============================================================
class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    kb_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user = relationship("User", back_populates="conversations")
    kb = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", lazy="selectin")


# ============================================================
# 11. messages
# ============================================================
class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    retrieval_trace_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", uselist=False, lazy="selectin")


# ============================================================
# 12. feedback
# ============================================================
class Feedback(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "feedback"

    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, unique=True, index=True
    )
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(
        Enum(
            "useful", "not_useful", "citation_error", "irrelevant",
            "hallucination", "incomplete", "wrong_format",
            name="error_type_enum",
        ),
        nullable=True,
    )

    message = relationship("Message", back_populates="feedback")


# ============================================================
# 13. ingest_jobs
# ============================================================
class IngestJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ingest_jobs"

    kb_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=False, index=True
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False,
        doc="PENDING|RUNNING|RETRYING|SUCCESS|FAILED|CANCELLED"
    )
    phase: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True,
        doc="detecting|parsing|chunking|embedding|indexing|checking"
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    kb = relationship("KnowledgeBase", back_populates="ingest_jobs")
    document = relationship("Document", back_populates="ingest_jobs")


# ============================================================
# 14. eval_datasets
# ============================================================
class EvalDataset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eval_datasets"

    kb_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cases = relationship("EvalCase", back_populates="dataset", lazy="selectin")


# ============================================================
# 15. eval_cases
# ============================================================
class EvalCase(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eval_cases"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_docs_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    expected_chunks_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reference_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Evaluation results (Phase 1.6)
    model_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieval_results_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    auto_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    human_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall_at_k: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mrr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_precision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_recall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    refusal_accuracy: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    eval_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    dataset = relationship("EvalDataset", back_populates="cases")
