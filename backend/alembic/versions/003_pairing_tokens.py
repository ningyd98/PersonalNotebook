"""Phase 2A-v2: persist app pairing tokens

Revision ID: 003_pairing_tokens
Revises: 002_phase16
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_pairing_tokens"
down_revision: Union[str, None] = "002_phase16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paired_devices",
        sa.Column("tenant_id", sa.String(100), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_paired_devices_expires_at", "paired_devices", ["expires_at"])
    op.create_index("ix_paired_devices_last_seen_at", "paired_devices", ["last_seen_at"])
    op.create_index("ix_paired_devices_revoked_at", "paired_devices", ["revoked_at"])
    op.create_index("ix_paired_devices_tenant_id", "paired_devices", ["tenant_id"])
    op.create_index("ix_paired_devices_token_hash", "paired_devices", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_paired_devices_token_hash", table_name="paired_devices")
    op.drop_index("ix_paired_devices_tenant_id", table_name="paired_devices")
    op.drop_index("ix_paired_devices_revoked_at", table_name="paired_devices")
    op.drop_index("ix_paired_devices_last_seen_at", table_name="paired_devices")
    op.drop_index("ix_paired_devices_expires_at", table_name="paired_devices")
    op.drop_table("paired_devices")
