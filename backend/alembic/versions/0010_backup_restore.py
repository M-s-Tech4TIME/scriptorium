"""Backup/restore — tombstone ownership + async backup jobs.

Revision ID: 0010backup
Revises: 0009media

0039 E1 requires restore to distinguish a user's own public-name tombstone
from someone else's. `public_names.owner_id` is backfilled from each live
Athenaeum and preserved when the Athenaeum row is deleted.

`backup_jobs` tracks Full exports and Full restores; Editorial exports are
synchronous and never create a row.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010backup"
down_revision = "0009media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "public_names",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_public_names_owner_id",
        "public_names",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE public_names AS pn
        SET owner_id = a.owner_id
        FROM athenaeums AS a
        WHERE pn.athenaeum_id = a.id
        """
    )

    op.create_table(
        "backup_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('export', 'restore')", name="ck_backup_jobs_kind"),
        sa.CheckConstraint("mode IN ('editorial', 'full')", name="ck_backup_jobs_mode"),
        sa.CheckConstraint("format IN ('zip', 'tar.gz')", name="ck_backup_jobs_format"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'ok', 'failed')",
            name="ck_backup_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["athenaeum_id"],
            ["athenaeums.id"],
            name="fk_backup_jobs_athenaeum_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["result_athenaeum_id"],
            ["athenaeums.id"],
            name="fk_backup_jobs_result_athenaeum_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name="fk_backup_jobs_requested_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backup_jobs"),
    )
    op.create_index("ix_backup_jobs_athenaeum_id", "backup_jobs", ["athenaeum_id"])


def downgrade() -> None:
    op.drop_index("ix_backup_jobs_athenaeum_id", table_name="backup_jobs")
    op.drop_table("backup_jobs")
    op.drop_constraint("fk_public_names_owner_id", "public_names", type_="foreignkey")
    op.drop_column("public_names", "owner_id")
