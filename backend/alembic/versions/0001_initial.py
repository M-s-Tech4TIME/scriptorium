"""M1 initial schema (hand-written, reviewed — mirrors app/models.py).

Tables: users, memberships, projects, nodes (generic ordered tree),
documents (TipTap JSON canonical), document_history, builds, audit_log.
Cascades: project delete removes its tree; audit/actor refs SET NULL.

Revision ID: 0001initial
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("pw_hash", sa.String(255), nullable=False),
        sa.Column("display", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_format", sa.String(8), server_default="rst", nullable=False),
        sa.Column("theme", sa.String(80), server_default="scriptorium", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_format IN ('rst', 'myst')", name="ck_projects_format"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner', 'editor', 'viewer')", name="ck_memberships_role"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "project_id"),
    )
    op.create_table(
        "nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("kind IN ('category', 'page')", name="ck_nodes_kind"),
        sa.ForeignKeyConstraint(["parent_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nodes_project_id", "nodes", ["project_id"])
    op.create_index("ix_nodes_parent_id", "nodes", ["parent_id"])
    op.create_index(
        "uq_nodes_root_slug",
        "nodes",
        ["project_id", "slug"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_nodes_child_slug",
        "nodes",
        ["project_id", "parent_id", "slug"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tiptap_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_text", sa.Text(), server_default="", nullable=False),
        sa.Column("source_format", sa.String(8), server_default="rst", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id"),
    )
    op.create_table(
        "document_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "tiptap_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("author", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_history_document_id", "document_history", ["document_id"]
    )
    op.create_index(
        "uq_document_history_version",
        "document_history",
        ["document_id", "version"],
        unique=True,
    )
    op.create_table(
        "builds",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), server_default="queued", nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished", sa.DateTime(timezone=True), nullable=True),
        sa.Column("log_path", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'ok', 'failed')", name="ck_builds_status"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_builds_project_id", "builds", ["project_id"])
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("actor", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "meta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_index("ix_builds_project_id", table_name="builds")
    op.drop_table("builds")
    op.drop_index("uq_document_history_version", table_name="document_history")
    op.drop_index("ix_document_history_document_id", table_name="document_history")
    op.drop_table("document_history")
    op.drop_table("documents")
    op.drop_index("uq_nodes_child_slug", table_name="nodes")
    op.drop_index("uq_nodes_root_slug", table_name="nodes")
    op.drop_index("ix_nodes_parent_id", table_name="nodes")
    op.drop_index("ix_nodes_project_id", table_name="nodes")
    op.drop_table("nodes")
    op.drop_table("memberships")
    op.drop_table("projects")
    op.drop_table("users")
