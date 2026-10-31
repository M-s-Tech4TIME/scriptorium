"""Media assets — editor-uploaded images/GIFs owned by a grimoire.

V1 media scope: raster images and GIF only. The row stores authorization
metadata and the storage path; bytes live under ``SC_MEDIA_ROOT`` and are
copied into every build snapshot that references them.

Revision ID: 0009media
Revises: 0008urldurability
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009media"
down_revision = "0008urldurability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "grimoire_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "content_type IN "
            "('image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/avif')",
            name="ck_media_assets_type",
        ),
        sa.ForeignKeyConstraint(
            ["grimoire_id"],
            ["grimoires.id"],
            name="fk_media_assets_grimoire_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_media_assets_created_by",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
    )
    op.create_index(
        "ix_media_assets_grimoire_id",
        "media_assets",
        ["grimoire_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_grimoire_id", table_name="media_assets")
    op.drop_table("media_assets")
