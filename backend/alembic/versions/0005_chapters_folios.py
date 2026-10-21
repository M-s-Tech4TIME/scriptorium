"""M3.7 folio/chapter vocabulary (decision 0022) — kind value rewrite.

`nodes.kind` ∈ ('page','category') under 0010 becomes ('folio','chapter')
under the owner's library vocabulary. The CHECK is dropped first (values
outside it can't be written while it exists), data rewritten, CHECK
recreated with the same name; downgrade is the exact mirror. Append-only
history: 0001–0004 untouched.
"""

from __future__ import annotations

from alembic import op

revision = "0005foliochapter"
down_revision = "0004athenaeum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_nodes_kind", "nodes", type_="check")
    op.execute("UPDATE nodes SET kind = 'chapter' WHERE kind = 'category'")
    op.execute("UPDATE nodes SET kind = 'folio' WHERE kind = 'page'")
    op.create_check_constraint("ck_nodes_kind", "nodes", "kind IN ('chapter', 'folio')")


def downgrade() -> None:
    op.drop_constraint("ck_nodes_kind", "nodes", type_="check")
    op.execute("UPDATE nodes SET kind = 'page' WHERE kind = 'folio'")
    op.execute("UPDATE nodes SET kind = 'category' WHERE kind = 'chapter'")
    op.create_check_constraint("ck_nodes_kind", "nodes", "kind IN ('category', 'page')")
