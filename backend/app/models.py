"""SQLAlchemy 2.x models — schema per decisions 0010 (tree) / 0018 (grimoire).

Conventions: UUID PKs (Python-side uuid4 + PG gen_random_uuid() server default),
timestamptz created/updated, per-grimoire cascade deletes, SET NULL for audit trails.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def _now() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    pw_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # argon2id string (auth.py, M1)
    display: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = _now()


class RefreshToken(Base):
    """Server-side refresh-token record — family-based reuse detection (0017).

    Only identifiers/state are stored; token material itself never is (Rule 2).
    revoked_reason: 'rotated' (normal rotation), 'reuse' (chain burned),
    'logout', 'expired'.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    jti: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False
    )
    parent_jti: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = _now()
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
    __table_args__ = (
        CheckConstraint(
            "revoked_reason IN ('rotated', 'reuse', 'logout', 'expired')",
            name="ck_refresh_tokens_reason",
        ),
    )


class Athenaeum(Base):
    """One library — a complete documentation project for a product (0020).

    Native hierarchy: user → Athenaeums → categories → grimoires.
    Slug uniqueness is per owner (every user may own slug `default`).
    """

    __tablename__ = "athenaeums"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    # Serving phase (0035 D1), amended by 0036: the current global public
    # URL name. The editor-facing `slug` stays per-owner (0021); this column
    # is the canonical target of `/a/{public_slug}/...`. Owner renames move
    # the canonical value and leave the old value as a `public_names` alias.
    public_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    custom_css: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    latest_build_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("builds.id", ondelete="SET NULL"), nullable=True
    )
    stable_build_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("builds.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = _now()
    __table_args__ = (
        UniqueConstraint("owner_id", "slug", name="uq_athenaeums_owner_slug"),
        UniqueConstraint("public_slug", name="uq_athenaeums_public_slug"),
    )


class PublicName(Base):
    """Public URL-name registry (0036 A1/C1) — canonical, aliases, tombstones.

    ``slug`` is the single global namespace behind ``/a/{slug}/...``. A
    current row has ``is_current=True`` and a live ``athenaeum_id``. A
    rename retires the old row (still addressable as an alias); deleting
    the Athenaeum sets ``athenaeum_id`` to NULL but keeps the row as a
    permanent tombstone so an old public URL can never be taken over.
    """

    __tablename__ = "public_names"

    slug: Mapped[str] = mapped_column(String(160), primary_key=True)
    athenaeum_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("athenaeums.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = _now()
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        Index(
            "uq_public_names_current",
            "athenaeum_id",
            unique=True,
            postgresql_where=text("is_current AND athenaeum_id IS NOT NULL"),
        ),
    )


class GrimoireCategory(Base):
    """A section inside an Athenaeum grouping grimoires (0020 Q-M3-9=A).

    Scoped to one Athenaeum (ownership flows via the Athenaeum's owner).
    Deleting a category leaves its grimoires with NULL category
    (Uncategorized) inside the same Athenaeum.
    """

    __tablename__ = "grimoire_categories"

    id: Mapped[uuid.UUID] = _uuid_pk()
    athenaeum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athenaeums.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _now()
    __table_args__ = (
        UniqueConstraint("athenaeum_id", "name", name="uq_grimoire_categories_name"),
    )


class Grimoire(Base):
    """One self-contained documentation set — a "book" inside an Athenaeum."""

    __tablename__ = "grimoires"

    id: Mapped[uuid.UUID] = _uuid_pk()
    athenaeum_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("athenaeums.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grimoire_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_format: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="rst"
    )
    theme: Mapped[str] = mapped_column(
        String(80), nullable=False, server_default="scriptorium"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = _now()
    __table_args__ = (
        CheckConstraint("source_format IN ('rst', 'myst')", name="ck_grimoires_format"),
    )


class Membership(Base):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    grimoire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grimoires.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'editor', 'viewer')", name="ck_memberships_role"
        ),
    )


class Node(Base):
    """One ordered-tree row (kind chapter|folio, 0022) driving TOC + toctree.

    Root rows have parent_id NULL. Slug uniqueness is enforced per sibling set via
    partial indexes (plain UNIQUE would let NULL parent_ids collide in PG).
    """

    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    grimoire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grimoires.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    __table_args__ = (
        CheckConstraint("kind IN ('chapter', 'folio')", name="ck_nodes_kind"),
        Index(
            "uq_nodes_root_slug",
            "grimoire_id",
            "slug",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "uq_nodes_child_slug",
            "grimoire_id",
            "parent_id",
            "slug",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
        ),
    )


class Document(Base):
    """Editor content for a page-node. TipTap JSON is canonical (decision 0010)."""

    __tablename__ = "documents"
    # fetch server-generated values (INSERT default + onupdate timestamp)
    # during flush via RETURNING — otherwise the onupdate expiry makes a
    # post-commit read attempt lazy sync IO (MissingGreenlet in async).
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012 - SQLAlchemy API

    id: Mapped[uuid.UUID] = _uuid_pk()
    node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tiptap_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    source_format: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="rst"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DocumentHistory(Base):
    """Append-only per-document versions (single-editor history; Phase A keys versions here)."""

    __tablename__ = "document_history"

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    tiptap_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    at: Mapped[datetime] = _now()
    __table_args__ = (
        Index("uq_document_history_version", "document_id", "version", unique=True),
    )


class MediaAsset(Base):
    """One uploaded image/GIF owned by a grimoire (V1 media scope).

    Files live under the configured media root at ``storage_path``; the
    database row is the authorization + metadata source. Canonical TipTap
    image nodes point at ``/_static/media/{id}.{ext}`` so the same URL
    works in the editor preview (through the API) and in every published
    build (copied into the artifact's ``_static`` directory).
    """

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    grimoire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grimoires.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = _now()
    __table_args__ = (
        CheckConstraint(
            "content_type IN "
            "('image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/avif')",
            name="ck_media_assets_type",
        ),
    )


class Build(Base):
    """One numbered production of documentation (0026).

    Two key eras share this table: pre-M4 rows are grimoire-keyed
    (grimoire_id set, athenaeum_id NULL); 0026 site-build rows are
    athenaeum-keyed (athenaeum_id set, grimoire_id NULL) — exactly one
    of the two keys is ever set (ck_builds_site). Numbering is
    per-Athenaeum, monotonic (uq_builds_athenaeum_number).
    """

    __tablename__ = "builds"

    id: Mapped[uuid.UUID] = _uuid_pk()
    grimoire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grimoires.id", ondelete="CASCADE"), nullable=True, index=True
    )
    athenaeum_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("athenaeums.id", ondelete="CASCADE"), nullable=True, index=True
    )
    build_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="queued"
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Serving phase (0035 A2): first publication history. A build that was
    # ever published remains addressable by its immutable numbered URL.
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'ok', 'failed')", name="ck_builds_status"
        ),
        CheckConstraint(
            "((grimoire_id IS NULL) != (athenaeum_id IS NULL))",
            name="ck_builds_site",
        ),
        UniqueConstraint(
            "athenaeum_id", "build_number", name="uq_builds_athenaeum_number"
        ),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    actor: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    grimoire_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grimoires.id", ondelete="SET NULL"), nullable=True
    )
    at: Mapped[datetime] = _now()
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
