"""Phase 1.6: stability & trust — state machine, versioning, idempotency, eval fields

Revision ID: 002_phase16
Revises: 001_initial
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_phase16"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users: add tenant_id
    op.add_column("users", sa.Column("tenant_id", sa.String(100), nullable=True))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # documents: add status, active_version
    op.add_column("documents", sa.Column("status", sa.String(30), nullable=False, server_default="UPLOADED"))
    op.add_column("documents", sa.Column("active_version", sa.Integer(), nullable=False, server_default="1"))

    # document_chunks: add version_id, idempotency_key
    op.add_column("document_chunks", sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("document_chunks", sa.Column("idempotency_key", sa.String(128), nullable=True))
    op.create_index("ix_document_chunks_idempotency_key", "document_chunks", ["idempotency_key"])

    # ingest_jobs: migrate status enum to new values, add phase + idempotency_key
    # Drop old enum type and recreate with new values
    op.execute("ALTER TABLE ingest_jobs ALTER COLUMN status TYPE VARCHAR(30)")
    op.execute("UPDATE ingest_jobs SET status = 'RUNNING' WHERE status IN ('detecting','extracting','parsing','ocr','asr','captioning','chunking','embedding','indexing','checking')")
    op.execute("UPDATE ingest_jobs SET status = 'SUCCESS' WHERE status IN ('completed','partially_completed')")
    op.execute("UPDATE ingest_jobs SET status = 'FAILED' WHERE status = 'failed'")
    op.execute("UPDATE ingest_jobs SET status = 'PENDING' WHERE status = 'pending'")

    op.add_column("ingest_jobs", sa.Column("phase", sa.String(30), nullable=True))
    op.add_column("ingest_jobs", sa.Column("idempotency_key", sa.String(128), nullable=True))
    op.create_index("ix_ingest_jobs_idempotency_key", "ingest_jobs", ["idempotency_key"])

    # eval_cases: add evaluation result fields
    op.add_column("eval_cases", sa.Column("model_answer", sa.Text(), nullable=True))
    op.add_column("eval_cases", sa.Column("retrieval_results_json", postgresql.JSON(), nullable=True))
    op.add_column("eval_cases", sa.Column("auto_score", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("human_score", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("recall_at_k", postgresql.JSON(), nullable=True))
    op.add_column("eval_cases", sa.Column("mrr", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("citation_precision", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("citation_recall", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("faithfulness", sa.Float(), nullable=True))
    op.add_column("eval_cases", sa.Column("refusal_accuracy", sa.Boolean(), nullable=True))
    op.add_column("eval_cases", sa.Column("eval_latency_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("eval_cases", "eval_latency_ms")
    op.drop_column("eval_cases", "refusal_accuracy")
    op.drop_column("eval_cases", "faithfulness")
    op.drop_column("eval_cases", "citation_recall")
    op.drop_column("eval_cases", "citation_precision")
    op.drop_column("eval_cases", "mrr")
    op.drop_column("eval_cases", "recall_at_k")
    op.drop_column("eval_cases", "human_score")
    op.drop_column("eval_cases", "auto_score")
    op.drop_column("eval_cases", "retrieval_results_json")
    op.drop_column("eval_cases", "model_answer")

    op.drop_index("ix_ingest_jobs_idempotency_key", table_name="ingest_jobs")
    op.drop_column("ingest_jobs", "idempotency_key")
    op.drop_column("ingest_jobs", "phase")

    op.drop_index("ix_document_chunks_idempotency_key", table_name="document_chunks")
    op.drop_column("document_chunks", "idempotency_key")
    op.drop_column("document_chunks", "version_id")

    op.drop_column("documents", "active_version")
    op.drop_column("documents", "status")

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")
