"""Add profile upload columns for resume and context versions.

Revision ID: 20260331_0002
Revises: 20260328_0001
Create Date: 2026-03-31 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_0002"
down_revision = "20260328_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("resume_versions", "context_versions"):
        op.add_column(table_name, sa.Column("source_file_name", sa.String(length=512), nullable=True))
        op.add_column(table_name, sa.Column("source_file_mime_type", sa.String(length=255), nullable=True))
        op.add_column(table_name, sa.Column("source_file_size_bytes", sa.Integer(), nullable=True))
        op.add_column(table_name, sa.Column("source_file_bytes", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    for table_name in ("context_versions", "resume_versions"):
        op.drop_column(table_name, "source_file_bytes")
        op.drop_column(table_name, "source_file_size_bytes")
        op.drop_column(table_name, "source_file_mime_type")
        op.drop_column(table_name, "source_file_name")
