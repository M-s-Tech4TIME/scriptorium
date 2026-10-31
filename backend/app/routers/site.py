"""Public site serving (decisions 0035 C1/D1/B3, 0036 A1/D1).

FastAPI owns the artifact routes: it resolves the Athenaeum's current public
name or a permanent alias, enforces private visibility, follows the
latest/stable pointer or an immutable numbered build, and serves files from
the artifact root with the E2 header contract. No nginx alias is required
for v1; the same code path is the local/CI proof.

URL shape (0035 D1, unchanged by 0036):
    /a/{public_slug}/                 -> latest (or stable) channel
    /a/{public_slug}/latest/...       -> latest pointer, no-cache
    /a/{public_slug}/stable/...       -> stable pointer, no-cache
    /a/{public_slug}/b/{number}/...   -> immutable numbered build

A retired public name permanently 308-redirects to the current name after
the same private-access check. Path suffix and query string are preserved;
aliases flatten to the current canonical name. Only builds that were
successfully published at least once are addressable by number. Unpublished
drafts are not exposed.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user_id
from app.db import get_session
from app.models import Athenaeum, Build, PublicName
from app.serving.access import can_read_athenaeum
from app.serving.artifacts import safe_file, servable_artifact
from app.serving.security import artifact_headers

router = APIRouter(tags=["site"])


async def _resolve_public_name(
    session: AsyncSession, public_slug: str
) -> tuple[Athenaeum, bool]:
    """Resolve a current name or permanent alias to the live Athenaeum.

    A tombstone (``athenaeum_id IS NULL``) and an unknown name are the same
    uniform 404. The boolean says the requested name is not the current
    canonical name and therefore needs a permanent redirect after auth.
    """
    name = await session.get(PublicName, public_slug)
    if name is None or name.athenaeum_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    athenaeum = await session.get(Athenaeum, name.athenaeum_id)
    if athenaeum is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return athenaeum, athenaeum.public_slug != public_slug


async def _authorized_target(
    session: AsyncSession,
    public_slug: str,
    user_id: uuid.UUID | None,
) -> tuple[Athenaeum, bool]:
    athenaeum, alias = await _resolve_public_name(session, public_slug)
    await _authorize(session, athenaeum, user_id)
    return athenaeum, alias


async def _authorize(
    session: AsyncSession,
    athenaeum: Athenaeum,
    user_id: uuid.UUID | None,
) -> None:
    if not await can_read_athenaeum(session, athenaeum, user_id):
        # Uniform 404: private existence is not leaked to outsiders.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


async def _channel_build(
    session: AsyncSession, athenaeum: Athenaeum, channel: str
) -> Build | None:
    build_id = (
        athenaeum.latest_build_id if channel == "latest" else athenaeum.stable_build_id
    )
    if build_id is None:
        return None
    build = await session.get(Build, build_id)
    if (
        build is None
        or build.athenaeum_id != athenaeum.id
        or build.status != "ok"
        or build.published_at is None
    ):
        return None
    return build


async def _numbered_build(
    session: AsyncSession, athenaeum: Athenaeum, number: int
) -> Build | None:
    build = await session.scalar(
        select(Build).where(
            Build.athenaeum_id == athenaeum.id,
            Build.build_number == number,
        )
    )
    if build is None or build.status != "ok" or build.published_at is None:
        return None
    return build


def _redirect(
    path: str,
    request: Request,
    *,
    private: bool = False,
    status_code: int = status.HTTP_307_TEMPORARY_REDIRECT,
) -> RedirectResponse:
    # Relative target: never echo an attacker-controlled Host header into
    # a Location. Query strings survive canonicalization.
    target = f"{path}?{request.url.query}" if request.url.query else path
    headers = {"Cache-Control": "private, no-store" if private else "no-cache"}
    if private:
        headers["Vary"] = "Cookie"
        headers["X-Robots-Tag"] = "noindex, nofollow"
    return RedirectResponse(
        url=target,
        status_code=status_code,
        headers=headers,
    )


def _alias_redirect(
    request: Request, old_slug: str, athenaeum: Athenaeum
) -> RedirectResponse:
    """Permanent alias redirect, preserving the suffix and query string.

    Use the raw ASGI path so percent-encoded suffixes are not normalized
    into a different URL. The canonical slug is validated, and the target
    stays relative, so a hostile Host header cannot become an open redirect.
    """
    raw_path = request.scope.get("raw_path")
    path = request.url.path
    if isinstance(raw_path, bytes):
        try:
            path = raw_path.decode("ascii")
        except UnicodeDecodeError:
            path = request.url.path
    prefix = f"/a/{old_slug}"
    suffix = path[len(prefix) :] if path.startswith(prefix) else ""
    if not suffix:
        suffix = "/"
    elif not suffix.startswith("/"):
        suffix = f"/{suffix}"
    return _redirect(
        f"/a/{athenaeum.public_slug}{suffix}",
        request,
        private=not athenaeum.is_public,
        status_code=status.HTTP_308_PERMANENT_REDIRECT,
    )


async def _serve(
    request: Request,
    build: Build,
    athenaeum: Athenaeum,
    url_path: str,
    *,
    immutable: bool,
) -> FileResponse | RedirectResponse:
    servable = servable_artifact(build)
    if servable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    html_root, manifest = servable

    relative = url_path.lstrip("/")
    if relative and not url_path.endswith("/"):
        try:
            candidate_dir = (html_root / relative).resolve()
            inside = candidate_dir.is_relative_to(html_root.resolve())
        except OSError, RuntimeError:
            candidate_dir = None
            inside = False
        if candidate_dir is not None and inside and candidate_dir.is_dir():
            return _redirect(
                request.url.path + "/",
                request,
                private=not athenaeum.is_public,
            )

    target = safe_file(html_root, url_path)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    headers = artifact_headers(
        manifest,
        immutable=immutable,
        private=not athenaeum.is_public,
    )
    headers["X-Scriptorium-Build"] = f"{athenaeum.public_slug}/{build.build_number}"
    return FileResponse(target, headers=headers)


async def _serve_channel(
    request: Request,
    public_slug: str,
    channel: str,
    url_path: str,
    user_id: uuid.UUID | None,
    session: AsyncSession,
) -> FileResponse | RedirectResponse:
    athenaeum, alias = await _authorized_target(session, public_slug, user_id)
    if alias:
        return _alias_redirect(request, public_slug, athenaeum)
    build = await _channel_build(session, athenaeum, channel)
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return await _serve(request, build, athenaeum, url_path, immutable=False)


@router.get("/a/{public_slug}")
@router.get("/a/{public_slug}/")
async def site_root(
    public_slug: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    athenaeum, alias = await _authorized_target(session, public_slug, user_id)
    if alias:
        return _alias_redirect(request, public_slug, athenaeum)
    for channel in ("latest", "stable"):
        if await _channel_build(session, athenaeum, channel) is not None:
            return _redirect(
                f"/a/{athenaeum.public_slug}/{channel}/",
                request,
                private=not athenaeum.is_public,
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


@router.get("/a/{public_slug}/latest")
@router.get("/a/{public_slug}/stable")
async def site_channel_root(
    public_slug: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    channel = "latest" if request.url.path.endswith("/latest") else "stable"
    athenaeum, alias = await _authorized_target(session, public_slug, user_id)
    if alias:
        return _alias_redirect(request, public_slug, athenaeum)
    if await _channel_build(session, athenaeum, channel) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return _redirect(
        f"/a/{athenaeum.public_slug}/{channel}/",
        request,
        private=not athenaeum.is_public,
    )


@router.get("/a/{public_slug}/latest/")
@router.get("/a/{public_slug}/stable/")
async def site_channel_index(
    public_slug: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    channel = (
        "latest"
        if request.url.path.startswith(f"/a/{public_slug}/latest/")
        else "stable"
    )
    return await _serve_channel(request, public_slug, channel, "", user_id, session)


@router.get("/a/{public_slug}/latest/{path:path}")
@router.get("/a/{public_slug}/stable/{path:path}")
async def site_channel_file(
    public_slug: str,
    path: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    channel = (
        "latest"
        if request.url.path.startswith(f"/a/{public_slug}/latest/")
        else "stable"
    )
    return await _serve_channel(request, public_slug, channel, path, user_id, session)


@router.get("/a/{public_slug}/b/{build_number}")
async def site_build_root(
    public_slug: str,
    build_number: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RedirectResponse:
    athenaeum, alias = await _authorized_target(session, public_slug, user_id)
    if alias:
        return _alias_redirect(request, public_slug, athenaeum)
    try:
        number = int(build_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
        ) from exc
    if await _numbered_build(session, athenaeum, number) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return _redirect(
        f"/a/{athenaeum.public_slug}/b/{number}/",
        request,
        private=not athenaeum.is_public,
    )


@router.get("/a/{public_slug}/b/{build_number}/")
async def site_build_index(
    public_slug: str,
    build_number: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    return await _serve_numbered(
        request, public_slug, build_number, "", user_id, session
    )


@router.get("/a/{public_slug}/b/{build_number}/{path:path}")
async def site_build_file(
    public_slug: str,
    build_number: str,
    path: str,
    request: Request,
    user_id: Annotated[uuid.UUID | None, Depends(get_optional_user_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    return await _serve_numbered(
        request, public_slug, build_number, path, user_id, session
    )


async def _serve_numbered(
    request: Request,
    public_slug: str,
    build_number: str,
    url_path: str,
    user_id: uuid.UUID | None,
    session: AsyncSession,
) -> FileResponse | RedirectResponse:
    athenaeum, alias = await _authorized_target(session, public_slug, user_id)
    if alias:
        return _alias_redirect(request, public_slug, athenaeum)
    try:
        number = int(build_number)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
        ) from exc
    build = await _numbered_build(session, athenaeum, number)
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return await _serve(request, build, athenaeum, url_path, immutable=True)
