"""Initial migration — create all core tables + seed default user

Revision ID: 001_initial
Revises:
Create Date: 2026-05-27
"""
import uuid
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- knowledge_bases ---
    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_llm", sa.String(100), nullable=False, server_default="qwen3:8b"),
        sa.Column("embedding_model", sa.String(100), nullable=False, server_default="bge-m3"),
        sa.Column("rerank_model", sa.String(100), nullable=False, server_default="qwen3-reranker-0.6b"),
        sa.Column("chunk_strategy", sa.String(50), nullable=False, server_default="adaptive"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=False, index=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("mime_type", sa.String(200), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_hash", sa.String(128), nullable=False, index=True),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="upload"),
        sa.Column("source_uri", sa.String(2000), nullable=True),
        sa.Column("document_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parse_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("embed_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("index_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- document_blocks ---
    op.create_table(
        "document_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("parent_block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_blocks.id"), nullable=True),
        sa.Column("block_type", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("structured_json", postgresql.JSON(), nullable=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("slide_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("cell_range", sa.String(100), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=True),
        sa.Column("end_time", sa.Float(), nullable=True),
        sa.Column("bbox_json", postgresql.JSON(), nullable=True),
        sa.Column("section_path", sa.String(1000), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False, index=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_block_ids", postgresql.JSON(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("slide_number", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("cell_range", sa.String(100), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=True),
        sa.Column("end_time", sa.Float(), nullable=True),
        sa.Column("section_path", sa.String(1000), nullable=True),
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- document_assets ---
    op.create_table(
        "document_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("asset_uri", sa.String(2000), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=False),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- table_objects ---
    op.create_table(
        "table_objects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_blocks.id"), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("table_name", sa.String(255), nullable=True),
        sa.Column("headers_json", postgresql.JSON(), nullable=True),
        sa.Column("rows_json", postgresql.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("col_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cell_range", sa.String(200), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- media_segments ---
    op.create_table(
        "media_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("segment_type", sa.String(10), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("visual_caption", sa.Text(), nullable=True),
        sa.Column("speaker", sa.String(255), nullable=True),
        sa.Column("keyframes_json", postgresql.JSON(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- document_relations ---
    op.create_table(
        "document_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("target_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=True, index=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False, index=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", postgresql.JSON(), nullable=True),
        sa.Column("retrieval_trace_json", postgresql.JSON(), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- feedback ---
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id"), nullable=False, unique=True, index=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- ingest_jobs ---
    op.create_table(
        "ingest_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=False, index=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True, index=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("warnings_json", postgresql.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- eval_datasets ---
    op.create_table(
        "eval_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("kb_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("knowledge_bases.id"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- eval_cases ---
    op.create_table(
        "eval_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_datasets.id"), nullable=False, index=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_docs_json", postgresql.JSON(), nullable=True),
        sa.Column("expected_chunks_json", postgresql.JSON(), nullable=True),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("answer_type", sa.String(50), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Seed default user (MVP single-user mode) ---
    DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
    op.execute(
        f"INSERT INTO users (id, username, email, password_hash, role) "
        f"VALUES ('{DEFAULT_USER_ID}', 'admin', 'admin@personal-kb.local', "
        f"'$2b$12$default_hash_for_mvp_single_user_mode', 'admin') "
        f"ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000001'")
    op.drop_table("eval_cases")
    op.drop_table("eval_datasets")
    op.drop_table("ingest_jobs")
    op.drop_table("feedback")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("document_relations")
    op.drop_table("media_segments")
    op.drop_table("table_objects")
    op.drop_table("document_assets")
    op.drop_table("document_chunks")
    op.drop_table("document_blocks")
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
    op.drop_table("users")
