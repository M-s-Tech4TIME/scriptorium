"""SQLAlchemy 2.x models — schema per decisions 0010 (tree) / 0018 (grimoire).

Conventions: UUID PKs (Python-side uuid4 + PG gen_random_uuid() server default),
timestamptz created/updated, per-grimoire cascade deletes, SET NULL for audit trails.
"""

from __future__ import annotations

import uuid
from typing import Any
from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class GrimoireCategory(Base):
    """User-defined grouping bucket for grimoires (0018, Q-M3-6=A).

    Per-user: each user curates their own sidebar sections. Deleting a
    category leaves its grimoires with NULL category (Uncategorized).
    """

    __tablename__ = "grimoire_categories"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = _now()
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_grimoire_categories_name"),
    )


class Grimoire(Base):
    """One self-contained documentation set (renamed from "project", 0018)."""

    __tablename__ = "grimoires"

    id: Mapped[uuid.UUID] = _uuid_pk()
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
    """One ordered-tree row (kind category|page) driving TOC + toctree (0010).

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
        CheckConstraint("kind IN ('category', 'page')", name="ck_nodes_kind"),
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


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[uuid.UUID] = _uuid_pk()
    grimoire_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grimoires.id", ondelete="CASCADE"), nullable=False, index=True
    )
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
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'ok', 'failed')", name="ck_builds_status"
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
