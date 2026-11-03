"""Expiring HMAC download tokens for Full backup exports (0039 C1).

The token is self-contained and bound to one job id plus an absolute expiry;
no bearer session is required to download. The signing key is the deployment
``SECRET_KEY``; rotating it invalidates outstanding links.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime

from app.auth import get_secret

_CONTEXT = b"scriptorium-backup-download:"


def _sign(job_id: uuid.UUID, expiry: int) -> str:
    message = _CONTEXT + f"{job_id}:{expiry}".encode()
    return hmac.new(get_secret().encode(), message, hashlib.sha256).hexdigest()


def make_download_token(job_id: uuid.UUID, expires_at: datetime) -> str:
    expiry = int(expires_at.timestamp())
    return f"{expiry}.{_sign(job_id, expiry)}"


def verify_download_token(job_id: uuid.UUID, token: str) -> bool:
    try:
        expiry_text, signature = token.split(".", 1)
        expiry = int(expiry_text)
    except TypeError, ValueError:
        return False
    if expiry < int(datetime.now(UTC).timestamp()):
        return False
    expected = _sign(job_id, expiry)
    return secrets.compare_digest(signature, expected)
