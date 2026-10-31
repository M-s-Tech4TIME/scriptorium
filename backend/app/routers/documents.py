"""Folio document endpoints — save, concurrency, import, history (0024).

Mechanics per 0018 Q-M3-2/A and Q-M3-3/A: PUT carries `expected_version`
(mismatch → 409, nothing written); every save bumps the version, appends
an immutable history row, and re-derives `source_text` server-side from
the canonical TipTap JSON via the M2 exporter for the Grimoire's
`source_format`. Import-from-source runs the M2 importer; ConversionError
→ 422. Reads belong to any member; saves need editor/owner (0024 extends
D2=A to content).
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id, require_membership
from app.conversion.export_myst import export_myst
from app.conversion.export_rst import export_rst
from app.conversion.import_doc import ConversionError, import_document
from app.conversion.tiptap import canon_doc
from app.db import get_session
from app.media import MediaRefError, validate_media_refs
from app.models import Document, DocumentHistory, Grimoire, Node

router = APIRouter(
    prefix="/api/v1/grimoires/{grimoire_id}/nodes/{node_id}", tags=["documents"]
)

_MAX_SOURCE = 1_000_000
_MAX_TIPTAP = 2_000_000


class DocumentPut(BaseModel):
    tiptap_json: dict[str, Any] | None = None
    source_text: str | None = Field(default=None, max_length=_MAX_SOURCE)
    expected_version: int = Field(ge=0)


class RestoreIn(BaseModel):
    expected_version: int = Field(ge=0)


def _doc_body(document: Document, node_id: uuid.UUID) -> dict[str, object]:
    return {
        "node_id": str(node_id),
        "version": document.version,
        "tiptap_json": document.tiptap_json,
        "source_text": document.source_text,
        "source_format": document.source_format,
        "updated_by": str(document.updated_by) if document.updated_by else None,
        "updated_at": document.updated_at.isoformat(),
    }


async def _member_node(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
    *,
    need_editor: bool,
) -> Node:
    role = await require_membership(grimoire_id, user_id, session)
    if need_editor and role not in ("owner", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Editor role required."
        )
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


def _validate_body(body: DocumentPut) -> tuple[dict[str, Any] | None, str | None]:
    """Exactly one content field; canonical-mode shape + size caps (0024)."""
    modes = [
        field for field in (body.tiptap_json, body.source_text) if field is not None
    ]
    if len(modes) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide exactly one of tiptap_json or source_text.",
        )
    if body.source_text is not None:
        return None, body.source_text
    tiptap = body.tiptap_json
    assert tiptap is not None  # narrowing for mypy
    if tiptap.get("type") != "doc":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='tiptap_json must be a TipTap document with type "doc".',
        )
    if len(json.dumps(tiptap)) > _MAX_TIPTAP:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="tiptap_json exceeds the size cap.",
        )
    return tiptap, None


@router.get("/document")
async def get_document(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _member_node(grimoire_id, node_id, user_id, session, need_editor=False)
    document = (
        await session.scalars(select(Document).where(Document.node_id == node_id))
    ).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document yet — save one first.",
        )
    return _doc_body(document, node_id)


@router.put("/document")
async def put_document(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    body: DocumentPut,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _member_node(grimoire_id, node_id, user_id, session, need_editor=True)
    tiptap_in, source_in = _validate_body(body)

    document = (
        await session.scalars(select(Document).where(Document.node_id == node_id))
    ).first()
    current_version = document.version if document is not None else 0
    if body.expected_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Version conflict: expected {body.expected_version}, "
                f"current {current_version}."
            ),
        )

    grimoire = await session.get(Grimoire, grimoire_id)
    assert grimoire is not None  # membership resolved, so the row exists
    imported = source_in is not None
    if imported:
        assert source_in is not None  # narrowing for mypy
        try:
            canonical = canon_doc(import_document(source_in, grimoire.source_format))
        except ConversionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
    else:
        assert tiptap_in is not None
        canonical = canon_doc(tiptap_in)

    fmt = grimoire.source_format
    exporter = export_rst if fmt == "rst" else export_myst
    derived_source = exporter(canonical)

    try:
        await validate_media_refs(canonical, grimoire_id, session)
    except MediaRefError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    new_version = current_version + 1
    if document is None:
        document = Document(
            node_id=node_id,
            tiptap_json=canonical,
            source_text=derived_source,
            source_format=fmt,
            version=new_version,
            updated_by=user_id,
        )
        session.add(document)
        await session.flush()  # document.id must exist before the history row
    else:
        document.tiptap_json = canonical
        document.source_text = derived_source
        document.source_format = fmt
        document.version = new_version
        document.updated_by = user_id
    session.add(
        DocumentHistory(
            document_id=document.id,
            version=new_version,
            tiptap_json=canonical,
            source_text=derived_source,
            author=user_id,
        )
    )
    add_audit(
        session,
        actor=user_id,
        action="document_saved",
        grimoire_id=grimoire_id,
        meta={"node_id": str(node_id), "version": new_version, "imported": imported},
    )
    await session.commit()
    return _doc_body(document, node_id)


@router.get("/document/history")
async def get_history(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _member_node(grimoire_id, node_id, user_id, session, need_editor=False)
    document = (
        await session.scalars(select(Document).where(Document.node_id == node_id))
    ).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document yet — save one first.",
        )
    rows = await session.scalars(
        select(DocumentHistory)
        .where(DocumentHistory.document_id == document.id)
        .order_by(DocumentHistory.version)
    )
    versions = [
        {
            "version": row.version,
            "author": str(row.author) if row.author else None,
            "at": row.at.isoformat(),
        }
        for row in rows
    ]
    return {"document_id": str(document.id), "versions": versions}


async def _history_row(
    document_id: uuid.UUID, version: int, session: AsyncSession
) -> DocumentHistory:
    row = (
        await session.scalars(
            select(DocumentHistory).where(
                DocumentHistory.document_id == document_id,
                DocumentHistory.version == version,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History version not found.",
        )
    return row


@router.get("/document/history/{version}")
async def get_history_version(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    version: int,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    await _member_node(grimoire_id, node_id, user_id, session, need_editor=False)
    document = (
        await session.scalars(select(Document).where(Document.node_id == node_id))
    ).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document yet — save one first.",
        )
    row = await _history_row(document.id, version, session)
    return {
        "document_id": str(document.id),
        "version": row.version,
        "tiptap_json": row.tiptap_json,
        "source_text": row.source_text,
        "author": str(row.author) if row.author else None,
        "at": row.at.isoformat(),
    }


@router.post("/document/history/{version}/restore")
async def restore_history_version(
    grimoire_id: uuid.UUID,
    node_id: uuid.UUID,
    version: int,
    body: RestoreIn,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    """Append a new version copied from history — history stays immutable."""
    await _member_node(grimoire_id, node_id, user_id, session, need_editor=True)
    document = (
        await session.scalars(select(Document).where(Document.node_id == node_id))
    ).first()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document yet — save one first.",
        )
    if body.expected_version != document.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Version conflict: expected {body.expected_version}, "
                f"current {document.version}."
            ),
        )
    row = await _history_row(document.id, version, session)

    grimoire = await session.get(Grimoire, grimoire_id)
    assert grimoire is not None  # membership resolved, so the row exists
    canonical = canon_doc(row.tiptap_json)
    exporter = export_rst if grimoire.source_format == "rst" else export_myst
    derived_source = exporter(canonical)
    try:
        await validate_media_refs(canonical, grimoire_id, session)
    except MediaRefError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    new_version = document.version + 1
    document.tiptap_json = canonical
    document.source_text = derived_source
    document.source_format = grimoire.source_format
    document.version = new_version
    document.updated_by = user_id
    session.add(
        DocumentHistory(
            document_id=document.id,
            version=new_version,
            tiptap_json=canonical,
            source_text=derived_source,
            author=user_id,
        )
    )
    add_audit(
        session,
        actor=user_id,
        action="document_restored",
        grimoire_id=grimoire_id,
        meta={
            "node_id": str(node_id),
            "from_version": version,
            "version": new_version,
        },
    )
    await session.commit()
    return _doc_body(document, node_id)
