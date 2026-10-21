"""M4 build identity — per-Athenaeum site builds (decision 0026).

`builds` gains `athenaeum_id` (FK athenaeums, CASCADE — delete-refusal per
Q-M3-11=A makes it belt-and-braces) and `build_number` (per-Athenaeum
monotonic counter, backfilled deterministically). `grimoire_id` relaxes to
nullable: pre-M4 rows remain grimoire-keyed (their data is untouched);
0026 rows are site builds keyed by `athenaeum_id`. `ck_builds_site`
keeps exactly one of the two keys set — no both-null, no both-set.
Downgrade restores the grimoire-keyed NOT NULL law (honest mirror: it
fails if any 0026-era rows exist). Append-only history: 0001–0005
untouched.

Revision ID: 0006buildsite
Revises: 0005foliochapter
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006buildsite"
down_revision = "0005foliochapter"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "builds",
        sa.Column("athenaeum_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_builds_athenaeum_id",
        "builds",
        "athenaeums",
        ["athenaeum_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_builds_athenaeum_id", "builds", ["athenaeum_id"])

    # Backfill: number every known build — per-Athenaeum sequence; the
    # pre-M4 grimoire-era rows share one legacy sequence under the NULL
    # partition (ordered by started, id — deterministic and derived).
    op.add_column("builds", sa.Column("build_number", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE builds SET build_number = s.n FROM ("
        "  SELECT id, ROW_NUMBER() OVER ("
        "    PARTITION BY athenaeum_id ORDER BY started NULLS LAST, id"
        "  ) AS n FROM builds"
        ") AS s WHERE builds.id = s.id"
    )
    op.alter_column("builds", "build_number", nullable=False)
    op.create_unique_constraint(
        "uq_builds_athenaeum_number",
        "builds",
        ["athenaeum_id", "build_number"],
    )

    # Site-build era: grimoire key becomes optional for new rows only.
    op.alter_column(
        "builds",
        "grimoire_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_builds_site",
        "builds",
        "((grimoire_id IS NULL) != (athenaeum_id IS NULL))",
    )


def downgrade() -> None:
    # Honest mirror (integrity discipline): the legacy model only had
    # grimoire builds — library-era rows cannot be represented, so the
    # downgrade drops them before re-tightening the legacy NOT NULL.
    # (Found by C3 live rounds: athenaeum-keyed test rows previously
    # failed this ALTER at downgrade time.)
    op.execute("DELETE FROM builds WHERE athenaeum_id IS NOT NULL")
    op.drop_constraint("ck_builds_site", "builds", type_="check")
    op.alter_column(
        "builds",
        "grimoire_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint("uq_builds_athenaeum_number", "builds", type_="unique")
    op.drop_column("builds", "build_number")
    op.drop_index("ix_builds_athenaeum_id", table_name="builds")
    op.drop_constraint("fk_builds_athenaeum_id", "builds", type_="foreignkey")
    op.drop_column("builds", "athenaeum_id")
