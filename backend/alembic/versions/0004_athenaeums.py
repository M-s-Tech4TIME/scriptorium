"""M3.5 athenaeum layer — native library hierarchy (decision 0020).

Creates `athenaeums` (per-user libraries), re-scopes `grimoire_categories`
to Athenaeums (drops user_id), and pins every grimoire to an Athenaeum
(NOT NULL, backfilled into a per-user "Default" library). Delete-refusal
(Q-M3-11=A) makes the CASCADE on grimoires.athenaeum_id unreachable via
API — belt and braces.

Revision ID: 0004athenaeum
Revises: 0003grimoire
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004athenaeum"
down_revision = "0003grimoire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "athenaeums",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "slug", name="uq_athenaeums_owner_slug"),
    )
    op.create_index("ix_athenaeums_owner_id", "athenaeums", ["owner_id"])

    # Backfill: one "Default" Athenaeum per user.
    op.execute(
        "INSERT INTO athenaeums (id, owner_id, slug, title) "
        "SELECT gen_random_uuid(), u.id, 'default', 'Default' "
        "FROM users u"
    )

    # grimoire_categories: user_id → athenaeum_id
    op.add_column(
        "grimoire_categories",
        sa.Column("athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE grimoire_categories gc SET athenaeum_id = a.id "
        "FROM athenaeums a WHERE a.owner_id = gc.user_id"
    )
    op.alter_column("grimoire_categories", "athenaeum_id", nullable=False)
    op.drop_constraint(
        "uq_grimoire_categories_name", "grimoire_categories", type_="unique"
    )
    op.drop_index("ix_grimoire_categories_user_id", table_name="grimoire_categories")
    op.drop_column("grimoire_categories", "user_id")
    op.create_unique_constraint(
        "uq_grimoire_categories_name",
        "grimoire_categories",
        ["athenaeum_id", "name"],
    )
    op.create_foreign_key(
        "fk_grimoire_categories_athenaeum_id",
        "grimoire_categories",
        "athenaeums",
        ["athenaeum_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_grimoire_categories_athenaeum_id",
        "grimoire_categories",
        ["athenaeum_id"],
    )

    # grimoires: every grimoire gets an Athenaeum home.
    op.add_column(
        "grimoires",
        sa.Column("athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE grimoires g SET athenaeum_id = COALESCE("
        "  (SELECT a.id FROM athenaeums a WHERE a.owner_id = g.created_by LIMIT 1),"
        "  (SELECT a.id FROM athenaeums a ORDER BY a.created_at, a.id LIMIT 1))"
    )
    op.alter_column("grimoires", "athenaeum_id", nullable=False)
    op.create_foreign_key(
        "fk_grimoires_athenaeum_id",
        "grimoires",
        "athenaeums",
        ["athenaeum_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_grimoires_athenaeum_id", "grimoires", ["athenaeum_id"])


def downgrade() -> None:
    op.drop_index("ix_grimoires_athenaeum_id", table_name="grimoires")
    op.drop_constraint("fk_grimoires_athenaeum_id", "grimoires", type_="foreignkey")
    op.drop_column("grimoires", "athenaeum_id")

    op.drop_index(
        "ix_grimoire_categories_athenaeum_id", table_name="grimoire_categories"
    )
    op.drop_constraint(
        "fk_grimoire_categories_athenaeum_id", "grimoire_categories", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_grimoire_categories_name", "grimoire_categories", type_="unique"
    )
    op.add_column(
        "grimoire_categories",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "UPDATE grimoire_categories gc SET user_id = a.owner_id "
        "FROM athenaeums a WHERE a.id = gc.athenaeum_id"
    )
    op.alter_column("grimoire_categories", "user_id", nullable=False)
    op.create_unique_constraint(
        "uq_grimoire_categories_name",
        "grimoire_categories",
        ["user_id", "name"],
    )
    op.create_index(
        "ix_grimoire_categories_user_id", "grimoire_categories", ["user_id"]
    )
    op.drop_column("grimoire_categories", "athenaeum_id")

    op.drop_index("ix_athenaeums_owner_id", table_name="athenaeums")
    op.drop_table("athenaeums")
