"""Snapshot loading (M4-C3) — DB slices for `plan_site` (decision 0026).

Ordering mirrors the nested sidebar exactly (Q-M3-13): categories by
(position, created_at); grimoires by title within their bucket; the
uncategorized bucket last. Node rows sort by (position, id) — the
stable per-parent sibling order `snapshot_nodes` preserves.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Athenaeum, Document, Grimoire, GrimoireCategory, Node
from app.sphinx.sourcegen import StagedBook, snapshot_nodes


class SnapshotMissing(LookupError):
    """The build references an Athenaeum that no longer exists."""


async def load_site_snapshot(
    session: AsyncSession, athenaeum_id: uuid.UUID
) -> tuple[Athenaeum, list[StagedBook]]:
    """Slice one Athenaeum into the ordered per-book snapshot material."""
    athenaeum = await session.get(Athenaeum, athenaeum_id)
    if athenaeum is None:
        raise SnapshotMissing(f"Athenaeum {athenaeum_id} not found.")

    categories = await session.scalars(
        select(GrimoireCategory)
        .where(GrimoireCategory.athenaeum_id == athenaeum_id)
        .order_by(GrimoireCategory.position, GrimoireCategory.created_at)
    )
    bucket_meta = [(c.id, c.name) for c in categories]
    bucket_order: list[uuid.UUID | None] = [cid for cid, _ in bucket_meta]
    category_name = dict(bucket_meta)

    grimoires = await session.scalars(
        select(Grimoire)
        .where(Grimoire.athenaeum_id == athenaeum_id)
        .order_by(Grimoire.title)
    )
    buckets: dict[Any, list[Grimoire]] = {cid: [] for cid in bucket_order}
    uncategorized: list[Grimoire] = []
    for grimoire in grimoires:
        if grimoire.category_id is None:
            uncategorized.append(grimoire)
        else:
            buckets[grimoire.category_id].append(grimoire)

    ordered: list[Grimoire] = []
    for cid in bucket_order:
        ordered.extend(buckets[cid])
    ordered.extend(uncategorized)

    books: list[StagedBook] = []
    for grimoire in ordered:
        rows = await session.execute(
            select(
                Node.id,
                Node.parent_id,
                Node.kind,
                Node.slug,
                Node.title,
                Document.tiptap_json,
            )
            .select_from(Node)
            .outerjoin(Document, Document.node_id == Node.id)
            .where(Node.grimoire_id == grimoire.id)
            .order_by(Node.position, Node.id)
        )
        node_rows: list[dict[str, Any]] = [
            {
                "id": row[0],
                "parent_id": row[1],
                "kind": row[2],
                "slug": row[3],
                "title": row[4],
                "tiptap": row[5],
            }
            for row in rows
        ]
        books.append(
            StagedBook(
                slug=grimoire.slug,
                title=grimoire.title,
                source_format=grimoire.source_format,
                nodes=snapshot_nodes(node_rows),
                category_label=(
                    category_name[grimoire.category_id]
                    if grimoire.category_id is not None
                    else None
                ),
            )
        )
    return athenaeum, books
