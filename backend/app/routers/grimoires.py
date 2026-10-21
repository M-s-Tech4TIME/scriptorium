"""Grimoire + membership routes (M3 C3, decisions 0010/0017/0018).

Access model: `require_membership` resolves the caller's role per request;
any non-member gets a uniform 404 (existence is never leaked, IDOR rule).
Members attempting a mutation above their role get 403.

Micro-defaults (documented in docs/architecture/overview.md, owner-vetoable):
- `source_format` is immutable after creation.
- Member roles assigned via API: editor|viewer only (no owner transfer yet).
- The owner cannot remove themselves (delete the grimoire or transfer first).
- Category reorder on grimoires follows the per-user categories router.
"""

from __future__ import annotations

import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id, require_membership
from app.db import get_session
from app.models import (
    Athenaeum,
    Document,
    Grimoire,
    GrimoireCategory,
    Membership,
    Node,
    User,
)

router = APIRouter(prefix="/api/v1/grimoires", tags=["grimoires"])

_SLUG_RE = re.compile(r"[a-z0-9-]+")


class GrimoireIn(BaseModel):
    # native hierarchy (0020 Q-M3-10=A): every grimoire lives in an Athenaeum
    athenaeum_id: uuid.UUID
    slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    source_format: Literal["rst", "myst"] = "rst"
    theme: str | None = Field(default=None, min_length=1, max_length=80)
    category_id: uuid.UUID | None = None


class GrimoirePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    theme: str | None = Field(default=None, min_length=1, max_length=80)
    athenaeum_id: uuid.UUID | None = None  # cross-Athenaeum move (owner of target)
    category_id: uuid.UUID | None = None  # `None` present in body clears it


class MemberIn(BaseModel):
    email: str
    role: Literal["editor", "viewer"]


class MemberPatch(BaseModel):
    role: Literal["editor", "viewer"]


def _check_slug(slug: str) -> str:
    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Slug must match [a-z0-9-]+.",
        )
    return slug


def _grimoire_body(row: Grimoire, role: str) -> dict[str, object]:
    return {
        "id": str(row.id),
        "athenaeum_id": str(row.athenaeum_id),
        "slug": row.slug,
        "title": row.title,
        "source_format": row.source_format,
        "theme": row.theme,
        "category_id": str(row.category_id) if row.category_id else None,
        "created_by": str(row.created_by) if row.created_by else None,
        "role": role,
    }


async def _own_grimoire_by_slug_or_conflict(slug: str, session: AsyncSession) -> None:
    taken = await session.scalar(select(Grimoire.id).where(Grimoire.slug == slug))
    if taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already exists."
        )


async def _verify_category(
    athenaeum_id: uuid.UUID,
    category_id: uuid.UUID | None,
    session: AsyncSession,
) -> None:
    if category_id is None:
        return
    category = await session.get(GrimoireCategory, category_id)
    if category is None or category.athenaeum_id != athenaeum_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found."
        )


async def _own_athenaeum(
    athenaeum_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> Athenaeum:
    row = await session.get(Athenaeum, athenaeum_id)
    if row is None or row.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athenaeum not found.",
        )
    return row


