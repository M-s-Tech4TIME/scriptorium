"""M3 grimoire rename + per-user categories (decision 0018).

Renames `projects` → `grimoires` (terminology decision Q-M3-5=A) and adds
`grimoire_categories` (Q-M3-6=A) with `grimoires.category_id` (nullable,
SET NULL on category delete — Q-M3-7/8=A). PG FKs bind by OID, so the
rename keeps existing foreign keys live; constraint names are re-pointed
for tidiness.

Revision ID: 0003grimoire
Revises: 0002refresh
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003grimoire"
down_revision = "0002refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("projects", "grimoires")
    op.execute(
        "ALTER TABLE grimoires RENAME CONSTRAINT ck_projects_format "
        "TO ck_grimoires_format"
    )
    op.execute(
        "ALTER TABLE grimoires RENAME CONSTRAINT projects_pkey TO grimoires_pkey"
    )
    # memberships / nodes / builds / audit_log: column + FK + index renames.
    op.execute("ALTER TABLE memberships RENAME COLUMN project_id TO grimoire_id")
    op.execute("ALTER TABLE nodes RENAME COLUMN project_id TO grimoire_id")
    op.execute("ALTER TABLE builds RENAME COLUMN project_id TO grimoire_id")
    op.execute("ALTER TABLE audit_log RENAME COLUMN project_id TO grimoire_id")
    op.execute(
        "ALTER TABLE memberships RENAME CONSTRAINT memberships_project_id_fkey "
        "TO memberships_grimoire_id_fkey"
    )
    op.execute(
        "ALTER TABLE nodes RENAME CONSTRAINT nodes_project_id_fkey "
        "TO nodes_grimoire_id_fkey"
    )
    op.execute(
        "ALTER TABLE builds RENAME CONSTRAINT builds_project_id_fkey "
        "TO builds_grimoire_id_fkey"
    )
    op.execute(
        "ALTER TABLE audit_log RENAME CONSTRAINT audit_log_project_id_fkey "
        "TO audit_log_grimoire_id_fkey"
    )
    op.execute("ALTER INDEX ix_nodes_project_id RENAME TO ix_nodes_grimoire_id")
    op.execute("ALTER INDEX ix_builds_project_id RENAME TO ix_builds_grimoire_id")

    op.create_table(
        "grimoire_categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_grimoire_categories_name"),
    )
    op.create_index(
        "ix_grimoire_categories_user_id", "grimoire_categories", ["user_id"]
    )

    op.add_column(
        "grimoires",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_grimoires_category_id",
        "grimoires",
        "grimoire_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_grimoires_category_id", "grimoires", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_grimoires_category_id", table_name="grimoires")
    op.drop_constraint("fk_grimoires_category_id", "grimoires", type_="foreignkey")
    op.drop_column("grimoires", "category_id")
    op.drop_index("ix_grimoire_categories_user_id", table_name="grimoire_categories")
    op.drop_table("grimoire_categories")
    op.execute("ALTER INDEX ix_builds_grimoire_id RENAME TO ix_builds_project_id")
    op.execute("ALTER INDEX ix_nodes_grimoire_id RENAME TO ix_nodes_project_id")
    op.execute(
        "ALTER TABLE audit_log RENAME CONSTRAINT audit_log_grimoire_id_fkey "
        "TO audit_log_project_id_fkey"
    )
    op.execute(
        "ALTER TABLE builds RENAME CONSTRAINT builds_grimoire_id_fkey "
        "TO builds_project_id_fkey"
    )
    op.execute(
        "ALTER TABLE nodes RENAME CONSTRAINT nodes_grimoire_id_fkey "
        "TO nodes_project_id_fkey"
    )
    op.execute(
        "ALTER TABLE memberships RENAME CONSTRAINT memberships_grimoire_id_fkey "
        "TO memberships_project_id_fkey"
    )
    op.execute("ALTER TABLE audit_log RENAME COLUMN grimoire_id TO project_id")
    op.execute("ALTER TABLE builds RENAME COLUMN grimoire_id TO project_id")
    op.execute("ALTER TABLE nodes RENAME COLUMN grimoire_id TO project_id")
    op.execute("ALTER TABLE memberships RENAME COLUMN grimoire_id TO project_id")
    op.execute(
        "ALTER TABLE grimoires RENAME CONSTRAINT grimoires_pkey TO projects_pkey"
    )
    op.execute(
        "ALTER TABLE grimoires RENAME CONSTRAINT ck_grimoires_format "
        "TO ck_projects_format"
    )
    op.rename_table("grimoires", "projects")
