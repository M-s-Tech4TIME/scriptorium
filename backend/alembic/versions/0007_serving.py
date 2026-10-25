"""Serving phase — publication pointers, visibility, public slug, custom CSS.

Decision 0035 (owner-approved A2/B3/C1/D1/E2). Adds:

- ``athenaeums.public_slug`` — a globally unique, immutable URL name. The
  editor-facing ``slug`` remains per-owner (0021); public serving cannot use
  a name that two owners may share, so it gets its own identifier.
- ``athenaeums.is_public`` — private by default (B3).
- ``athenaeums.latest_build_id`` / ``stable_build_id`` — owner-selected
  publication pointers (A2). Numbered build URLs remain immutable.
- ``athenaeums.custom_css`` — validated, namespaced skin input (E2).
- ``builds.published_at`` / ``published_by`` — publication history; a build
  that was ever published stays addressable by its numbered URL.

Backfill is deterministic: a globally unique slug keeps its value; duplicate
per-owner slugs get a full-UUID suffix, with a numeric suffix only if a
user-chosen slug already occupies that generated name (``public_slug`` is
capped at 160 characters; 120 + 1 + 32 fits).

Revision ID: 0007serving
Revises: 0006buildsite
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007serving"
down_revision = "0006buildsite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "athenaeums",
        sa.Column("public_slug", sa.String(160), nullable=True),
    )
    op.add_column(
        "athenaeums",
        sa.Column(
            "is_public",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "athenaeums",
        sa.Column(
            "custom_css",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
    )
    op.add_column(
        "athenaeums",
        sa.Column("latest_build_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "athenaeums",
        sa.Column("stable_build_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Preserve a slug when it is globally unique; otherwise make the public
    # name collision-proof with the full UUID. The public name is intentionally
    # immutable after creation, so a later editor-side rename never breaks a
    # published URL.
    op.execute(
        "UPDATE athenaeums a SET public_slug = a.slug "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM athenaeums b "
        "  WHERE b.slug = a.slug AND b.id <> a.id"
        ")"
    )
    # Generated candidates are checked against every existing public name,
    # so a user-chosen slug that happens to look like a generated suffix
    # cannot make the backfill fail its unique constraint.
    op.execute(
        """
        DO $$
        DECLARE
          r RECORD;
          base TEXT;
          candidate TEXT;
          suffix INT;
        BEGIN
          FOR r IN SELECT id, slug FROM athenaeums WHERE public_slug IS NULL LOOP
            base := left(r.slug, 120) || '-' || replace(r.id::text, '-', '');
            candidate := base;
            suffix := 0;
            WHILE EXISTS (
              SELECT 1 FROM athenaeums WHERE public_slug = candidate
            ) LOOP
              suffix := suffix + 1;
              candidate := left(base, 159 - length(suffix::text)) || '-' || suffix::text;
            END LOOP;
            UPDATE athenaeums SET public_slug = candidate WHERE id = r.id;
          END LOOP;
        END $$;
        """
    )
    op.alter_column("athenaeums", "public_slug", nullable=False)
    op.create_unique_constraint(
        "uq_athenaeums_public_slug", "athenaeums", ["public_slug"]
    )

    op.create_foreign_key(
        "fk_athenaeums_latest_build_id",
        "athenaeums",
        "builds",
        ["latest_build_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_athenaeums_stable_build_id",
        "athenaeums",
        "builds",
        ["stable_build_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "builds",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "builds",
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_builds_published_by",
        "builds",
        "users",
        ["published_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_builds_published_by", "builds", type_="foreignkey")
    op.drop_column("builds", "published_by")
    op.drop_column("builds", "published_at")

    op.drop_constraint(
        "fk_athenaeums_stable_build_id", "athenaeums", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_athenaeums_latest_build_id", "athenaeums", type_="foreignkey"
    )
    op.drop_constraint("uq_athenaeums_public_slug", "athenaeums", type_="unique")
    op.drop_column("athenaeums", "stable_build_id")
    op.drop_column("athenaeums", "latest_build_id")
    op.drop_column("athenaeums", "custom_css")
    op.drop_column("athenaeums", "is_public")
    op.drop_column("athenaeums", "public_slug")
