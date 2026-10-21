"""Grimoire tree endpoints — Chapters & Folios (decision 0023).

Access: any member reads the tree; mutations are owner-only (D2=A).
Delete refuses 409 while the node still holds sub-nodes or a folio
document (D1=A). Re-parenting is same-Grimoire only with a cycle guard;
reorder is explicit 1-based insert-displacement (Q-M3-4=A). Slugs are
renamable per sibling set (0021). Chapter/folio kinds (0022) do not
restrict nesting — Scriptorium keeps full Sphinx/RTD flexibility
(0023 micro-default).
"""

from __future__ import annotations

import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id, require_membership
from app.db import get_session
from app.models import Document, Node

router = APIRouter(prefix="/api/v1/grimoires/{grimoire_id}", tags=["tree"])

_SLUG_RE = re.compile(r"[a-z0-9-]+")


class NodeIn(BaseModel):
    parent_id: uuid.UUID | None = None  # omitted/`null` inserts into the root set
    kind: Literal["chapter", "folio"]
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=160)


class NodePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    parent_id: uuid.UUID | None = None  # presence = re-parent; `null` = move to root
    position: int | None = Field(default=None, ge=1)


def _check_slug(slug: str) -> str:
    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Slug must match [a-z0-9-]+.",
        )
    return slug


def _node_body(node: Node) -> dict[str, object]:
    return {
        "id": str(node.id),
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "kind": node.kind,
        "title": node.title,
        "slug": node.slug,
        "position": node.position,
        "children": [],
    }


async def _require_owner(
    grimoire_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> None:
    role = await require_membership(grimoire_id, user_id, session)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required."
        )


async def _node_in_grimoire(
    grimoire_id: uuid.UUID, node_id: uuid.UUID, session: AsyncSession
) -> Node:
    node = (
        await session.scalars(
            select(Node).where(Node.id == node_id, Node.grimoire_id == grimoire_id)
        )
    ).first()
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found."
        )
    return node


async def _resolve_parent(
    grimoire_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    session: AsyncSession,
) -> Node | None:
    """Parent for create/re-parent: `None` = root set; foreign/unknown → `404`."""
    if parent_id is None:
        return None
    parent = (
        await session.scalars(
            select(Node).where(Node.id == parent_id, Node.grimoire_id == grimoire_id)
        )
    ).first()
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Node not found."
        )
    return parent


def _sibling_filters(
    grimoire_id: uuid.UUID, parent_id: uuid.UUID | None
) -> list[ColumnElement[bool]]:
    if parent_id is None:
        return [Node.grimoire_id == grimoire_id, Node.parent_id.is_(None)]
    return [Node.grimoire_id == grimoire_id, Node.parent_id == parent_id]