@router.get("")
async def list_grimoires(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    rows = await session.execute(
        select(Grimoire, Membership.role)
        .join(Membership, Membership.grimoire_id == Grimoire.id)
        .where(Membership.user_id == user_id)
        .order_by(Grimoire.title)
    )
    return [_grimoire_body(row, role) for row, role in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_grimoire(
    body: GrimoireIn,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await _own_athenaeum(body.athenaeum_id, user_id, session)
    _check_slug(body.slug)
    await _own_grimoire_by_slug_or_conflict(body.slug, session)
    await _verify_category(body.athenaeum_id, body.category_id, session)
    grimoire = Grimoire(
        athenaeum_id=body.athenaeum_id,
        slug=body.slug,
        title=body.title,
        source_format=body.source_format,
        theme=body.theme or "scriptorium",
        category_id=body.category_id,
        created_by=user_id,
    )
    session.add(grimoire)
    await session.flush()
    session.add(Membership(user_id=user_id, grimoire_id=grimoire.id, role="owner"))
    add_audit(
        session,
        actor=user_id,
        action="grimoire_created",
        grimoire_id=grimoire.id,
        meta={"slug": grimoire.slug, "source_format": grimoire.source_format},
    )
    await session.commit()
    return _grimoire_body(grimoire, "owner")


async def _role_grimoire(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    *,
    need_owner: bool,
) -> tuple[Grimoire, str]:
    """Fetch + authorize: outsider 404; member-not-owner on owner routes 403."""
    role = await require_membership(grimoire_id, user_id, session)
    grimoire = await session.get(Grimoire, grimoire_id)
    if grimoire is None:  # membership rows are CASCADE — means concurrent delete
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Grimoire not found."
        )
    if need_owner and role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required.",
        )
    return grimoire, role


@router.get("/{grimoire_id}")
async def get_grimoire(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    grimoire, role = await _role_grimoire(
        grimoire_id, user_id, session, need_owner=False
    )
    return _grimoire_body(grimoire, role)


@router.patch("/{grimoire_id}")
async def patch_grimoire(
    grimoire_id: uuid.UUID,
    body: GrimoirePatch,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    grimoire, role = await _role_grimoire(
        grimoire_id, user_id, session, need_owner=True
    )
    provided = body.model_fields_set
    moved = False
    if "athenaeum_id" in provided:
        target = body.athenaeum_id
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="athenaeum_id is required — grimoires cannot float.",
            )
        if target != grimoire.athenaeum_id:
            await _own_athenaeum(target, user_id, session)
            grimoire.athenaeum_id = target
            moved = True
    if "slug" in provided:
        if body.slug is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="slug is required — grimoires cannot float.",
            )
        _check_slug(body.slug)
        if body.slug != grimoire.slug:
            dup = await session.scalar(
                select(Grimoire.id).where(
                    Grimoire.slug == body.slug, Grimoire.id != grimoire_id
                )
            )
            if dup is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Slug already exists."
                )
            grimoire.slug = body.slug
    if "category_id" in provided:
        scope = grimoire.athenaeum_id
        await _verify_category(scope, body.category_id, session)
        grimoire.category_id = body.category_id  # explicit None ⇒ Uncategorized
    if body.title is not None:
        grimoire.title = body.title
    if body.theme is not None:
        grimoire.theme = body.theme
    add_audit(
        session,
        actor=user_id,
        action="grimoire_moved" if moved else "grimoire_patched",
        grimoire_id=grimoire_id,
        meta={
            "changes": sorted(provided),
            "to_athenaeum": str(body.athenaeum_id) if moved else None,
        },
    )
    await session.commit()
    return _grimoire_body(grimoire, role)


@router.delete("/{grimoire_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_grimoire(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> Response:
    grimoire, _ = await _role_grimoire(grimoire_id, user_id, session, need_owner=True)
    node_count = await session.scalar(
        select(func.count()).select_from(Node).where(Node.grimoire_id == grimoire_id)
    )
    await session.delete(grimoire)
    add_audit(
        session,
        actor=user_id,
        action="grimoire_deleted",
        meta={"slug": grimoire.slug, "nodes": int(node_count or 0)},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class DuplicateIn(BaseModel):
    athenaeum_id: uuid.UUID | None = None  # default: the source's library
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=200)


async def _free_auto_slug(base: str, session: AsyncSession) -> str:
    """0025 ruling a: `base-copy`, then `-copy-2`, …; first free wins."""
    candidates = [f"{base}-copy"] + [f"{base}-copy-{n}" for n in range(2, 101)]
    for candidate in candidates:
        taken = await session.scalar(
            select(Grimoire.id).where(Grimoire.slug == candidate)
        )
        if taken is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No free copy slug could be derived.",
    )


def _parent_first(nodes: list[Node]) -> list[Node]:
    """Order nodes so parents precede children (roots, then BFS by level)."""
    by_parent: dict[uuid.UUID | None, list[Node]] = {}
    for node in nodes:
        by_parent.setdefault(node.parent_id, []).append(node)
    result: list[Node] = []
    frontier: list[uuid.UUID | None] = [None]
    while frontier:
        level = frontier
        frontier = []
        for parent_id in level:
            for node in by_parent.get(parent_id, []):
                result.append(node)
                frontier.append(node.id)
    if len(result) != len(nodes):  # unreachables mean a cycle API rules forbid
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source tree is inconsistent; duplication refused.",
        )
    return result


