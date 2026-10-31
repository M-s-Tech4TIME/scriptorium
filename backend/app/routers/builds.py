"""Build endpoints (M4-C3, decision 0026) — the production trigger.

- `POST /api/v1/athenaeums/{id}/builds` — **Athenaeum owner only**;
  E1: no grimoires → 422; E3: while a build is queued/running → 409
  (the E3 check and the `max(build_number)+1` insert are serialized by
  a per-Athenaeum PG advisory xact lock). Dispatch per
  `SC_BUILD_DISPATCH` ("celery" is the production default; "inline"
  executes in a worker thread — dev/CI convenience, disclosed).
- `GET  /api/v1/athenaeums/{id}/builds` and `/builds/{build_id}` — the
  owner or any member (a membership on any grimoire inside).
- No build DELETE: retention is a serving-phase decision (0026 P4) —
  an unregistered route yields the framework's own 405, which is the
  honest refusal.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import add_audit
from app.auth import get_current_user_id
from app.db import get_session
from app.models import Athenaeum, Build, Grimoire, Membership
from app.sphinx.execute import execute_build_sync

router = APIRouter(prefix="/api/v1/athenaeums", tags=["builds"])


def _body(row: Build) -> dict[str, object]:
    return {
        "id": str(row.id),
        "athenaeum_id": str(row.athenaeum_id) if row.athenaeum_id else "",
        "build_number": row.build_number,
        "status": row.status,
        "triggered_by": str(row.triggered_by) if row.triggered_by else None,
        "started": (
            row.started.isoformat() if isinstance(row.started, datetime) else None
        ),
        "finished": (
            row.finished.isoformat() if isinstance(row.finished, datetime) else None
        ),
        "log_path": row.log_path,
        "artifact_path": row.artifact_path,
        "published_at": (
            row.published_at.isoformat()
            if isinstance(row.published_at, datetime)
            else None
        ),
        "published_by": str(row.published_by) if row.published_by else None,
    }


async def _load_athenaeum(athenaeum_id: uuid.UUID, session: AsyncSession) -> Athenaeum:
    row = await session.get(Athenaeum, athenaeum_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Athenaeum not found."
        )
    return row


def dispatch_mode() -> str:
    mode = os.environ.get("SC_BUILD_DISPATCH", "celery")
    if mode not in ("celery", "inline"):
        raise RuntimeError(
            f"SC_BUILD_DISPATCH must be 'celery' or 'inline', got {mode!r}."
        )
    return mode


async def _member_or_none(
    athenaeum_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
) -> bool:
    """True when the caller holds any membership inside the Athenaeum."""
    held = await session.scalar(
        select(Grimoire.id)
        .join(Membership, Membership.grimoire_id == Grimoire.id)
        .where(
            Grimoire.athenaeum_id == athenaeum_id,
            Membership.user_id == user_id,
        )
        .limit(1)
    )
    return held is not None


@router.post("/{athenaeum_id}/builds", status_code=status.HTTP_201_CREATED)
async def trigger_build(
    athenaeum_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    athenaeum = await _load_athenaeum(athenaeum_id, session)
    if athenaeum.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Athenaeum not found."
        )

    # E1 (0026): an empty Athenaeum has nothing to build — refuse early.
    counts = await session.scalar(
        select(func.count())
        .select_from(Grimoire)
        .where(Grimoire.athenaeum_id == athenaeum_id)
    )
    if not counts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Athenaeum has no grimoires to build.",
        )

    # E3 (0026): one publication at a time per Athenaeum. Serialize the
    # conflict check + the max+1 numbering with a per-Athenaeum lock
    # (single bigint form of pg_advisory_xact_lock: the int8 keyspace is
    # fed from the first half of the Athenaeum id).
    tkey = int.from_bytes(athenaeum_id.bytes[:8], "big", signed=True)
    await session.execute(select(func.pg_advisory_xact_lock(tkey)))

    active = await session.scalar(
        select(Build.id)
        .where(
            Build.athenaeum_id == athenaeum_id,
            Build.status.in_(("queued", "running")),
        )
        .limit(1)
    )
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A build is already queued or running for this Athenaeum.",
        )

    highest = await session.scalar(
        select(func.max(Build.build_number)).where(Build.athenaeum_id == athenaeum_id)
    )
    number = int(highest or 0) + 1
    build = Build(
        athenaeum_id=athenaeum_id,
        build_number=number,
        status="queued",
        triggered_by=user_id,
    )
    session.add(build)
    add_audit(
        session,
        actor=user_id,
        action="build_triggered",
        meta={
            "athenaeum_id": str(athenaeum_id),
            "build_id": str(build.id),
            "build_number": number,
        },
    )
    await session.commit()

    if dispatch_mode() == "inline":
        await anyio.to_thread.run_sync(execute_build_sync, str(build.id))
        # inline ran in another session (fresh engine per Rule) — the
        # request copy is stale: re-read before reporting the outcome.
        await session.refresh(build)

    return _body(build)


@router.get("/{athenaeum_id}/builds")
async def list_builds(
    athenaeum_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[dict[str, object]]:
    athenaeum = await _load_athenaeum(athenaeum_id, session)
    allowed = athenaeum.owner_id == user_id or await _member_or_none(
        athenaeum_id, user_id, session
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Athenaeum not found."
        )
    builds = await session.scalars(
        select(Build)
        .where(Build.athenaeum_id == athenaeum_id)
        .order_by(Build.build_number.desc())
    )
    return [_body(build) for build in builds]


@router.get("/{athenaeum_id}/builds/{build_id}")
async def get_build(
    athenaeum_id: uuid.UUID,
    build_id: uuid.UUID,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, object]:
    athenaeum = await _load_athenaeum(athenaeum_id, session)
    allowed = athenaeum.owner_id == user_id or await _member_or_none(
        athenaeum_id, user_id, session
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Athenaeum not found."
        )
    build = await session.get(Build, build_id)
    if build is None or build.athenaeum_id != athenaeum_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Build not found."
        )
    return _body(build)