@router.get("/tree")
async def get_tree(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await require_membership(grimoire_id, user_id, session)
    nodes = (
        await session.scalars(
            select(Node)
            .where(Node.grimoire_id == grimoire_id)
            .order_by(Node.position, Node.id)
        )
    ).all()  # materialize once — ScalarResult is single-pass
    bodies: dict[uuid.UUID, dict[str, object]] = {
        node.id: _node_body(node) for node in nodes
    }
    children_of: dict[str, list[dict[str, object]]] = {}
    for node in nodes:
        key = str(node.parent_id) if node.parent_id else "root"
        children_of.setdefault(key, []).append(bodies[node.id])
    for node in nodes:
        key = str(node.parent_id) if node.parent_id else "root"
        bodies[node.id]["children"] = children_of.get(key, [])
    return {"grimoire_id": str(grimoire_id), "nodes": children_of.get("root", [])}


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
async def create_node(
    grimoire_id: uuid.UUID,
    body: NodeIn,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await _require_owner(grimoire_id, user_id, session)
    _check_slug(body.slug)
    parent = await _resolve_parent(grimoire_id, body.parent_id, session)
    parent_id = parent.id if parent is not None else None
    dup = await session.scalar(
        select(Node.id).where(
            *_sibling_filters(grimoire_id, parent_id),
            Node.slug == body.slug,
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already exists here."
        )
    next_pos = await session.scalar(
        select(func.max(Node.position)).where(*_sibling_filters(grimoire_id, parent_id))
    )
    node = Node(
        grimoire_id=grimoire_id,
        parent_id=parent_id,
        kind=body.kind,
        title=body.title,
        slug=body.slug,
        position=(next_pos or 0) + 1,
    )
    session.add(node)
    await session.flush()
    add_audit(
        session,
        actor=user_id,
        action="node_created",
        grimoire_id=grimoire_id,
        meta={
            "node_id": str(node.id),
            "kind": node.kind,
            "parent_id": str(parent_id) if parent_id else None,
        },
    )
    await session.commit()
    return _node_body(node)


@router.patch("/nodes/{node_id}")
async def patch_node(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    body: NodePatch,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await _require_owner(grimoire_id, user_id, session)
    node = await _node_in_grimoire(grimoire_id, node_id, session)
    provided = body.model_fields_set
    reparented = False

    if "title" in provided:
        if body.title is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="title is required — nodes cannot be unnamed.",
            )
        node.title = body.title

    if "parent_id" in provided:
        target = body.parent_id
        if target == node.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot move a node under itself.",
            )
        if target is not None:
            parent = await _resolve_parent(grimoire_id, target, session)
            walker: Node | None = parent
            while walker is not None:
                if walker.id == node.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot move a node under its own subtree.",
                    )
                walker = (
                    await session.get(Node, walker.parent_id)
                    if walker.parent_id is not None
                    else None
                )
        node.parent_id = target
        reparented = True

    if "slug" in provided:
        if body.slug is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="slug is required — nodes cannot float.",
            )
        _check_slug(body.slug)
        if body.slug != node.slug:
            dup = await session.scalar(
                select(Node.id).where(
                    *_sibling_filters(grimoire_id, node.parent_id),
                    Node.slug == body.slug,
                    Node.id != node.id,
                )
            )
            if dup is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Slug already exists here.",
                )
            node.slug = body.slug

    if "position" in provided:
        if body.position is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="position must be a 1-based integer index.",
            )
        order: list[uuid.UUID] = [
            row
            for row in await session.scalars(
                select(Node.id)
                .where(*_sibling_filters(grimoire_id, node.parent_id))
                .order_by(Node.position, Node.id)
            )
        ]
        if node.id in order:
            order.remove(node.id)
        index = max(0, min(body.position - 1, len(order)))
        order.insert(index, node.id)
        for new_pos, moved_id in enumerate(order, start=1):
            await session.execute(
                update(Node).where(Node.id == moved_id).values(position=new_pos)
            )
        node.position = index + 1

    add_audit(
        session,
        actor=user_id,
        action="node_moved" if reparented else "node_patched",
        grimoire_id=grimoire_id,
        meta={
            "node_id": str(node.id),
            "changes": sorted(provided),
            "to_parent": (
                str(body.parent_id)
                if reparented and body.parent_id is not None
                else None
            )
            if reparented
            else None,
        },
    )
    await session.commit()
    return _node_body(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await _require_owner(grimoire_id, user_id, session)
    node = await _node_in_grimoire(grimoire_id, node_id, session)
    children = await session.scalar(
        select(func.count()).select_from(Node).where(Node.parent_id == node_id)
    )
    if children:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node still holds nodes; move or remove them first.",
        )
    documents = await session.scalar(
        select(func.count()).select_from(Document).where(Document.node_id == node_id)
    )
    if documents:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node still holds a document; remove it first.",
        )
    await session.delete(node)
    add_audit(
        session,
        actor=user_id,
        action="node_deleted",
        grimoire_id=grimoire_id,
        meta={"node_id": str(node_id), "kind": node.kind, "slug": node.slug},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
