"""Audit-log helper — every M3 mutation writes one row in the same transaction.

Kept deliberately tiny: callers add the row to `session` themselves so the
flush/commit is the caller's transaction (no surprise commits mid-request).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def add_audit(
    session: AsyncSession,
    *,
    actor: uuid.UUID | None,
    action: str,
    grimoire_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Stage an audit row (call `commit()` as usual — staged for atomicity)."""
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            grimoire_id=grimoire_id,
            meta=meta or {},
        )
    )
