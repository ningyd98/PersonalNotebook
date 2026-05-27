"""Phase 1.5: add started_at/finished_at/retry_count to ingest_jobs, latency_ms to messages

Revision ID: phase_1_5_add_fields
Revises: None
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "phase_1_5_add_fields"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ingest_jobs: add started_at, finished_at, retry_count
    op.add_column("ingest_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingest_jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingest_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))

    # messages: add latency_ms
    op.add_column("messages", sa.Column("latency_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingest_jobs", "retry_count")
    op.drop_column("ingest_jobs", "finished_at")
    op.drop_column("ingest_jobs", "started_at")
    op.drop_column("messages", "latency_ms")
