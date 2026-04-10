"""Phase 8 hardening cleanup and task reliability metadata.

Revision ID: 20260403_0003
Revises: 20260331_0002
Create Date: 2026-04-03 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260403_0003"
down_revision = "20260331_0002"
branch_labels = None
depends_on = None


legacy_background_task_type_values = (
    "score_job",
    "generate_cover_letter",
    "export_google_doc",
    "sync_google_sheet",
)


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.add_column(sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
        batch_op.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text(
            "DELETE FROM background_tasks WHERE task_type IN ('export_google_doc', 'sync_google_sheet')"
        )
    )

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE background_task_type RENAME TO background_task_type_legacy")
        current_task_type = postgresql.ENUM(
            "score_job",
            "generate_cover_letter",
            name="background_task_type",
        )
        current_task_type.create(bind, checkfirst=False)
        op.execute(
            """
            ALTER TABLE background_tasks
            ALTER COLUMN task_type
            TYPE background_task_type
            USING task_type::text::background_task_type
            """
        )
        op.execute("DROP TYPE background_task_type_legacy")

    op.drop_table("google_documents")
    op.drop_table("google_sheet_syncs")
    op.drop_table("google_connections")

    with op.batch_alter_table("cover_letters") as batch_op:
        batch_op.drop_column("google_doc_url")


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("cover_letters") as batch_op:
        batch_op.add_column(sa.Column("google_doc_url", sa.Text(), nullable=True))

    op.create_table(
        "google_connections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("google_account_email", sa.String(length=320), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_google_connections_user_id"), "google_connections", ["user_id"], unique=True)

    op.create_table(
        "google_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("cover_letter_id", sa.String(length=36), nullable=True),
        sa.Column("external_document_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cover_letter_id"], ["cover_letters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_google_documents_job_id"), "google_documents", ["job_id"], unique=False)
    op.create_index(op.f("ix_google_documents_user_id"), "google_documents", ["user_id"], unique=False)

    op.create_table(
        "google_sheet_syncs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("sheet_id", sa.String(length=255), nullable=False),
        sa.Column("worksheet_name", sa.String(length=255), nullable=True),
        sa.Column("row_reference", sa.String(length=255), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_google_sheet_syncs_job_id"), "google_sheet_syncs", ["job_id"], unique=False)
    op.create_index(op.f("ix_google_sheet_syncs_user_id"), "google_sheet_syncs", ["user_id"], unique=False)

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE background_task_type RENAME TO background_task_type_current")
        legacy_task_type = postgresql.ENUM(*legacy_background_task_type_values, name="background_task_type")
        legacy_task_type.create(bind, checkfirst=False)
        op.execute(
            """
            ALTER TABLE background_tasks
            ALTER COLUMN task_type
            TYPE background_task_type
            USING task_type::text::background_task_type
            """
        )
        op.execute("DROP TYPE background_task_type_current")

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("last_attempt_at")
        batch_op.drop_column("max_attempts")
        batch_op.drop_column("attempt_count")