@router.post("/{grimoire_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_grimoire(
    grimoire_id: uuid.UUID,
    body: DuplicateIn,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Deep copy (0025): grimoire + tree + head documents; fresh roster, v1."""
    grimoire, _ = await _role_grimoire(grimoire_id, user_id, session, need_owner=True)

    target_athenaeum = body.athenaeum_id or grimoire.athenaeum_id
    if body.athenaeum_id is not None and body.athenaeum_id != grimoire.athenaeum_id:
        await _own_athenaeum(body.athenaeum_id, user_id, session)  # foreign → 404

    if body.slug is not None:
        _check_slug(body.slug)
        new_slug = body.slug
    else:
        new_slug = await _free_auto_slug(grimoire.slug, session)
    taken = await session.scalar(select(Grimoire.id).where(Grimoire.slug == new_slug))
    if taken is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already exists."
        )
    new_title = body.title if body.title is not None else f"{grimoire.title} (copy)"

    same_library = target_athenaeum == grimoire.athenaeum_id
    copy_id = uuid.uuid4()  # explicit ids: client-side defaults land at flush
    copy = Grimoire(
        id=copy_id,
        athenaeum_id=target_athenaeum,
        slug=new_slug,
        title=new_title,
        source_format=grimoire.source_format,
        theme=grimoire.theme,
        created_by=user_id,
        category_id=grimoire.category_id if same_library else None,
    )
    session.add(copy)
    # ruling b: fresh roster — the duplicator is the copy's sole owner
    session.add(Membership(user_id=user_id, grimoire_id=copy_id, role="owner"))

    source_nodes = list(
        (
            await session.scalars(
                select(Node)
                .where(Node.grimoire_id == grimoire_id)
                .order_by(Node.position, Node.id)
            )
        ).all()
    )
    ordered = _parent_first(source_nodes)
    id_map: dict[uuid.UUID, uuid.UUID] = {}
    for source_node in ordered:
        node_id = uuid.uuid4()
        session.add(
            Node(
                id=node_id,
                grimoire_id=copy_id,
                parent_id=(
                    id_map[source_node.parent_id]
                    if source_node.parent_id is not None
                    else None
                ),
                kind=source_node.kind,
                title=source_node.title,
                slug=source_node.slug,
                position=source_node.position,
            )
        )
        id_map[source_node.id] = node_id

    source_docs = list(
        (
            await session.scalars(
                select(Document).where(
                    Document.node_id.in_(
                        select(Node.id).where(Node.grimoire_id == grimoire_id)
                    )
                )
            )
        ).all()
    )
    for source_doc in source_docs:
        session.add(
            Document(
                node_id=id_map[source_doc.node_id],
                tiptap_json=source_doc.tiptap_json,
                source_text=source_doc.source_text,
                source_format=source_doc.source_format,
                version=1,  # ruling c: head content as v1, no history clone
                updated_by=user_id,
            )
        )

    add_audit(
        session,
        actor=user_id,
        action="grimoire_duplicated",
        grimoire_id=copy_id,
        meta={
            "source_id": str(grimoire_id),
            "slug": new_slug,
            "nodes": len(ordered),
            "documents": len(source_docs),
        },
    )
    await session.commit()
    copy_row = await session.get(Grimoire, copy_id)
    assert copy_row is not None
    return _grimoire_body(copy_row, "owner")


@router.get("/{grimoire_id}/members")
async def list_members(
    grimoire_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    await require_membership(grimoire_id, user_id, session)
    rows = await session.execute(
        select(Membership.user_id, Membership.role, User.display)
        .join(User, User.id == Membership.user_id)
        .where(Membership.grimoire_id == grimoire_id)
        .order_by(Membership.role)
    )
    return [
        {"user_id": str(uid), "role": role, "display": display}
        for uid, role, display in rows
    ]


@router.post("/{grimoire_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    grimoire_id: uuid.UUID,
    body: MemberIn,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await _role_grimoire(grimoire_id, user_id, session, need_owner=True)
    target = await session.scalar(select(User).where(User.email == body.email.lower()))
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    existing = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == target.id,
            Membership.grimoire_id == grimoire_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Already a member."
        )
    session.add(
        Membership(
            user_id=uuid.UUID(str(target.id)),
            grimoire_id=grimoire_id,
            role=body.role,
        )
    )
    add_audit(
        session,
        actor=user_id,
        action="member_added",
        grimoire_id=grimoire_id,
        meta={"user_id": str(target.id), "role": body.role},
    )
    await session.commit()
    return {
        "user_id": str(target.id),
        "role": body.role,
        "display": target.display,
    }


@router.patch("/{grimoire_id}/members/{member_id}")
async def patch_member(
    grimoire_id: uuid.UUID,
    member_id: uuid.UUID,
    body: MemberPatch,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await _role_grimoire(grimoire_id, user_id, session, need_owner=True)
    role_row = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == member_id, Membership.grimoire_id == grimoire_id
        )
    )
    if role_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    if role_row == "owner":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner role is fixed."
        )
    await session.execute(
        sa_update(Membership)
        .where(Membership.user_id == member_id, Membership.grimoire_id == grimoire_id)
        .values(role=body.role)
    )
    add_audit(
        session,
        actor=user_id,
        action="member_role_changed",
        grimoire_id=grimoire_id,
        meta={"user_id": str(member_id), "role": body.role},
    )
    await session.commit()
    return {"user_id": str(member_id), "role": body.role}


@router.delete(
    "/{grimoire_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    grimoire_id: uuid.UUID,
    member_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> Response:
    role = await require_membership(grimoire_id, user_id, session)
    if role != "owner" and member_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Owner role required."
        )
    if role == "owner" and member_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner cannot leave; delete the grimoire or transfer first.",
        )
    gone = await session.scalar(
        select(Membership.role).where(
            Membership.user_id == member_id, Membership.grimoire_id == grimoire_id
        )
    )
    if gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found."
        )
    await session.execute(
        sa_delete(Membership).where(
            Membership.user_id == member_id, Membership.grimoire_id == grimoire_id
        )
    )
    add_audit(
        session,
        actor=user_id,
        action="member_removed",
        grimoire_id=grimoire_id,
        meta={"user_id": str(member_id), "was": gone, "self": member_id == user_id},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
