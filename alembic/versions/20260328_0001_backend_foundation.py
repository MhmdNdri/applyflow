"""Backend foundation schema.

Revision ID: 20260328_0001
Revises:
Create Date: 2026-03-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260328_0001"
down_revision = None
branch_labels = None
depends_on = None


application_status = postgresql.ENUM(
    "wishlist",
    "applied",
    "waiting",
    "recruiter screen",
    "interview scheduled",
    "interviewing",
    "final round",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    name="application_status",
    create_type=False,
)

evaluation_verdict = postgresql.ENUM(
    "strong_fit",
    "possible_fit",
    "weak_fit",
    "not_fit",
    name="evaluation_verdict",
    create_type=False,
)

background_task_status = postgresql.ENUM(
    "queued",
    "running",
    "completed",
    "failed",
    name="background_task_status",
    create_type=False,
)

background_task_type = postgresql.ENUM(
    "score_job",
    "generate_cover_letter",
    "export_google_doc",
    "sync_google_sheet",
    name="background_task_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    application_status.create(bind, checkfirst=True)
    evaluation_verdict.create(bind, checkfirst=True)
    background_task_status.create(bind, checkfirst=True)
    background_task_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_clerk_user_id"), "users", ["clerk_user_id"], unique=True)

    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_profiles_user_id"), "profiles", ["user_id"], unique=True)

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version_number", name="uq_resume_versions_profile_version"),
    )
    op.create_index(op.f("ix_resume_versions_profile_id"), "resume_versions", ["profile_id"], unique=False)

    op.create_table(
        "context_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version_number", name="uq_context_versions_profile_version"),
    )
    op.create_index(op.f("ix_context_versions_profile_id"), "context_versions", ["profile_id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role_title", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("current_status", application_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_profile_id"), "jobs", ["profile_id"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("resume_version_id", sa.String(length=36), nullable=True),
        sa.Column("context_version_id", sa.String(length=36), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("verdict", evaluation_verdict, nullable=False),
        sa.Column("top_strengths", sa.JSON(), nullable=False),
        sa.Column("critical_gaps", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("profile_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_version_id"], ["context_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluations_job_id"), "evaluations", ["job_id"], unique=False)

    op.create_table(
        "cover_letters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_id", sa.String(length=36), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("google_doc_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cover_letters_job_id"), "cover_letters", ["job_id"], unique=False)

    op.create_table(
        "application_status_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("previous_status", application_status, nullable=True),
        sa.Column("next_status", application_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_application_status_events_job_id"), "application_status_events", ["job_id"], unique=False)

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

    op.create_table(
        "background_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("task_type", background_task_type, nullable=False),
        sa.Column("status", background_task_status, nullable=False),
        sa.Column("provider_job_id", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_background_tasks_job_id"), "background_tasks", ["job_id"], unique=False)
    op.create_index(op.f("ix_background_tasks_user_id"), "background_tasks", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_background_tasks_user_id"), table_name="background_tasks")
    op.drop_index(op.f("ix_background_tasks_job_id"), table_name="background_tasks")
    op.drop_table("background_tasks")

    op.drop_index(op.f("ix_google_sheet_syncs_user_id"), table_name="google_sheet_syncs")
    op.drop_index(op.f("ix_google_sheet_syncs_job_id"), table_name="google_sheet_syncs")
    op.drop_table("google_sheet_syncs")

    op.drop_index(op.f("ix_google_documents_user_id"), table_name="google_documents")
    op.drop_index(op.f("ix_google_documents_job_id"), table_name="google_documents")
    op.drop_table("google_documents")

    op.drop_index(op.f("ix_google_connections_user_id"), table_name="google_connections")
    op.drop_table("google_connections")

    op.drop_index(op.f("ix_application_status_events_job_id"), table_name="application_status_events")
    op.drop_table("application_status_events")

    op.drop_index(op.f("ix_cover_letters_job_id"), table_name="cover_letters")
    op.drop_table("cover_letters")

    op.drop_index(op.f("ix_evaluations_job_id"), table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_profile_id"), table_name="jobs")
    op.drop_table("jobs")

    op.drop_index(op.f("ix_context_versions_profile_id"), table_name="context_versions")
    op.drop_table("context_versions")

    op.drop_index(op.f("ix_resume_versions_profile_id"), table_name="resume_versions")
    op.drop_table("resume_versions")

    op.drop_index(op.f("ix_profiles_user_id"), table_name="profiles")
    op.drop_table("profiles")

    op.drop_index(op.f("ix_users_clerk_user_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    background_task_type.drop(bind, checkfirst=True)
    background_task_status.drop(bind, checkfirst=True)
    evaluation_verdict.drop(bind, checkfirst=True)
    application_status.drop(bind, checkfirst=True)
