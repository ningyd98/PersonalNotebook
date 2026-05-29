"""Phase 3B: Knowledge Base Management — retry + soft-delete migration

Revision ID: 004_phase3b
Revises: 003_pairing_tokens
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_phase3b'
down_revision: Union[str, None] = '003_pairing_tokens'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def upgrade() -> None:
    for tbl, col in [("documents", "last_retry_at"), ("ingest_jobs", "last_retry_at")]:
        if not column_exists(tbl, col):
            op.add_column(tbl, sa.Column(col, sa.DateTime(timezone=True), nullable=True))
    if not column_exists("documents", "deleted_at"):
        op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for tbl, col in [("documents", "last_retry_at"), ("documents", "deleted_at"), ("ingest_jobs", "last_retry_at")]:
        if column_exists(tbl, col):
            op.drop_column(tbl, col)
