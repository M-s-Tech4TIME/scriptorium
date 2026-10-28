"""URL durability — the global public-name registry, aliases, tombstones.

Decision 0036 (owner-approved A1/B1/C1/D1/E1/F1). Adds
``public_names`` as the single namespace behind ``/a/{slug}/...``:

- one current row per Athenaeum (partial unique index);
- retired rows remain as permanent aliases;
- deleting an Athenaeum sets ``athenaeum_id`` to NULL but keeps the slug
  as a permanent tombstone, so an old public URL can never be reused.

The migration backfills every existing ``athenaeums.public_slug`` as the
current row. No existing public URL changes.

Revision ID: 0008urldurability
Revises: 0007serving
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008urldurability"
down_revision = "0007serving"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_names",
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_current",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("slug", name="pk_public_names"),
        sa.ForeignKeyConstraint(
            ["athenaeum_id"],
            ["athenaeums.id"],
            name="fk_public_names_athenaeum_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_public_names_athenaeum_id",
        "public_names",
        ["athenaeum_id"],
    )
    op.create_index(
        "uq_public_names_current",
        "public_names",
        ["athenaeum_id"],
        unique=True,
        postgresql_where=sa.text("is_current AND athenaeum_id IS NOT NULL"),
    )
    op.execute(
        "INSERT INTO public_names (slug, athenaeum_id, is_current) "
        "SELECT public_slug, id, true FROM athenaeums"
    )


def downgrade() -> None:
    op.drop_index("uq_public_names_current", table_name="public_names")
    op.drop_index("ix_public_names_athenaeum_id", table_name="public_names")
    op.drop_table("public_names")
